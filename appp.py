import requests
import pandas as pd

def obtener_datos_openaq():
    url = "https://api.openaq.org/v2/measurements"
    params = {
        'country': 'CL',
        'date_from': '2025-08-08T21:15:00Z',
        'date_to': '2025-08-08T21:47:00Z',
        'limit': 1000
    }
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if 'results' in data:
            df = pd.json_normalize(data['results'])
            return df
    return pd.DataFrame()

# Carga datos reales
df = obtener_datos_openaq()

if df.empty:
    st.error("❌ No se pudieron obtener datos de OpenAQ.")
else:
    st.success(f"✅ Datos cargados: {len(df)} mediciones")
    st.write(df[['date.utc', 'location', 'parameter', 'value', 'unit', 'coordinates.latitude', 'coordinates.longitude']].head())