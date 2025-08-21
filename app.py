# app.py
# AirCesfam: Sistema de apoyo a la gestión de recursos humanos
# en Cesfam La Floresta basado en calidad del aire

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import os
import glob
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="AirCesfam - Cesfam La Floresta",
    page_icon="🏥",
    layout="wide"
)

# Título principal
st.title("🏥 AirCesfam – Cesfam La Floresta")
st.markdown("""
**Sistema de apoyo a la gestión de recursos humanos y asignación de turnos,**
basado en la calidad del aire para optimizar la atención de urgencias en el Cesfam.
""")

# --- 1. CARGA DE CREDENCIALES ---
# Cargar .env si existe (modo local)
if os.path.exists(".env"):
    load_dotenv()

def get_secret(key):
    try:
        return st.secrets[key]
    except:
        return os.getenv(key)

EMAIL_REMITENTE = get_secret("EMAIL_REMITENTE")
EMAIL_APP_PASSWORD = get_secret("EMAIL_APP_PASSWORD")

if not EMAIL_REMITENTE or not EMAIL_APP_PASSWORD:
    st.error("❌ Error: No se encontraron las credenciales de correo. Revisa .env o secrets.toml")
    st.stop()

# --- 2. CARGA DE DATOS (cacheada) ---
@st.cache_data
def cargar_datos_unidos(ruta_carpeta):
    patron = os.path.join(ruta_carpeta, "*.csv")
    archivos_csv = glob.glob(patron)

    if not archivos_csv:
        st.error("❌ No se encontraron archivos CSV en la carpeta especificada.")
        return None

    listado_dataframes = []
    for archivo in archivos_csv:
        try:
            df = pd.read_csv(archivo)
            listado_dataframes.append(df)
        except Exception as e:
            st.warning(f"❌ Error al leer {os.path.basename(archivo)}: {e}")

    if not listado_dataframes:
        st.error("⚠️ No se pudo cargar ningún archivo correctamente.")
        return None

    df_unido = pd.concat(listado_dataframes, ignore_index=True)
    return df_unido

# Ruta de datos (ajustar según entorno)
ruta_carpeta = r"C:\Users\sucor\OneDrive\Escritorio\UDEC_MAGISTER\VI - TRIMESTRE\PROYECTO INTEGRADO\proyecto-aire"
df = cargar_datos_unidos(ruta_carpeta)

if df is None:
    st.stop()

# --- 3. LIMPIEZA Y PREPARACIÓN ---
df['datetimeLocal'] = pd.to_datetime(df['datetimeLocal'], errors='coerce')
df = df.dropna(subset=['datetimeLocal', 'value', 'parameter', 'location_name'])
df['value'] = pd.to_numeric(df['value'], errors='coerce')
df = df.dropna(subset=['value'])

# Filtrar contaminantes clave
contaminantes_clave = ['pm25', 'pm10', 'o3', 'no2']
df = df[df['parameter'].isin(contaminantes_clave)]

# Extraer fecha y hora
df['fecha'] = df['datetimeLocal'].dt.date
df['hora'] = df['datetimeLocal'].dt.hour

# --- 4. NIVELES DE ALERTA ---
def nivel_contaminacion(valor, parametro):
    if parametro == 'pm25':
        if valor <= 12: return 'Bueno', 'green'
        elif valor <= 35: return 'Moderado', 'yellow'
        elif valor <= 55: return 'Dañino S. G.', 'orange'
        elif valor <= 150: return 'Dañino', 'red'
        elif valor <= 250: return 'Muy Dañino', 'purple'
        else: return 'Peligroso', 'maroon'
    elif parametro == 'pm10':
        if valor <= 54: return 'Bueno', 'green'
        elif valor <= 154: return 'Moderado', 'yellow'
        elif valor <= 254: return 'Dañino S. G.', 'orange'
        elif valor <= 354: return 'Dañino', 'red'
        else: return 'Peligroso', 'purple'
    else:
        return 'Moderado', 'gray'

df['nivel_alerta'] = df.apply(lambda x: nivel_contaminacion(x['value'], x['parameter']), axis=1)
df['nivel'] = df['nivel_alerta'].apply(lambda x: x[0])
df['color'] = df['nivel_alerta'].apply(lambda x: x[1])

