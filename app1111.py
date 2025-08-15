# app.py
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="AirAlert Chile", layout="wide")
st.title("🌬️ AirAlert: Sistema de Alerta Ciudadana para Calidad del Aire en Chile")

# --- 2. FUNCIÓN PARA OBTENER DATOS DE OPENAQ v3 ---
@st.cache_data(ttl=3600)  # Cache por 1 hora
def obtener_mediciones_chile():
    # ✅ CORREGIDO: URL sin espacios
    BASE_URL = "https://api.openaq.org/v3"
    COUNTRY = "CL"
    PARAMETERS = ["pm25", "pm10", "no2", "o3", "co", "so2"]
    LIMIT = 1000

    todos_los_datos = []

    for parametro in PARAMETERS:
        st.write(f"🔍 Obteniendo datos de {parametro.upper()}...")

        params = {
            'country': COUNTRY,
            'parameter': parametro,
            'limit': LIMIT,
            'order_by': 'datetime',
            'sort': 'desc'
        }

        # ✅ CORREGIDO: Definir headers ANTES de asignar
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'AirAlert-Chile-UdeC/1.0'
        }

        # ✅ Opcional: Agregar API Key si es requerida
        API_KEY = "91eab8b4c15ab8e5eda9712fa803abe4bb45e5a6c8ee961d295de18b0b15722a"
        if API_KEY:
            headers['X-API-Key'] = API_KEY  # ✅ Ahora sí está definido

        try:
            url = f"{BASE_URL}/measurements"
            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                if 'results' in data and len(data['results']) > 0:
                    st.success(f"✅ {len(data['results'])} mediciones de {parametro}")
                    for item in data['results']:
                        coords = item.get('coordinates', {}) or {}
                        location = item.get('location', {})
                        parametro_data = item.get('parameter', {})

                        registro = {
                            'timestamp_extraccion': pd.Timestamp.now(),
                            'ubicacion_id': location.get('id'),
                            'ubicacion_nombre': location.get('name'),
                            'ciudad': item.get('city'),
                            'sensor_id': item.get('sensor', {}).get('id'),
                            'parametro': parametro_data.get('name'),
                            'parametro_display': f"{parametro_data.get('name', '').upper()}: {item.get('value')} {item.get('unit')}",
                            'unidades': item.get('unit'),
                            'latitud': coords.get('latitude'),
                            'longitud': coords.get('longitude'),
                            'proveedor': item.get('provider', {}).get('name'),
                            'owner': item.get('owner'),
                            'tipo_instrumento': item.get('sensor', {}).get('instrument_type'),
                            'timezone': item.get('timezone'),
                            'fecha_primer_dato': None,
                            'fecha_ultimo_dato': None,
                            'sensor_activo': True,
                            'valor_actual': item.get('value'),
                            'fecha_medicion': item.get('date', {}).get('utc'),
                            'datos_disponibles': item.get('value') is not None
                        }
                        todos_los_datos.append(registro)
                else:
                    st.warning(f"⚠️ No se encontraron datos de {parametro}")
            elif response.status_code == 401:
                st.error("❌ 401 Unauthorized: Verifica tu API Key o prueba sin ella.")
                st.json(response.json())
                return pd.DataFrame()
            elif response.status_code == 410:
                st.error("❌ 410 Gone: La API v2 fue descontinuada. Estás usando v3, pero verifica el endpoint.")
                return pd.DataFrame()
            else:
                st.error(f"❌ Error {response.status_code}: {response.text}")

        except Exception as e:
            st.error(f"❌ Error al conectar con OpenAQ: {e}")

    return pd.DataFrame(todos_los_datos) if todos_los_datos else pd.DataFrame()

# --- 3. CARGA DE DATOS ---
df = obtener_mediciones_chile()

if df.empty:
    st.warning("No se pudieron cargar datos de calidad del aire.")
    st.stop()

