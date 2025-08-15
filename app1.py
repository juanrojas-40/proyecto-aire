# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import folium
from folium.plugins import MarkerCluster  # ✅ Importación crítica
from streamlit_folium import st_folium

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="AirAlert Chile", layout="wide")
st.title("🌬️ AirAlert: Sistema de Alerta Ciudadana para Calidad del Aire")

# --- 2. GENERACIÓN DE DATOS ALEATORIOS ---
def generar_datos_aleatorios():
    """Genera datos simulados de calidad del aire"""
    fechas = pd.date_range(start='2025-08-11 21:00', periods=7, freq='h')  # ✅ 'h' en minúscula

    data = {
        'Fecha y hora': fechas,
        'MP 10': [80, 34, 13, 14, 21, 17, 5],
        'MP 2,5': [79, 33, 12, 13, 19, 15, 5],
        'SO2': [12.54, 12.12, 11.74, 11.82, 11.64, 11.93, 11.2],
        'NO2': [0.52, 0.47, 0.87, 0.87, 0.87, 0.87, 0.87],
        'CO': [1.42, 1.01, 0.73, 0.74, 0.74, 0.68, 0.51],
        'O3': [13, 14, 15, 14, 15, 16, 16]
    }
    df = pd.DataFrame(data)
    return df

# Generar datos
df = generar_datos_aleatorios()

# --- 3. INTERFAZ ---
tab1, tab2, tab3 = st.tabs(["📊 Datos", "📈 Gráficos", "🌍 Mapa"])

# --- PESTAÑA 1: TABLA DE DATOS ---
with tab1:
    st.subheader("Datos de Calidad del Aire (Simulados)")
    st.dataframe(df)

# --- PESTAÑA 2: GRÁFICOS ---
with tab2:
    st.subheader("Tendencias de Contaminantes")
    
    # Gráfico de líneas
    df_long = pd.melt(df, id_vars=['Fecha y hora'], var_name='Contaminante', value_name='Valor')
    fig = px.line(df_long, x='Fecha y hora', y='Valor', color='Contaminante', title="Evolución de Contaminantes")
    st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 3: MAPA INTERACTIVO ---
with tab3:
    st.subheader("📍 Mapa de Calidad del Aire (Simulado)")

    # Coordenadas ficticias de estaciones en Chile
    ubicaciones = {
        'Santiago': [-33.45694, -70.66927],
        'Temuco': [-38.9333, -72.6500],
        'Concepción': [-36.8187, -73.0573],
        'Valparaíso': [-33.0493, -71.5442]
    }

    # Selección de estación
    estacion = st.selectbox("Seleccionar Estación", list(ubicaciones.keys()))
    lat, lon = ubicaciones[estacion]

    # Crear mapa
    m = folium.Map(location=[lat, lon], zoom_start=12, tiles="OpenStreetMap")

    # ✅ Crear y agregar MarkerCluster
    marker_cluster = MarkerCluster().add_to(m)  # ✅ Ahora está definido

    # Añadir marcador
    folium.Marker(
        location=[lat, lon],
        popup=f"<b>{estacion}</b><br>Última medición: {df['MP 2,5'].iloc[-1]} µg/m³",
        tooltip=estacion
    ).add_to(marker_cluster)

    # Mostrar mapa en Streamlit
    st_folium(m, width=800, height=600)

# --- 4. SISTEMA DE SUSCRIPCIÓN ---
st.sidebar.markdown("---")
st.sidebar.subheader("📬 Suscríbete al Reporte Diario")

with st.sidebar.form(key="form_suscripcion"):
    email = st.text_input("Correo electrónico", placeholder="tu@correo.cl")
    submit = st.form_submit_button("Suscribirse")

if submit:
    if not email or "@" not in email or "." not in email:
        st.sidebar.error("Por favor, ingresa un correo válido.")
    else:
        st.sidebar.success(f"✅ ¡Gracias, {email}! Recibirás un reporte diario.")

# --- 5. ESTADÍSTICAS ---
st.sidebar.markdown("---")
st.sidebar.write("### 📊 Últimos Valores")
st.sidebar.write(f"**PM2.5:** {df['MP 2,5'].iloc[-1]} µg/m³")
st.sidebar.write(f"**PM10:** {df['MP 10'].iloc[-1]} µg/m³")
st.sidebar.write(f"**O3:** {df['O3'].iloc[-1]} ppb")

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def enviar_email_bienvenida(destinatario):
    """
    Envía un correo de bienvenida al usuario suscrito.
    """
    # Configuración del remitente
    remitente = "prefereport@gmail.com"
    app_password = "tu_app_password_aqui"  # Reemplaza con tu App Password

    # Crear mensaje
    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = "¡Bienvenido al Reporte de Calidad del Aire! 🌿"
    mensaje["From"] = remitente
    mensaje["To"] = destinatario

    # Cuerpo del correo en HTML
    cuerpo_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2>¡Hola, gracias por suscribirte! 🌬️</h2>
        <p>Te damos la bienvenida a <strong>AirAlert Chile</strong>, tu aliado para mantener el aire limpio y seguro.</p>
        
        <p>Con este reporte diario, recibirás:</p>
        <ul>
            <li>🔍 Niveles de PM2.5, PM10, O₃ y otros contaminantes</li>
            <li>📊 Recomendaciones personalizadas según la calidad del aire</li>
            <li>📍 Alertas para tu ciudad</li>
        </ul>

        <p>Próximamente recibirás tu primer reporte. Mientras tanto, visita nuestra plataforma: <a href="http://localhost:8501" target="_blank">AirAlert Dashboard</a></p>

        <p>Saludos,<br>
        <strong>Equipo AirAlert</strong><br>
        <em>Preferencia Report - Calidad del Aire en Chile</em></p>

        <hr>
        <p><small>¿No solicitaste esto? Puedes ignorar este correo o <a href="#">darte de baja</a>.</small></p>
    </body>
    </html>
    """

    parte_html = MIMEText(cuerpo_html, "html")
    mensaje.attach(parte_html)

    # Conexión al servidor SMTP de Gmail
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()  # Habilitar seguridad
        server.login(remitente, app_password)
        server.sendmail(remitente, destinatario, mensaje.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"❌ No se pudo enviar el correo: {e}")
        return False


if submit:
    if not email or "@" not in email or "." not in email:
        st.sidebar.error("Por favor, ingresa un correo válido.")
    else:
        # ✅ Enviar correo de bienvenida
        if enviar_email_bienvenida(email):
            st.sidebar.success(f"✅ ¡Gracias, {email}! Hemos enviado un correo de bienvenida.")
        else:
            st.sidebar.warning(f"✅ Gracias por suscribirte, {email}. Hubo un problema con el correo de bienvenida, pero tu suscripción es válida.")

        # Opcional: guardar en CSV
        with open("suscriptores.csv", "a") as f:
            f.write(f"{email},{pd.Timestamp.now()}\n")