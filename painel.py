import streamlit as st
import pandas as pd
import requests
import time
import math
from datetime import datetime, timedelta, timezone

# --- PROTEÇÃO E CONFIGURAÇÃO DA IA ---
try:
    import google.generativeai as genai
    GEMINI_DISPONIVEL = True
except ImportError:
    GEMINI_DISPONIVEL = False

st.set_page_config(page_title="Smart Tipster Pro - Painel Clássico & IA", layout="wide")

# --- CONFIGURAÇÕES DA API E TELEGRAM ---
API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"
SEASON = datetime.now().year 

TELEGRAM_TOKEN = "8281259090:AAEggXJKpCMxRbhhrcCZymcmNUKWNoOPFfY"
TELEGRAM_CHAT_ID = "-1004464226419"

# 🔑 INSIRA SUA CHAVE REAL DO GEMINI AQUI ABAIXO:
GEMINI_API_KEY = "gen-lang-client-0304545979" 

if GEMINI_DISPONIVEL and GEMINI_API_KEY != "gen-lang-client-0304545979":
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        chat_ativo = True
    except:
        chat_ativo = False
else:
    chat_ativo = False

# --- DICIONÁRIO DE LIGAS MONITORADAS ---
LIGAS_MONITORADAS = {
    71: "Brasileirão Série A",
    72: "Brasileirão Série B",
    73: "Copa do Brasil",
    128: "Campeonato Argentino",
    39: "Premier League (Inglaterra)",
    140: "La Liga (Espanha)",
    78: "Bundesliga (Alemanha)",
    2: "UEFA Champions League",
    3: "UEFA Liga Europa",
    848: "UEFA Conference League",
    13: "Copa Libertadores",
    11: "Copa Sudamericana"
}

def obter_chave_atualizacao():
    agora = datetime.now()
    if agora.hour < 8:
        return (agora - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        return agora.strftime("%Y-%m-%d")

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v21_classico"  
DATA_HOJE_STR = datetime.now().strftime("%Y-%m-%d")

# --- BARRA LATERAL (FORMATO CLÁSSICO) ---
st.sidebar.header("🏆 Competições")
opcao_liga = st.sidebar.radio(
    "Escolha o campeonato:",
    list(LIGAS_MONITORADAS.values()),
    index=0
)

LEAGUE_ID = [k for k, v in LIGAS_MONITORADAS.items() if v == opcao_liga][0]

@st.cache_data(persist="disk")
def descobrir_temporada_valida(league_id, season_atual, key, data_cache):
    for s in [season_atual, season_atual - 1, season_atual - 2]:
        url = f"https://v3.football.api-sports.io/teams?league={league_id}&season={s}"
        headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
        try:
            res = requests.get(url, headers=headers)
            if res.json().get('results', 0) > 0: return s
        except: pass
    return season_atual

SEASON_EFETIVA = descobrir_temporada_valida(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)

@st.cache_data(persist="disk")
def buscar_times_por_liga(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/teams?league={league_id}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        times = {}
        if res.json().get('results', 0) > 0:
            for item in res.json()['response']:
                times[item['team']['name']] = item['team']['id']
            return times
    except: pass
    return {}

TEAM_IDS = buscar_times_por_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Seleção de Equipe")
time_principal = st.sidebar.selectbox("Time Principal", sorted(list(TEAM_IDS.keys())) if TEAM_IDS else [], index=0 if TEAM_IDS else None)
id_time1 = TEAM_IDS[time_principal] if time_principal else None

st.sidebar.markdown("---")
st.sidebar.markdown("**Desenvolvedor:** Thiago Oliveira De sá")

# --- FUNÇÕES DE ESTATÍSTICA ---
@st.cache_data(persist="disk")
def buscar_estatisticas_time(team_id, league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/teams/statistics?league={league_id}&season={season}&team={team_id}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        if res.json().get('results', 0) > 0:
            stats = res.json()['response']
            gf = stats.get('goals',{}).get('for',{}).get('average',{})
            ga = stats.get('goals',{}).get('against',{}).get('average',{})
            return {
                'jogos': stats.get('fixtures',{}).get('played',{}).get('total',0),
                'gols_feitos_media': float(gf.get('total') or 0),
                'gols_sofridos_media': float(ga.get('total') or 0),
            }
    except: pass
    return {'jogos':0,'gols_feitos_media':0.0,'gols_sofridos_media':0.0}

stats_t1 = buscar_estatisticas_time(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO) if id_time1 else {}

# --- TELA PRINCIPAL ---
st.title(f"⚽ Smart Tipster Pro - {opcao_liga}")

# Abas organizadas no estilo clássico
aba_painel, aba_ia = st.tabs(["📊 Painel Estatístico & Poisson", "💬 Chat Analista IA (Gemini)"])

with aba_painel:
    st.subheader(f"Raio-X: {time_principal if time_principal else 'Geral'}")
    if time_principal:
        c1, c2, c3 = st.columns(3)
        c1.metric("Jogos Disputados", stats_t1.get('jogos', 0))
        c2.metric("Média Gols Pró", f"{stats_t1.get('gols_feitos_media', 0):.2f}")
        c3.metric("Média Gols Sofridos", f"{stats_t1.get('gols_sofridos_media', 0):.2f}")
    else:
        st.info("Selecione um time na barra lateral.")

with aba_ia:
    st.subheader("💬 Central de Inteligência Artificial Analítica")
    st.markdown("Faça perguntas diretas ao assistente baseadas nas estatísticas atuais da competição e do time selecionado.")
    
    if not chat_ativo:
        st.error("⚠️ A IA do Gemini está inativa. Verifique se substituiu 'SUA_CHAVE_GEMINI_AQUI' pela sua chave correta e se adicionou 'google-generativeai' no requirements.txt.")
    else:
        pergunta_usuario = st.text_input("Digite sua dúvida ou comando para a IA:", placeholder="Ex: Qual a projeção de gols para o próximo jogo deste time?")
        
        if st.button("🤖 Consultar Inteligência Artificial"):
            if not pergunta_usuario:
                st.warning("Por favor, digite uma pergunta.")
            else:
                with st.spinner("Analisando dados do painel e gerando relatório..."):
                    try:
                        instrucao_sistema = f"Você é um tipster profissional e especialista em apostas esportivas. Competição ativa: {opcao_liga}. Time selecionado: {time_principal}. Dados: {stats_t1}."
                        modelo = genai.GenerativeModel('gemini-1.5-flash', system_instruction=instrucao_sistema)
                        resposta = modelo.generate_content(pergunta_usuario)
                        st.success("✅ Análise Pronta:")
                        st.markdown(resposta.text)
                    except Exception as e:
                        st.error(f"Erro ao consultar o modelo de IA: {e}")