# --- 4. FILTRO POR PM2.5 Y LIMPIEZA ---
df_pm25 = df[df['parametro'] == 'pm25'].copy()
df_pm25 = df_pm25[df_pm25['unidades'] == 'µg/m³'].copy()
df_pm25['valor_actual'] = pd.to_numeric(df_pm25['valor_actual'], errors='coerce')
df_pm25.dropna(subset=['valor_actual'], inplace=True)
df_pm25 = df_pm25[df_pm25['valor_actual'] >= 0]

if df_pm25.empty:
    st.warning("No hay datos válidos de PM2.5.")
    st.stop()

# --- 5. CLASIFICACIÓN Y RECOMENDACIONES ---
def obtener_nivel_riesgo(pm25):
    if pm25 <= 12.0:
        return "Bueno", "green", "Prefiera espacios cerrados si es vulnerable."
    elif pm25 <= 35.4:
        return "Moderado", "yellow", "Grupos sensibles limiten actividades prolongadas al aire libre."
    elif pm25 <= 55.4:
        return "Insalubre S", "orange", "Grupos sensibles eviten actividades al aire libre. Mejore calefacción."
    elif pm25 <= 150.4:
        return "Insalubre", "red", "Toda la población evite actividades físicas al aire libre. Use mascarilla."
    else:
        return "Muy Insalubre", "purple", "Permanezca en interiores. No use vehículos, cigarrillos ni estufas."

df_pm25['nivel_riesgo'] = df_pm25['valor_actual'].apply(lambda x: obtener_nivel_riesgo(x)[0])
df_pm25['color_map'] = df_pm25['valor_actual'].apply(lambda x: obtener_nivel_riesgo(x)[1])
df_pm25['recomendacion'] = df_pm25['valor_actual'].apply(lambda x: obtener_nivel_riesgo(x)[2])

# --- 6. INTERFAZ ---
tab1, tab2, tab3 = st.tabs(["🗺️ Mapa", "📊 Análisis", "📋 Datos"])

with tab1:
    st.subheader("📍 Calidad del Aire en Chile (Datos en Tiempo Real)")
    df_valid = df_pm25.dropna(subset=['latitud', 'longitud'])
    
    if df_valid.empty:
        st.warning("No hay coordenadas válidas para mostrar en el mapa.")
    else:
        m = folium.Map(location=[-30, -71], zoom_start=5)
        marker_cluster = MarkerCluster().add_to(m)

        for idx, row in df_valid.iterrows():
            folium.CircleMarker(
                location=[row['latitud'], row['longitud']],
                radius=8,
                popup=f"<b>{row['ubicacion_nombre']}</b><br>PM2.5: {row['valor_actual']:.1f} µg/m³<br>{row['nivel_riesgo']}",
                color=row['color_map'],
                fill=True,
                fillColor=row['color_map']
            ).add_to(marker_cluster)
        
        st_folium(m, width=1200, height=600)

with tab2:
    st.subheader("📈 Distribución de PM2.5")
    fig = px.histogram(df_pm25, x='valor_actual', nbins=30, title="Histograma de PM2.5 en Chile")
    fig.update_layout(xaxis_title="PM2.5 (µg/m³)", yaxis_title="Frecuencia")
    st.plotly_chart(fig)
    
    st.write(f"**Promedio Nacional:** {df_pm25['valor_actual'].mean():.2f} µg/m³")
    max_row = df_pm25.loc[df_pm25['valor_actual'].idxmax()]
    st.write(f"**Máximo:** {max_row['valor_actual']:.2f} µg/m³ en {max_row['ciudad']}")

with tab3:
    st.dataframe(df_pm25[[
        'ubicacion_nombre', 'ciudad', 'valor_actual', 'nivel_riesgo', 'recomendacion'
    ]].sort_values('valor_actual', ascending=False))

# --- 7. BARRA LATERAL ---
st.sidebar.title("ℹ️ Recomendaciones")
st.sidebar.write("Use el mapa para ver el riesgo en su ciudad.")