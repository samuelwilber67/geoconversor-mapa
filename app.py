import streamlit as st
import pandas as pd
import simplekml
from geopy.geocoders import ArcGIS
import time
import re

# Configuração da interface
st.set_page_config(page_title="MAPA - Precisão Geográfica", layout="wide")
st.title("📍 Geocodificador de Alta Precisão para Convênios")
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

def limpar_nome_estrito(nome):
    """Limpeza profunda para evitar que nomes de ruas ou distritos confundam o GPS"""
    nome = str(nome).upper()
    # Remove termos que costumam causar erros de localização
    termos_sujeira = [
        "MUNICIPIO DE ", "PREFEITURA DE ", "GOVERNO DE ", "PM DE ", 
        "PREFEITURA MUNICIPAL DE ", "GLEBA ", "LOTE ", "DISTRITO DE ", "VILA "
    ]
    for termo in termos_sujeira:
        nome = nome.replace(termo, "")
    # Remove qualquer coisa entre parênteses (comum em planilhas de convênio)
    nome = re.sub(r'\(.*\)', '', nome)
    return nome.strip()

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

geolocator = ArcGIS(timeout=15)

uploaded_file = st.file_uploader("Suba sua planilha Excel (sem títulos)", type=['xlsx', 'xls'])

if uploaded_file:
    df = pd.read_excel(uploaded_file, header=None)
    
    st.sidebar.header("⚙️ Verificação de Colunas")
    # Tenta sugerir os índices (0, 1, 2, 3) mas permite ajuste
    idx_conv = st.sidebar.number_input("Índice Convênio", value=0)
    idx_mun = st.sidebar.number_input("Índice Município", value=1)
    idx_uf = st.sidebar.number_input("Índice UF", value=2)
    idx_perc = st.sidebar.number_input("Índice Execução", value=3)

    # Filtro por UF
    col_uf = df.columns[idx_uf]
    ufs_disponiveis = sorted(df[col_uf].dropna().unique().tolist())
    ufs_selecionadas = st.multiselect("🌍 Filtrar por UF", ufs_disponiveis, default=ufs_disponiveis)
    df_filtrado = df[df[col_uf].isin(ufs_selecionadas)]

    if st.button("🚀 Iniciar Geocodificação de Precisão"):
        kml = simplekml.Kml()
        cache = {}
        logs_verificacao = []
        progress_bar = st.progress(0)
        status_msg = st.empty()
        table_placeholder = st.empty()

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
                mun_busca = limpar_nome_estrito(mun_raw)
                cabecalho = f"🏙️ Município: {mun_raw}"

            query = f"{mun_busca}, {uf}, Brasil"
            status_msg.text(f"Buscando: {query}")

            if query in cache:
                location = cache[query]
            else:
                try:
                    location = geolocator.geocode(query)
                    cache[query] = location
                except: location = None

            if location:
                # Verificação de segurança: O endereço retornado contém a UF correta?
                endereco_confirmado = location.address
                
                pnt = kml.newpoint(name=convenio)
                pnt.coords = [(location.longitude, location.latitude)]
                icon_url, perc_texto = obter_estilo_execucao(perc_val)
                pnt.description = f"<b>{cabecalho}</b><br><br><b>UF:</b> {uf}<br><b>Convênio:</b> {convenio}<br><b>Execução:</b> {perc_texto}<br><b>Endereço Base:</b> {endereco_confirmado}"
                pnt.style.iconstyle.icon.href = icon_url
                
                logs_verificacao.append({"Convênio": convenio, "Busca Enviada": query, "Localização Confirmada": endereco_confirmado, "Status": "✅"})
            else:
                logs_verificacao.append({"Convênio": convenio, "Busca Enviada": query, "Localização Confirmada": "NÃO ENCONTRADO", "Status": "❌"})
            
            # Atualiza a tabela de conferência a cada 5 registros
            if i % 5 == 0:
                table_placeholder.dataframe(pd.DataFrame(logs_verificacao).tail(10))

        status_msg.success("Processamento finalizado!")
        st.write("### Tabela de Conferência Geográfica")
        st.dataframe(pd.DataFrame(logs_verificacao))
        
        st.download_button("💾 BAIXAR KML DE PRECISÃO", kml.kml(), "mapa_convenios_precisao.kml")
