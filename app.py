import streamlit as st
import pandas as pd
import simplekml
from geopy.geocoders import ArcGIS
import time

# Configuração da interface
st.set_page_config(page_title="MAPA - Geoprocessamento Alta Performance", layout="wide")
st.title("📍 Sistema de Geocodificação de Convênios (Versão Ultra)")
st.markdown("---")

# Função para limpar nomes
def limpar_nome(nome):
    nome = str(nome).upper()
    termos = ["MUNICIPIO DE ", "PREFEITURA DE ", "GOVERNO DE ", "PM DE "]
    for termo in termos:
        nome = nome.replace(termo, "")
    return nome.strip()

# MUDANÇA CRÍTICA: Trocamos Nominatim por ArcGIS
# O ArcGIS é muito mais rápido e não exige chaves para buscas simples
geolocator = ArcGIS(timeout=10)

uploaded_file = st.file_uploader("Suba sua planilha Excel (Suporta 1000+ linhas)", type=['xlsx', 'xls'])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    cols = df.columns.tolist()
    
    st.sidebar.header("Configurações")
    col_conv = st.sidebar.selectbox("Coluna Nº Convênio", cols)
    col_mun = st.sidebar.selectbox("Coluna Município", cols)
    col_uf = st.sidebar.selectbox("Coluna UF", cols)

    if st.button("🚀 Iniciar Processamento Rápido"):
        kml = simplekml.Kml()
        pontos_ok = 0
        erros = []
        cache = {} # Evita buscar o mesmo município várias vezes
        
        progress_bar = st.progress(0)
        status_msg = st.empty()
        
        start_time = time.time()

        for i, row in df.iterrows():
            progress_bar.progress((i + 1) / len(df))
            
            mun_limpo = limpar_nome(row[col_mun])
            uf = str(row[col_uf]).strip()
            convenio = str(row[col_conv]).strip()
            
            query = f"{mun_limpo}, {uf}, Brasil"
            status_msg.text(f"Processando {i+1}/{len(df)}: {query}")

            # Lógica de Cache para acelerar ainda mais
            if query in cache:
                location = cache[query]
            else:
                try:
                    # ArcGIS é quase instantâneo, não precisa de RateLimiter lento
                    location = geolocator.geocode(query)
                    cache[query] = location
                except Exception as e:
                    location = None
                    erros.append({"Linha": i+2, "Convênio": convenio, "Erro": "Falha na conexão"})

            if location:
                pnt = kml.newpoint(name=convenio)
                pnt.coords = [(location.longitude, location.latitude)]
                pnt.description = f"Município: {row[col_mun]}\nUF: {uf}\nConvênio: {convenio}"
                pontos_ok += 1
            else:
                erros.append({"Linha": i+2, "Convênio": convenio, "Erro": "Município não encontrado"})

        end_time = time.time()
        tempo_total = round(end_time - start_time, 2)
        
        status_msg.empty()
        st.success(f"Concluído! {pontos_ok} pontos gerados em {tempo_total} segundos.")

        if pontos_ok > 0:
            st.download_button(
                label="💾 BAIXAR ARQUIVO KML",
                data=kml.kml(),
                file_name="pontos_convenios_mapa.kml",
                mime="application/vnd.google-earth.kml+xml"
            )

        if erros:
            with st.expander("Ver detalhes de problemas"):
                st.table(pd.DataFrame(erros))
