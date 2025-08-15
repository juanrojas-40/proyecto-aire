# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# --- 1. CARGA DE VARIABLES DE ENTORNO ---
from dotenv import load_dotenv
import os

# Cargar variables del archivo .env
load_dotenv()

# Obtener credenciales (si no existen, se asigna None)
EMAIL_REMITENTE = os.getenv("EMAIL_REMITENTE")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

# Validación de credenciales
if not EMAIL_REMITENTE or not EMAIL_APP_PASSWORD:
    st.error("❌ Error de configuración: No se encontraron las credenciales en el archivo .env")
    st.stop()

# --- 2. GENERACIÓN DE DATOS ALEATORIOS ---
def generar_datos_aleatorios():
    fechas = pd.date_range(start='2025-08-11 21:00', periods=7, freq='h')
    data = {
        'Fecha y hora': fechas,
        'MP 10': [80, 34, 13, 14, 21, 17, 5],
        'MP 2,5': [79, 33, 12, 13, 19, 15, 5],
        'SO2': [12.54, 12.12, 11.74, 11.82, 11.64, 11.93, 11.2],
        'NO2': [0.52, 0.47, 0.87, 0.87, 0.87, 0.87, 0.87],
        'CO': [1.42, 1.01, 0.73, 0.74, 0.74, 0.68, 0.51],
        'O3': [13, 14, 15, 14, 15, 16, 16]
    }
    return pd.DataFrame(data)

df = generar_datos_aleatorios()

# --- 3. FUNCIÓN PARA ENVIAR EMAIL DE BIENVENIDA ---
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
tab1, tab2, tab3 = st.tabs(["📊 Datos", "📈 Gráficos", "🌍 Mapa"])

with tab1:
    st.subheader("Datos de Calidad del Aire (Simulados)")
    st.dataframe(df)

with tab2:
    st.subheader("Tendencias de Contaminantes")
    df_long = pd.melt(df, id_vars=['Fecha y hora'], var_name='Contaminante', value_name='Valor')
    fig = px.line(df_long, x='Fecha y hora', y='Valor', color='Contaminante', title="Evolución de Contaminantes")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("📍 Mapa de Calidad del Aire (Simulado)")
    ubicaciones = {
        'Santiago': [-33.45694, -70.66927],
        'Temuco': [-38.9333, -72.6500],
        'Concepción': [-36.8187, -73.0573],
        'Valparaíso': [-33.0493, -71.5442]
    }
    estacion = st.selectbox("Seleccionar Estación", list(ubicaciones.keys()))
    lat, lon = ubicaciones[estacion]

    m = folium.Map(location=[lat, lon], zoom_start=12)
    marker_cluster = MarkerCluster().add_to(m)
    folium.Marker(location=[lat, lon], popup=estacion, tooltip=estacion).add_to(marker_cluster)
    st_folium(m, width=800, height=600)

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
        if enviar_email_bienvenida(email):
            st.sidebar.success(f"✅ ¡Gracias, {email}! Revisa tu bandeja de entrada.")
        else:
            st.sidebar.warning(f"✅ Gracias por suscribirte, {email}. Hubo un problema con el correo, pero tu suscripción es válida.")

# --- 6. GUARDAR SUSCRIPTORES (opcional) ---
try:
    suscriptores = pd.read_csv("suscriptores.csv")
except FileNotFoundError:
    suscriptores = pd.DataFrame(columns=["email", "fecha"])

nuevo = pd.DataFrame([{"email": email, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
suscriptores = pd.concat([suscriptores, nuevo], ignore_index=True)
suscriptores.to_csv("suscriptores.csv", index=False)