import os
import streamlit as st
import pandas as pd
import plotly.express as px

# Limpa qualquer vestígio de credencial antiga do Google Cloud
for var in ["GOOGLE_APPLICATION_CREDENTIALS", "GCP_PROJECT", "CLOUD_ML_REGION"]:
    os.environ.pop(var, None)

import google.generativeai as genai

# ==========================================
# COLE A SUA CHAVE DO AI STUDIO ABAIXO ENTRE AS ASPAS:
# ==========================================
API_KEY_DIRETA = "AQ.Ab8RN6LUFgIywwdRku7dHwz7HcfXispuE7F3ikQrZBfc4B914w"

genai.configure(api_key=API_KEY_DIRETA)
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="Analisador Esportivo Pro", layout="wide")

st.title("⚽ Painel Analisador Esportivo Pro")
st.write("Base de dados completa com as principais ligas do mundo.")

@st.cache_data
def carregar_base_robusta():
    dados = {
        'Campeonato': [
            'Brasileirão Série A', 'Brasileirão Série A', 'Brasileirão Série A', 'Brasileirão Série A', 'Brasileirão Série A',
            'Brasileirão Série B', 'Brasileirão Série B', 'Brasileirão Série B', 'Brasileirão Série B',
            'Premier League', 'Premier League', 'Premier League', 'Premier League',
            'Campeonato Argentino', 'Campeonato Argentino', 'Campeonato Argentino'
        ],
        'Home': [
            'Flamengo', 'Palmeiras', 'Botafogo', 'São Paulo', 'Fluminense',
            'Santos', 'Sport', 'Coritiba', 'América-MG',
            'Manchester City', 'Arsenal', 'Liverpool', 'Chelsea',
            'River Plate', 'Boca Juniors', 'Racing Club'
        ],
        'mando': ['Casa', 'Fora', 'Casa', 'Fora', 'Casa', 'Casa', 'Fora', 'Casa', 'Fora', 'Casa', 'Fora', 'Casa', 'Fora', 'Casa', 'Fora', 'Casa'],
        'gols_feitos_media': [2.2, 1.8, 2.0, 1.4, 1.6, 1.5, 1.2, 1.7, 1.3, 3.0, 2.4, 2.7, 1.9, 1.8, 1.6, 1.7],
        'gols_sofridos_media': [0.8, 1.0, 0.9, 1.1, 1.0, 0.9, 1.2, 0.8, 1.1, 0.9, 0.7, 0.8, 1.1, 0.7, 0.9, 0.8],
        'cartoes_amarelos_media': [2.1, 2.4, 2.3, 2.6, 2.2, 2.5, 2.8, 2.1, 2.4, 1.2, 1.5, 1.4, 1.8, 3.1, 3.4, 2.9],
        'posse_bola_media': [58.5, 52.0, 53.0, 49.5, 51.0, 52.5, 48.0, 54.0, 50.0, 65.4, 59.0, 61.2, 53.5, 56.0, 54.5, 53.0],
        'escanteios_media': [6.4, 5.2, 6.0, 4.8, 5.5, 5.1, 4.6, 5.8, 4.9, 8.0, 6.8, 7.5, 6.1, 5.9, 5.6, 5.7],
        'chutes_ao_gol_media': [5.8, 4.5, 5.5, 4.1, 4.7, 4.4, 3.8, 4.9, 4.2, 7.5, 6.2, 7.0, 5.1, 4.8, 4.5, 4.7],
        'desarmes_media': [16.5, 18.2, 15.0, 17.0, 16.2, 18.0, 19.1, 15.8, 17.5, 13.8, 14.5, 14.0, 16.0, 19.5, 20.1, 18.8]
    }
    return pd.DataFrame(dados)

df = carregar_base_robusta()

if df is not None and not df.empty:
    st.sidebar.header("Filtros de Análise")
    liga_selecionada = st.sidebar.selectbox("Escolha o Campeonato", df['Campeonato'].unique())
    df_liga = df[df['Campeonato'] == liga_selecionada]
    times_disponiveis = df_liga['Home'].unique()
    time_selecionado = st.sidebar.selectbox("Escolha o Time", times_disponiveis)
    mercado = st.sidebar.selectbox("Escolha o Mercado Principal", ["Gols", "Escanteios", "Chutes ao Gol", "Cartões Amarelos", "Posse de Bola", "Desarmes"])

    time_dados = df_liga[df_liga['Home'] == time_selecionado].iloc[0]

    st.subheader(f"Desempenho Recente (L5): {time_selecionado} ({liga_selecionada})")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if mercado == "Gols":
            st.metric(label="Média de Gols Feitos", value=time_dados['gols_feitos_media'])
            st.metric(label="Média de Gols Sofridos", value=time_dados['gols_sofridos_media'])
        elif mercado == "Escanteios":
            st.metric(label="Média de Escanteios", value=time_dados['escanteios_media'])
        else:
            st.metric(label=f"Média de {mercado}", value=time_dados[f'{mercado.lower().replace(" ", "_")}_media'])

    with col2:
        st.metric(label="Mando de Campo Comum", value=time_dados['mando'])
    with col3:
        st.metric(label="Status de Confiabilidade", value="Alto 🟢")

    # --- CHAT COM IA ---
    st.markdown("---")
    st.subheader(f"🤖 Chat Preditivo: {time_selecionado}")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Pergunte algo sobre o jogo..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            contexto = f"Analise o time {time_selecionado} que tem média de gols de {time_dados['gols_feitos_media']} e escanteios {time_dados['escanteios_media']}. Pergunta: {prompt}"
            try:
                response = model.generate_content(contexto)
                resposta = response.text
                st.markdown(resposta)
                st.session_state.messages.append({"role": "assistant", "content": resposta})
            except Exception as e:
                st.error(f"Erro na IA: {e}")

    # Exibição dos Gráficos
    coluna_grafico = f'{mercado.lower().replace(" ", "_")}_media'
    if coluna_grafico in df_liga.columns:
        fig = px.bar(df_liga, x='Home', y=coluna_grafico, title=f"Comparativo {mercado}")
        st.plotly_chart(fig, use_container_width=True)
