import streamlit as st
import pandas as pd
import simplekml
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time

# Configuração da interface
st.set_page_config(page_title="MAPA - Geoprocessamento Pro", layout="wide")
st.title("📍 Sistema de Geocodificação de Convênios")
st.markdown("---")

# Função para limpar nomes burocráticos
def limpar_nome(nome):
    nome = str(nome).upper()
    for termo in ["MUNICIPIO DE ", "PREFEITURA DE ", "GOVERNO DE ", "PM DE "]:
        nome = nome.replace(termo, "")
    return nome.strip()

# Inicializa o buscador com identificador ÚNICO e timeout alto
# O timeout de 20s ajuda a evitar o erro de 'Read Timeout'
geolocator = Nominatim(user_agent="samuel_wilber_mapa_v4_2025", timeout=20)

# O RateLimiter agora está configurado corretamente para ser usado como função
geocode_service = RateLimiter(geolocator.geocode, min_delay_seconds=1.6, max_retries=3)

uploaded_file = st.file_uploader("Suba sua planilha Excel", type=['xlsx', 'xls'])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    cols = df.columns.tolist()
    
    st.sidebar.header("Configurações")
    col_conv = st.sidebar.selectbox("Coluna Nº Convênio", cols)
    col_mun = st.sidebar.selectbox("Coluna Município", cols)
    col_uf = st.sidebar.selectbox("Coluna UF", cols)

    if st.button("🚀 Iniciar Processamento"):
        kml = simplekml.Kml()
        pontos_ok = 0
        erros = []
        
        progress_bar = st.progress(0)
        status_msg = st.empty()

        for i, row in df.iterrows():
            progress_bar.progress((i + 1) / len(df))
            
            mun_limpo = limpar_nome(row[col_mun])
            uf = str(row[col_uf]).strip()
            convenio = str(row[col_conv]).strip()
            
            # Tentativa 1: Município + UF + Brasil
            query = f"{mun_limpo}, {uf}, Brasil"
            status_msg.text(f"Buscando {i+1}/{len(df)}: {query}")

            try:
                # IMPORTANTE: Usamos o geocode_service (RateLimiter) e não o geolocator direto
                location = geocode_service(query)
                
                # Tentativa 2 (Fallback): Se falhar, tenta apenas Município + UF
                if not location:
                    location = geocode_service(f"{mun_limpo} {uf}")

                if location:
                    pnt = kml.newpoint(name=convenio)
                    pnt.coords = [(location.longitude, location.latitude)]
                    pnt.description = f"Município: {row[col_mun]}\nUF: {uf}\nConvênio: {convenio}"
                    pontos_ok += 1
                else:
                    erros.append({"Linha": i+2, "Convênio": convenio, "Busca": query, "Motivo": "Não encontrado"})
            
            except Exception as e:
                erros.append({"Linha": i+2, "Convênio": convenio, "Busca": query, "Motivo": str(e)})
                time.sleep(2) # Pausa extra em caso de erro de rede

        # Resultados
        status_msg.empty()
        st.success(f"Processamento concluído! {pontos_ok} pontos gerados com sucesso.")

        if pontos_ok > 0:
            # Gerar o KML em memória para download
            kml_output = kml.kml()
            st.download_button(
                label="💾 BAIXAR ARQUIVO KML",
                data=kml_output,
                file_name="pontos_convenios_mapa.kml",
                mime="application/vnd.google-earth.kml+xml"
            )

        if erros:
            with st.expander("Ver detalhes dos erros"):
                st.table(pd.DataFrame(erros))
