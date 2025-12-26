import streamlit as st
import pandas as pd
import simplekml
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time

# Configuração da interface
st.set_page_config(page_title="Geoconversor MAPA v2", layout="wide")
st.title("📍 Localizador de Convênios MAPA")
st.markdown("---")

# Inicializa o buscador com um identificador único para evitar bloqueios
geolocator = Nominatim(user_agent="mapa_geocoder_samuel_v2_2025")
# RateLimiter garante que não faremos mais de 1 busca por segundo (regra do serviço gratuito)
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.2, return_value_on_exception=None)

uploaded_file = st.file_uploader("Suba sua planilha Excel com Município, UF e Convênio", type=['xlsx', 'xls'])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    cols = df.columns.tolist()
    
    st.info(f"Planilha carregada com {len(df)} linhas.")
    
    # Seleção de colunas
    c1, c2, c3 = st.columns(3)
    with c1: col_conv = st.selectbox("Coluna Nº Convênio", cols)
    with c2: col_mun = st.selectbox("Coluna Município", cols)
    with c3: col_uf = st.selectbox("Coluna UF", cols)

    if st.button("🚀 Iniciar Processamento Geográfico"):
        kml = simplekml.Kml()
        resultados_debug = []
        pontos_adicionados = 0
        
        progress_bar = st.progress(0)
        status_msg = st.empty()

        for i, row in df.iterrows():
            # Atualiza progresso
            progress_bar.progress((i + 1) / len(df))
            
            # Limpa e formata os dados
            municipio = str(row[col_mun]).strip()
            uf = str(row[col_uf]).strip()
            convenio = str(row[col_conv]).strip()
            
            # Monta a query de busca
            query = f"{municipio}, {uf}, Brasil"
            status_msg.text(f"Processando {i+1}/{len(df)}: {query}")

            try:
                location = geolocator.geocode(query)
                if location:
                    # Adiciona o ponto ao KML
                    pnt = kml.newpoint(name=convenio)
                    pnt.coords = [(location.longitude, location.latitude)]
                    pnt.description = f"Município: {municipio}-{uf}\nConvênio: {convenio}"
                    
                    resultados_debug.append({"Convênio": convenio, "Busca": query, "Status": "✅ Encontrado", "Lat/Long": f"{location.latitude}, {location.longitude}"})
                    pontos_adicionados += 1
                else:
                    resultados_debug.append({"Convênio": convenio, "Busca": query, "Status": "❌ Não Localizado", "Lat/Long": "-"})
            except Exception as e:
                resultados_debug.append({"Convênio": convenio, "Busca": query, "Status": f"⚠️ Erro: {str(e)}", "Lat/Long": "-"})
                time.sleep(2) # Pausa maior se houver erro de conexão

        # Exibe tabela de resultados para conferência
        st.write("### Relatório de Processamento")
        st.table(pd.DataFrame(resultados_debug))

        if pontos_adicionados > 0:
            st.success(f"Sucesso! {pontos_adicionados} pontos foram inseridos no arquivo KML.")
            st.download_button(
                label="💾 Baixar Arquivo KML Final",
                data=kml.kml(),
                file_name="mapa_convenios_mapa.kml",
                mime="application/vnd.google-earth.kml+xml"
            )
        else:
            st.error("Nenhum ponto foi encontrado. Verifique se os nomes dos municípios e UFs estão corretos na planilha.")
