import streamlit as st
import pandas as pd
import simplekml
from geopy.geocoders import ArcGIS
import time
import re

# Configuração da interface
st.set_page_config(page_title="MAPA - Geoprocessamento Inteligente", layout="wide")
st.title("📍 Sistema de Geocodificação (Sem Cabeçalho)")
st.markdown("---")

CAPITAIS = {
    'AC': 'Rio Branco', 'AL': 'Maceió', 'AP': 'Macapá', 'AM': 'Manaus',
    'BA': 'Salvador', 'CE': 'Fortaleza', 'DF': 'Brasília', 'ES': 'Vitória',
    'GO': 'Goiânia', 'MA': 'São Luís', 'MT': 'Cuiabá', 'MS': 'Campo Grande',
    'MG': 'Belo Horizonte', 'PA': 'Belém', 'PB': 'João Pessoa', 'PR': 'Curitiba',
    'PE': 'Recife', 'PI': 'Teresina', 'RJ': 'Rio de Janeiro', 'RN': 'Natal',
    'RS': 'Porto Alegre', 'RO': 'Porto Velho', 'RR': 'Boa Vista', 'SC': 'Florianópolis',
    'SP': 'São Paulo', 'SE': 'Aracaju', 'TO': 'Palmas'
}

def detectar_colunas_por_conteudo(df):
    """Analisa o conteúdo da primeira linha para adivinhar as colunas"""
    mapeamento = {}
    if df.empty: return mapeamento
    
    primeira_linha = df.iloc[0]
    for i, valor in enumerate(primeira_linha):
        val_str = str(valor).strip().upper()
        
        # Detecta UF (Exatamente 2 letras)
        if len(val_str) == 2 and val_str.isalpha() and 'uf' not in mapeamento:
            mapeamento['uf'] = i
        
        # Detecta Percentual (Tem % ou é um número entre 0 e 100)
        elif '%' in val_str or (isinstance(valor, (int, float)) and 0 <= valor <= 100):
            if 'percentual' not in mapeamento: mapeamento['percentual'] = i
            
        # Detecta Convênio (Número longo)
        elif val_str.isdigit() and len(val_str) > 4:
            if 'convenio' not in mapeamento: mapeamento['convenio'] = i
            
        # Detecta Município (Texto que não é UF)
        elif len(val_str) > 2 and not val_str.isdigit():
            if 'municipio' not in mapeamento: mapeamento['municipio'] = i
            
    return mapeamento

def obter_estilo_execucao(valor):
    try:
        v = float(str(valor).replace('%', '').replace(',', '.'))
        if v > 1 and v <= 100: v = v / 100
        if v == 0:
            return 'http://maps.google.com/mapfiles/kml/paddle/blu-circle.png', "0% (Não Iniciada)"
        elif v <= 0.8:
            return 'http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png', f"{v*100:.1f}% (Em Andamento)"
        else:
            return 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png', f"{v*100:.1f}% (Fase Final/Concluída)"
    except:
        return 'http://maps.google.com/mapfiles/kml/paddle/wht-circle.png', "Dado Inválido"

geolocator = ArcGIS(timeout=10)

uploaded_file = st.file_uploader("Suba sua planilha Excel (sem títulos)", type=['xlsx', 'xls'])

if uploaded_file:
    # Lemos COM header=None para não perder a primeira linha de dados
    df = pd.read_excel(uploaded_file, header=None)
    
    # Tenta detectar as colunas pelo que tem dentro delas
    mapa_idx = detectar_colunas_por_conteudo(df)
    
    st.sidebar.header("⚙️ Colunas Detectadas")
    idx_conv = st.sidebar.number_input("Índice Convênio", value=mapa_idx.get('convenio', 0))
    idx_mun = st.sidebar.number_input("Índice Município", value=mapa_idx.get('municipio', 1))
    idx_uf = st.sidebar.number_input("Índice UF", value=mapa_idx.get('uf', 2))
    idx_perc = st.sidebar.number_input("Índice Execução", value=mapa_idx.get('percentual', 3))

    # Filtro por UF
    col_uf = df.columns[idx_uf]
    ufs_disponiveis = sorted(df[col_uf].dropna().unique().tolist())
    ufs_selecionadas = st.multiselect("🌍 Filtrar por UF", ufs_disponiveis, default=ufs_disponiveis)
    df_filtrado = df[df[col_uf].isin(ufs_selecionadas)]

    if st.button("🚀 Gerar Mapa"):
        kml = simplekml.Kml()
        cache = {}
        progress_bar = st.progress(0)
        status_msg = st.empty()

        for i, (idx, row) in enumerate(df_filtrado.iterrows()):
            progress_bar.progress((i + 1) / len(df_filtrado))
            
            mun_raw = str(row[idx_mun]).strip() if pd.notna(row[idx_mun]) else ""
            uf = str(row[idx_uf]).strip().upper()
            convenio = str(row[idx_conv]).strip()
            perc_val = row[idx_perc]

            # Lógica de Estado vs Município
            if mun_raw == "" or "ESTADO" in mun_raw.upper():
                mun_busca = CAPITAIS.get(uf, "Brasília")
                cabecalho = "🏢 CONVÊNIO COM O GOVERNO DO ESTADO"
            else:
                mun_busca = mun_raw
                cabecalho = f"🏙️ Município: {mun_raw}"

            query = f"{mun_busca}, {uf}, Brasil"
            status_msg.text(f"Geocodificando: {query}")

            if query in cache:
                location = cache[query]
            else:
                try:
                    location = geolocator.geocode(query)
                    cache[query] = location
                except: location = None

            if location:
                pnt = kml.newpoint(name=convenio)
                pnt.coords = [(location.longitude, location.latitude)]
                icon_url, perc_texto = obter_estilo_execucao(perc_val)
                pnt.description = f"<b>{cabecalho}</b><br><br><b>UF:</b> {uf}<br><b>Convênio:</b> {convenio}<br><b>Execução:</b> {perc_texto}"
                pnt.style.iconstyle.icon.href = icon_url
            
        st.success("Mapa gerado!")
        st.download_button("💾 BAIXAR KML", kml.kml(), "mapa_convenios.kml")
