# app.py
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
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 6. CONEXIÓN CON GOOGLE SHEETS ---
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

def guardar_suscriptor(email):
    """
    Guarda un nuevo suscriptor en Google Sheets.
    """
    try:
        # Configuración de autenticación
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)

        # Abre la hoja de cálculo por nombre
        sheet = client.open("suscriptores_airalert").sheet1  # Asegúrate del nombre

        # Agrega una nueva fila
        sheet.append_row([
            email,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar suscriptor: {e}")
        return False
    
import os


# Opcional: Verifica que el archivo existe
#if not os.path.exists("credentials.json"):
#    st.warning("⚠️ Archivo credentials.json no encontrado. Asegúrate de haberlo subido.")
#else:
#    st.write("✅ Credenciales de Google Sheets cargadas")

#try:
#    import gspread
#    st.write("✅ gspread instalado correctamente")
#except Exception as e:
#    st.error(f"❌ Error al importar gspread: {e}")



# Diagnóstico de secretos
#st.sidebar.subheader("🔧 Diagnóstico de secretos")
#try:
#    st.sidebar.write("EMAIL_REMITENTE:", st.secrets["EMAIL_REMITENTE"])
#    st.sidebar.write("EMAIL_APP_PASSWORD:", "✅ Cargado" if st.secrets["EMAIL_APP_PASSWORD"] else "❌ Vacío")
#except Exception as e:
#    st.sidebar.error(f"No se pudieron leer los secretos: {e}")


# --- 1. CARGA DE CREDENCIALES SEGURAS ---
# Cargar .env solo si existe (modo desarrollo)
if os.path.exists(".env"):
    load_dotenv()

# Función para obtener secretos: primero de Streamlit Cloud, luego de .env
def get_secret(key):
    try:
        return st.secrets[key]
    except:
        return os.getenv(key)

# Obtener credenciales
EMAIL_REMITENTE = get_secret("EMAIL_REMITENTE")
EMAIL_APP_PASSWORD = get_secret("EMAIL_APP_PASSWORD")

# Validar que se cargaron
if not EMAIL_REMITENTE or not EMAIL_APP_PASSWORD:
    st.error("❌ Error de configuración: No se encontraron las credenciales. Revisa .env o secrets.toml")
    st.stop()


######################33
# --- FUNCIÓN PARA CARGAR Y UNIR LOS DATOS (se ejecuta solo una vez) ---
@st.cache_data
def cargar_datos_unidos(ruta_carpeta):
    """Carga y une todos los CSV de la carpeta. Usa caché para evitar repetición."""
    
    # Buscar todos los archivos CSV en la carpeta
    patron = os.path.join(ruta_carpeta, "*.csv")
    archivos_csv = glob.glob(patron)

    if not archivos_csv:
        st.error("❌ No se encontraron archivos CSV en la carpeta especificada.")
        return None

    #st.info(f"📁 Se encontraron {len(archivos_csv)} archivos CSV. Uniendo...")

    listado_dataframes = []
    for archivo in archivos_csv:
        try:
            df = pd.read_csv(archivo)
            listado_dataframes.append(df)
            #st.write(f"✔️ Leído: {os.path.basename(archivo)}")
        except Exception as e:
            st.warning(f"❌ Error al leer {os.path.basename(archivo)}: {e}")

    if not listado_dataframes:
        st.error("⚠️ No se pudo cargar ningún archivo correctamente.")
        return None

    # Unir todos los DataFrames
    df_unido = pd.concat(listado_dataframes, ignore_index=True)
    #st.success(f"✅ Datos unidos exitosamente: {len(df_unido)} filas")

    return df_unido

# --- CONFIGURACIÓN ---
ruta_carpeta = r"C:\Users\sucor\OneDrive\Escritorio\UDEC_MAGISTER\VI - TRIMESTRE\PROYECTO INTEGRADO\proyecto-aire"

# --- CARGAR LOS DATOS (esto solo se ejecuta una vez por sesión) ---
df_unido = cargar_datos_unidos(ruta_carpeta)

# Si no hay datos, detener la ejecución
if df_unido is None:
    st.stop()  # Detiene aquí si no hay datos

# --- OPCIONAL: Guardar el CSV solo una vez (evita sobrescritura constante)
# Comenta esta línea si no necesitas el archivo físico
csv_salida = "openaq_todo_junto.csv"
if not os.path.exists(csv_salida):
    try:
        df_unido.to_csv(csv_salida, index=False)
        st.info("💾 Archivo 'openaq_todo_junto.csv' guardado.")
    except PermissionError:
        st.warning("⚠️ No se pudo guardar el archivo (puede estar abierto o bloqueado).")

# --- A PARTIR DE AQUÍ CONTINÚA TU APP (pestañas, gráficos, etc.) ---
# Ejemplo básico:

################################





# --- 3. FUNCIÓN PARA ENVIAR EMAIL DE BIENVENIDA ---
def enviar_email_bienvenida(destinatario):
    remitente = EMAIL_REMITENTE
    password = EMAIL_APP_PASSWORD

    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = "¡Bienvenido al Reporte de Calidad del Aire! 🌿"
    mensaje["From"] = remitente
    mensaje["To"] = destinatario

    cuerpo_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>¡Hola! Gracias por suscribirte a <strong>AirAlert Chile</strong> 🌬️</h2>
        <p>Recibirás reportes diarios sobre la calidad del aire en tu ciudad, con recomendaciones para proteger tu salud.</p>
        <p>Esto incluye:</p>
        <ul>
            <li>🔍 Niveles de PM2.5, PM10, O₃ y otros contaminantes</li>
            <li>📊 Recomendaciones personalizadas según la calidad del aire</li>
            <li>📍 Alertas para tu ciudad</li>
        </ul>
        <p>Saludos,<br>
        <strong>Equipo AirAlert</strong><br>
        <em>Preferencia Report - Calidad del Aire en Chile</em></p>
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

# --- 4. INTERFAZ DE USUARIO ---
# --- 4. INTERFAZ DE USUARIO ---
tab1, tab2, tab3 = st.tabs(["📊 Datos", "📈 Gráficos", "🌍 Mapa"])

with tab1:
    st.subheader("Datos de Calidad del Aire")
    st.dataframe(df_unido)

with tab2:
    st.subheader("Tendencias de Contaminantes")

    # Preparar datos para gráfico (melt)
    df_long = df_unido.copy()
    df_long['Fecha y hora'] = pd.to_datetime(df_long['datetimeLocal'])  # Convertir a fecha legible

    # Seleccionar solo los contaminantes numéricos (evitar valores no numéricos)
    df_long = df_long.dropna(subset=['value'])
    df_long['value'] = pd.to_numeric(df_long['value'], errors='coerce')

    # Filtrar solo datos válidos
    df_long = df_long[df_long['value'].notna()]

    # Melt para gráfico lineal
    df_melt = df_long.melt(
        id_vars=['Fecha y hora', 'location_name', 'parameter'],
        var_name='Contaminante',
        value_name='Valor'
    )

    # Graficar evolución por contaminante
    fig = px.line(
        df_melt,
        x='Fecha y hora',
        y='Valor',
        color='Contaminante',
        title="Evolución de Contaminantes por Estación",
        hover_data={'location_name': True}
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("📍 Mapa de Calidad del Aire")

    # Obtener lista única de estaciones (location_name)
    estaciones_disponibles = df_unido['location_name'].unique()
    estacion_seleccionada = st.selectbox("Seleccionar Estación", estaciones_disponibles)

    # Filtrar datos para la estación seleccionada
    df_estacion = df_unido[df_unido['location_name'] == estacion_seleccionada]

    if not df_estacion.empty:
        # Obtener latitud y longitud de la estación
        lat = df_estacion['latitude'].iloc[0]
        lon = df_estacion['longitude'].iloc[0]

        # Crear mapa con Folium
        m = folium.Map(location=[lat, lon], zoom_start=12)

        # Cluster de marcadores
        marker_cluster = MarkerCluster().add_to(m)

        # Agregar marcador con información
        popup_html = f"""
        <b>Estación:</b> {estacion_seleccionada}<br>
        <b>País:</b> {df_estacion['country_iso'].iloc[0]}<br>
        <b>Proveedor:</b> {df_estacion['provider'].iloc[0]}<br>
        <b>Último valor:</b> {df_estacion['value'].iloc[-1]:.2f} {df_estacion['unit'].iloc[-1]}
        """
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=estacion_seleccionada
        ).add_to(marker_cluster)

        # Mostrar mapa en Streamlit
        st_folium(m, width=800, height=600)
    else:
        st.warning("No se encontraron datos para esta estación.")

# --- 5. SISTEMA DE SUSCRIPCIÓN ---
st.sidebar.markdown("---")
st.sidebar.subheader("📬 Suscríbete al Reporte Diario")

with st.sidebar.form(key="form_suscripcion"):
    email = st.text_input("Correo electrónico", placeholder="tu@correo.cl")
    submit = st.form_submit_button("Suscribirse")

if submit:
    if not email or "@" not in email or "." not in email:
        st.sidebar.error("Por favor, ingresa un correo válido.")
    else:
        # 1. Envía correo de bienvenida
        exito_correo = enviar_email_bienvenida(email)
        
        # 2. Guarda en Google Sheets
        exito_guardado = guardar_suscriptor(email)
        
        # 3. Muestra mensaje
        if exito_guardado:
            if exito_correo:
                st.sidebar.success(f"✅ ¡Gracias, {email}! Revisa tu correo.")
            else:
                st.sidebar.warning(f"✅ Suscrito. Revisa tu correo pronto.")
        else:
            st.sidebar.error("Hubo un problema al guardar tu suscripción.")








# --- 6. GUARDAR SUSCRIPTORES (opcional - solo para desarrollo local) ---
# ⚠️ En Streamlit Cloud, los archivos se borran al reiniciar
# Para producción, usa Google Sheets, base de datos o API externa
# Ejemplo comentado:
# try:
#     suscriptores = pd.read_csv("suscriptores.csv")
# except FileNotFoundError:
#     suscriptores = pd.DataFrame(columns=["email", "fecha"])
# 
# nuevo = pd.DataFrame([{"email": email, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
# suscriptores = pd.concat([suscriptores, nuevo], ignore_index=True)
# suscriptores.to_csv("suscriptores.csv", index=False)