# --- 5. ESTIMACIÓN DE DEMANDA EN CESFAM ---
def estimar_demanda(pm25_value):
    base_consultas = 35  # promedio diario Cesfam La Floresta (ajustable)
    if pm25_value <= 12:
        factor = 1.0
    elif pm25_value <= 35:
        factor = 1.3
    elif pm25_value <= 55:
        factor = 1.7
    elif pm25_value <= 150:
        factor = 2.2
    else:
        factor = 2.8
    return int(base_consultas * factor)

# Últimos valores de PM2.5
df_pm25 = df[df['parameter'] == 'pm25'].sort_values('datetimeLocal')
ultimos_pm25 = df_pm25.groupby('location_name').last().reset_index()

# --- 6. CONEXIÓN CON GOOGLE SHEETS (SUSCRIPTORES) ---
def guardar_suscriptor(email):
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("suscriptores_aircesfam").sheet1
        sheet.append_row([email, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar suscriptor: {e}")
        return False

def enviar_email_bienvenida(destinatario):
    remitente = EMAIL_REMITENTE
    password = EMAIL_APP_PASSWORD

    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = "✅ Bienvenido al Sistema AirCesfam – Cesfam La Floresta"
    mensaje["From"] = remitente
    mensaje["To"] = destinatario

    cuerpo_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2>¡Hola! Gracias por suscribirte a <strong>AirCesfam</strong> 🌬️</h2>
        <p>Este sistema te mantendrá informado sobre:</p>
        <ul>
            <li>📊 Niveles de PM2.5, PM10 y otros contaminantes en tu zona</li>
            <li>⚠️ Alertas tempranas de alta demanda en urgencias</li>
            <li>👥 Recomendaciones de asignación de personal por turno</li>
            <li>📥 Reportes semanales para gestión del Cesfam La Floresta</li>
        </ul>
        <p>Este sistema apoya la toma de decisiones en la gestión de recursos humanos para mejorar la resolutividad y seguridad del paciente.</p>
        <p>Saludos,<br>
        <strong>Equipo de Gestión - Cesfam La Floresta</strong></p>
        <hr>
        <p><small>¿No solicitaste esto? Puedes ignorar este correo.</small></p>
    </body>
    </html>
    """
    parte_html = MIMEText(cuerpo_html, "html")
    mensaje.attach(parte_html)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, mensaje.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"❌ Error al enviar correo: {e}")
        return False

# --- 7. INTERFAZ DE USUARIO ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Resumen Ejecutivo", 
    "📈 Tendencias", 
    "🌍 Mapa de Alerta", 
    "📋 Gestión de Turnos"
])

# --- TAB 1: RESUMEN ---
with tab1:
    st.subheader("📈 Resumen de Calidad del Aire y Demanda Esperada")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Estaciones", len(ultimos_pm25))
    with col2:
        prom_pm25 = ultimos_pm25['value'].mean()
        st.metric("PM2.5 Promedio", f"{prom_pm25:.1f} µg/m³")
    with col3:
        demanda_media = int(ultimos_pm25['value'].apply(estimar_demanda).mean())
        st.metric("Consultas Esperadas", f"{demanda_media}/día")

    st.markdown("### 🔔 Alertas Activas")
    alertas = ultimos_pm25[ultimos_pm25['nivel'].isin(['Dañino', 'Muy Dañino', 'Peligroso'])]
    if not alertas.empty:
        for _, row in alertas.iterrows():
            st.error(f"🚨 {row['location_name']}: {row['value']:.1f} µg/m³ – {row['nivel']}")
    else:
        st.success("✅ No hay alertas activas.")

# --- TAB 2: TENDENCIAS ---
with tab2:
    st.subheader("Evolución de Contaminantes")
    estaciones = df['location_name'].unique()
    estacion_sel = st.selectbox("Seleccionar estación", estaciones, key="tendencia")
    df_filtrado = df[df['location_name'] == estacion_sel]
    fig = px.line(df_filtrado, x='datetimeLocal', y='value', color='parameter',
                  title=f"Contaminantes en {estacion_sel}",
                  labels={'value': 'Concentración (µg/m³)', 'datetimeLocal': 'Fecha y Hora'})
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 3: MAPA ---
with tab3:
    st.subheader("📍 Mapa de Monitoreo")
    lat_mean = df['latitude'].mean()
    lon_mean = df['longitude'].mean()
    m = folium.Map(location=[lat_mean, lon_mean], zoom_start=8)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in ultimos_pm25.iterrows():
        color_map = {'green': 'green', 'yellow': 'beige', 'orange': 'orange', 'red': 'red', 'purple': 'purple', 'maroon': 'darkred'}
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=f"<b>{row['location_name']}</b><br>PM2.5: {row['value']:.1f} µg/m³<br>Nivel: {row['nivel']}<br>Consultas esperadas: {estimar_demanda(row['value'])}",
            icon=folium.Icon(color=color_map.get(row['color'], 'gray'))
        ).add_to(marker_cluster)

    st_folium(m, width=800, height=600)

# --- TAB 4: GESTIÓN DE TURNOS ---
with tab4:
    st.subheader("📋 Recomendación de Asignación de Personal – Turno")

    turno = st.selectbox("Turno", ["Mañana (8-16)", "Tarde (16-24)", "Noche (0-8)"])
    
    # Simulación: seleccionar estación más cercana al Cesfam
    ubicacion_cesfam = ultimos_pm25.iloc[0]  # Ajustar por filtro real si se conoce
    pm25_actual = ubicacion_cesfam['value']
    nivel = ubicacion_cesfam['nivel']
    consultas_esperadas = estimar_demanda(pm25_actual)

    dotacion_base = 5  # médico, enfermera, técnico, administrativo, aseo
    if pm25_actual <= 12:
        adicional = 0
        recomendacion = "Dotación base suficiente."
    elif pm25_actual <= 35:
        adicional = 1
        recomendacion = "Agregar 1 profesional (preferentemente enfermería o técnico paramédico)."
    elif pm25_actual <= 55:
        adicional = 2
        recomendacion = "Asignar 2 adicionales. Revisar insumos respiratorios."
    else:
        adicional = 3
        recomendacion = "Activar plan de contingencia: 3 adicionales, revisar oxígeno y medicamentos."

    total = dotacion_base + adicional

    st.info(f"""
    **Nivel de Alerta:** {nivel}  
    **PM2.5:** {pm25_actual:.1f} µg/m³  
    **Consultas esperadas:** ~{consultas_esperadas}  
    **Recomendación de dotación:**  
    - **Total sugerido:** {total} profesionales ({adicional} adicionales)  
    - {recomendacion}
    """)

    # Descargar recomendación
    reporte = pd.DataFrame([{
        'Establecimiento': 'Cesfam La Floresta',
        'Turno': turno,
        'PM2.5': pm25_actual,
        'Nivel': nivel,
        'Consultas Esperadas': consultas_esperadas,
        'Dotacion Base': dotacion_base,
        'Adicional': adicional,
        'Total Recomendado': total,
        'Fecha': datetime.now().strftime("%Y-%m-%d %H:%M")
    }])
    csv = reporte.to_csv(index=False).encode('utf-8')

    st.download_button(
        label="📥 Descargar recomendación (CSV)",
        data=csv,
        file_name=f"recomendacion_cesfam_{turno}_{datetime.now().strftime('%H%M')}.csv",
        mime="text/csv"
    )

# --- SIDEBAR: SUSCRIPCIÓN POR CORREO ---
st.sidebar.header("📬 Suscríbete a AirCesfam")
st.sidebar.markdown("Recibe alertas semanales y recomendaciones de gestión.")

with st.sidebar.form(key="form_suscripcion"):
    email = st.text_input("Correo electrónico", placeholder="tu@correo.cl")
    submit = st.form_submit_button("Suscribirse")

if submit:
    if not email or "@" not in email or "." not in email:
        st.sidebar.error("📧 Por favor, ingresa un correo válido.")
    else:
        exito_correo = enviar_email_bienvenida(email)
        exito_guardado = guardar_suscriptor(email)
        
        if exito_guardado:
            if exito_correo:
                st.sidebar.success(f"✅ ¡Gracias, {email}! Revisa tu bandeja de entrada.")
            else:
                st.sidebar.warning(f"✅ Suscrito. Pronto recibirás información.")
        else:
            st.sidebar.error("Hubo un problema al registrar tu suscripción.")

# --- PIE DE PÁGINA ---
st.sidebar.markdown("---")
st.sidebar.write(f"📅 Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
st.sidebar.caption("Sistema desarrollado para el Cesfam La Floresta – Gestión 2025")