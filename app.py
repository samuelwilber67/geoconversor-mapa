`python
import streamlit as st
import pandas as pd
import simplekml
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time
import io

Configuração da página
st.set_page_config(page_title="Conversor MAPA: Município para KML", layout="wide")

st.title("📍 Localizador de Convênios (Excel para KML)")
st.markdown("""
Esta ferramenta busca a localização de municípios brasileiros e gera um arquivo KML para o Google Earth.
Campos necessários no Excel: Nº do convênio, UF, Município.
""")

Inicializa o buscador (Nominatim)
geolocator = Nominatim(user_agent="mapa_geocoder_v1_samuel")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)

uploaded_file = st.file_uploader("Escolha o arquivo Excel", type=['xlsx', 'xls'])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.write("### Prévia dos dados carregados:")
        st.dataframe(df.head())

        cols = df.columns.tolist()
        col_convenio = st.selectbox("Selecione a coluna do Nº do Convênio", cols)
        col_municipio = st.selectbox("Selecione a coluna do Município", cols)
        col_uf = st.selectbox("Selecione a coluna da UF", cols)

        if st.button("Gerar Arquivo KML"):
            kml = simplekml.Kml()
            pontos_encontrados = 0
            pontos_nao_encontrados = []

            progress_bar = st.progress(0)
            status_text = st.empty()

            for index, row in df.iterrows():
                percent = (index + 1) / len(df)
                progress_bar.progress(percent)
                
                mun = str(row[col_municipio]).strip()
                uf = str(row[col_uf]).strip()
                conv = str(row[col_convenio]).strip()

                if mun == 'nan' or uf == 'nan':
                    continue

                endereco_busca = f"{mun}, {uf}, Brasil"
                status_text.text(f"Processando {index+1}/{len(df)}: {endereco_busca}")

                try:
                    location = geolocator.geocode(endereco_busca)
                    if location:
                        pnt = kml.newpoint(name=conv)
                        pnt.coords = [(location.longitude, location.latitude)]
                        pnt.description = f"Município: {mun} - {uf}\nConvênio: {conv}"
                        pontos_encontrados += 1
                    else:
                        pontos_nao_encontrados.append(endereco_busca)
                except Exception as e:
                    st.warning(f"Erro ao buscar {endereco_busca}: {e}")
                    time.sleep(2)
                
                time.sleep(0.1) 

            status_text.text("Processamento concluído!")
            st.success(f"Sucesso! {pontos_encontrados} pontos localizados.")
            
            if pontos_nao_encontrados:
                st.warning(f"{len(pontos_nao_encontrados)} municípios não foram encontrados.")
                with st.expander("Ver lista de não encontrados"):
                    for item in pontos_nao_encontrados:
                        st.write(f"- {item}")

            kml_output = kml.kml()
            st.download_button(
                label="💾 Baixar Arquivo KML",
                data=kml_output,
                file_name="convenios_geolocalizados.kml",
                mime="application/vnd.google-earth.kml+xml"
            )
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
`