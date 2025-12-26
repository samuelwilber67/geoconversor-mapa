import streamlit as st
import pandas as pd
import simplekml
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time

# Configuração da interface
st.set_page_config(page_title="Geoconversor MAPA", layout="wide")
st.title("📍 Conversor de Convênios: Município para KML")

# Inicializa o buscador gratuito (Nominatim/OpenStreetMap)
geolocator = Nominatim(user_agent="mapa_geocoder_v1_samuel")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)

uploaded_file = st.file_uploader("Suba sua planilha Excel", type=['xlsx', 'xls'])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    cols = df.columns.tolist()
    
    # Seleção de colunas pelo usuário
    c1, c2, c3 = st.columns(3)
    with c1: col_conv = st.selectbox("Coluna Nº Convênio", cols)
    with c2: col_mun = st.selectbox("Coluna Município", cols)
    with c3: col_uf = st.selectbox("Coluna UF", cols)

    if st.button("🚀 Iniciar Geolocalização"):
        kml = simplekml.Kml()
        encontrados = 0
        falhas = []
        
        bar = st.progress(0)
        status = st.empty()

        for i, row in df.iterrows():
            bar.progress((i + 1) / len(df))
            mun, uf, n_conv = str(row[col_mun]), str(row[col_uf]), str(row[col_conv])
            query = f"{mun}, {uf}, Brasil"
            status.text(f"Buscando: {query}")

            try:
                loc = geolocator.geocode(query)
                if loc:
                    pnt = kml.newpoint(name=n_conv)
                    pnt.coords = [(loc.longitude, loc.latitude)]
                    pnt.description = f"Município: {mun}-{uf}\nConvênio: {n_conv}"
                    encontrados += 1
                else:
                    falhas.append(query)
            except:
                time.sleep(2)
            
            time.sleep(0.1)

        st.success(f"Concluído! {encontrados} pontos gerados.")
        if falhas:
            st.warning(f"{len(falhas)} municípios não localizados.")
            with st.expander("Ver lista de falhas"):
                st.write(falhas)

        # Download do arquivo final
        st.download_button("💾 Baixar KML para Google Earth", kml.kml(), "mapa_convenios.kml")
