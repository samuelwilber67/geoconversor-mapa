import streamlit as st
import pandas as pd
import simplekml
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time
import re

# Configuração da interface
st.set_page_config(page_title="MAPA - Geoprocessamento Pro", layout="wide")
st.title("📍 Sistema de Geocodificação de Convênios (Escala 1000+)")
st.markdown("---")

def limpar_nome_municipio(nome):
    """Remove termos burocráticos que atrapalham a busca geográfica"""
    nome = str(nome).upper()
    termos = ["MUNICIPIO DE ", "PREFEITURA DE ", "PREFEITURA MUNICIPAL DE ", "GOVERNO DE "]
    for termo in termos:
        nome = nome.replace(termo, "")
    return nome.strip()

# Inicializa o buscador com timeout estendido
geolocator = Nominatim(user_agent="mapa_infra_v3_2025", timeout=10)
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.5, max_retries=3, error_wait_seconds=2)

uploaded_file = st.file_uploader("Suba sua planilha Excel (Suporta até 1000+ linhas)", type=['xlsx', 'xls'])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    cols = df.columns.tolist()
    
    st.sidebar.header("Configurações de Colunas")
    col_conv = st.sidebar.selectbox("Coluna Nº Convênio", cols)
    col_mun = st.sidebar.selectbox("Coluna Município", cols)
    col_uf = st.sidebar.selectbox("Coluna UF", cols)

    st.warning(f"Atenção: Processar {len(df)} linhas levará aproximadamente {round(len(df)*1.6/60)} minutos devido aos limites da API gratuita.")

    if st.button("🚀 Iniciar Processamento em Lote"):
        kml = simplekml.Kml()
        cache_coordenadas = {}
        logs = []
        pontos_ok = 0
        
        progress_bar = st.progress(0)
        status_msg = st.empty()

        for i, row in df.iterrows():
            progress_bar.progress((i + 1) / len(df))
            
            # Limpeza e preparação
            mun_original = str(row[col_mun])
            mun_limpo = limpar_nome_municipio(mun_original)
            uf = str(row[col_uf]).strip()
            convenio = str(row[col_conv]).strip()
            
            query = f"{mun_limpo}, {uf}, Brasil"
            status_msg.text(f"Processando {i+1}/{len(df)}: {query}")

            # Verifica se já buscamos esse município para ganhar tempo
            if query in cache_coordenadas:
                location = cache_coordenadas[query]
            else:
                try:
                    location = geolocator.geocode(query)
                    cache_coordenadas[query] = location
                except Exception as e:
                    location = None
                    logs.append({"Linha": i+2, "Convênio": convenio, "Busca": query, "Erro": "Timeout/Conexão"})

            if location:
                pnt = kml.newpoint(name=convenio)
                pnt.coords = [(location.longitude, location.latitude)]
                pnt.description = f"Município: {mun_original}\nUF: {uf}\nConvênio: {convenio}"
                pontos_ok += 1
            else:
                logs.append({"Linha": i+2, "Convênio": convenio, "Busca": query, "Erro": "Não encontrado"})

        # Finalização
        status_msg.success(f"Processamento concluído! {pontos_ok} pontos gerados.")
        
        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            if pontos_ok > 0:
                st.download_button(
                    label="💾 Baixar KML (Google Earth)",
                    data=kml.kml(),
                    file_name="convenios_mapa.kml",
                    mime="application/vnd.google-earth.kml+xml"
                )
        
        with col_dl2:
            if logs:
                df_logs = pd.DataFrame(logs)
                st.download_button(
                    label="⚠️ Baixar Relatório de Erros (CSV)",
                    data=df_logs.to_csv(index=False).encode('utf-8'),
                    file_name="erros_geolocalizacao.csv",
                    mime="text/csv"
                )
                st.error(f"{len(logs)} linhas apresentaram problemas. Verifique o relatório.")
