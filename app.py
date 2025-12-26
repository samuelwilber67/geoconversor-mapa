import streamlit as st
import pandas as pd
import simplekml
from geopy.geocoders import ArcGIS
import time

# Configuração da interface
st.set_page_config(page_title="MAPA - Geoprocessamento de Convênios", layout="wide")
st.title("📍 Sistema de Geocodificação de Convênios (MAPA)")
st.markdown("---")

# Dicionário de Capitais para Alocação Automática
CAPITAIS = {
    'AC': 'Rio Branco', 'AL': 'Maceió', 'AP': 'Macapá', 'AM': 'Manaus',
    'BA': 'Salvador', 'CE': 'Fortaleza', 'DF': 'Brasília', 'ES': 'Vitória',
    'GO': 'Goiânia', 'MA': 'São Luís', 'MT': 'Cuiabá', 'MS': 'Campo Grande',
    'MG': 'Belo Horizonte', 'PA': 'Belém', 'PB': 'João Pessoa', 'PR': 'Curitiba',
    'PE': 'Recife', 'PI': 'Teresina', 'RJ': 'Rio de Janeiro', 'RN': 'Natal',
    'RS': 'Porto Alegre', 'RO': 'Porto Velho', 'RR': 'Boa Vista', 'SC': 'Florianópolis',
    'SP': 'São Paulo', 'SE': 'Aracaju', 'TO': 'Palmas'
}

def limpar_nome(nome):
    nome = str(nome).upper()
    termos = ["MUNICIPIO DE ", "PREFEITURA DE ", "GOVERNO DE ", "PM DE ", "PREFEITURA MUNICIPAL DE "]
    for termo in termos:
        nome = nome.replace(termo, "")
    return nome.strip()

geolocator = ArcGIS(timeout=10)

uploaded_file = st.file_uploader("Suba sua planilha Excel (Suporta 1000+ linhas)", type=['xlsx', 'xls'])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    cols = df.columns.tolist()
    
    st.sidebar.header("Configurações de Colunas")
    col_conv = st.sidebar.selectbox("Coluna Nº Convênio", cols)
    col_mun = st.sidebar.selectbox("Coluna Município", cols)
    col_uf = st.sidebar.selectbox("Coluna UF", cols)

    if st.button("🚀 Iniciar Processamento Geográfico"):
        kml = simplekml.Kml()
        pontos_municipio = 0
        pontos_estado = 0
        erros = []
        cache = {}
        
        progress_bar = st.progress(0)
        status_msg = st.empty()

        for i, row in df.iterrows():
            progress_bar.progress((i + 1) / len(df))
            
            mun_raw = str(row[col_mun]).strip()
            uf = str(row[col_uf]).strip().upper()
            convenio = str(row[col_conv]).strip()
            
            # Lógica de Identificação: Convênio com o Estado
            is_estado = False
            if mun_raw == "" or pd.isna(row[col_mun]) or "ESTADO DE" in mun_raw.upper() or mun_raw.upper() == "ESTADO":
                is_estado = True
                mun_limpo = CAPITAIS.get(uf, "Brasília")
                aviso_texto = "⚠️ CONVÊNIO COM O GOVERNO DO ESTADO"
            else:
                mun_limpo = limpar_nome(mun_raw)
                aviso_texto = f"Município: {mun_raw}"

            query = f"{mun_limpo}, {uf}, Brasil"
            status_msg.text(f"Processando {i+1}/{len(df)}: {query}")

            if query in cache:
                location = cache[query]
            else:
                try:
                    location = geolocator.geocode(query)
                    cache[query] = location
                except:
                    location = None

            if location:
                pnt = kml.newpoint(name=convenio)
                pnt.coords = [(location.longitude, location.latitude)]
                
                # Montagem da Descrição no Google Earth
                pnt.description = f"{aviso_texto}\n\nUF: {uf}\nConvênio: {convenio}"
                
                # Estilização Visual
                if is_estado:
                    # Marcador Vermelho para Governo do Estado
                    pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png'
                    pontos_estado += 1
                else:
                    # Marcador Azul para Municípios Identificados
                    pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/blu-circle.png'
                    pontos_municipio += 1
            else:
                erros.append({"Linha": i+2, "Convênio": convenio, "Local": query, "Erro": "Não localizado"})

        status_msg.empty()
        st.success("Processamento concluído com sucesso!")
        
        # Painel de Resumo
        c1, c2, c3 = st.columns(3)
        c1.metric("Municípios", pontos_municipio)
        c2.metric("Governo do Estado", pontos_estado)
        c3.metric("Falhas", len(erros))

        if (pontos_municipio + pontos_estado) > 0:
            st.download_button(
                label="💾 BAIXAR ARQUIVO KML (GOOGLE EARTH)",
                data=kml.kml(),
                file_name="convenios_infra_mapa.kml",
                mime="application/vnd.google-earth.kml+xml"
            )

        if erros:
            with st.expander("Ver detalhes de falhas"):
                st.table(pd.DataFrame(erros))
