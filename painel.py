import streamlit as st
import pandas as pd
import requests
import time
import math
from datetime import datetime, timedelta, timezone

# --- PROTEÇÃO SEGURA DE IMPORTAÇÃO DA IA ---
try:
    import google.generativeai as genai
    GEMINI_DISPONIVEL = True
except ImportError:
    GEMINI_DISPONIVEL = False

st.set_page_config(page_title="Painel Pro - Global Trading & IA Interativa", layout="wide")

# --- CONFIGURAÇÃO DA API E TELEGRAM ---
API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"
SEASON = datetime.now().year 

TELEGRAM_TOKEN = "8281259090:AAEggXJKpCMxRbhhrcCZymcmNUKWNoOPFfY"
TELEGRAM_CHAT_ID = "-1004464226419"

# INSIRA SUA CHAVE DA API DO GEMINI AQUI
GEMINI_API_KEY = "SUA_CHAVE_GEMINI_AQUI" 

if GEMINI_DISPONIVEL and GEMINI_API_KEY != "SUA_CHAVE_GEMINI_AQUI":
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

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v20_pro"  
DATA_HOJE_STR = datetime.now().strftime("%Y-%m-%d")

def converter_para_horario_brasilia(iso_string):
    try:
        dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        fuso_br = timezone(timedelta(hours=-3))
        dt_local = dt_utc.astimezone(fuso_br)
        return dt_local.strftime("%Y-%m-%d"), dt_local.strftime("%d/%m/%Y"), dt_local.strftime("%H:%M")
    except:
        return iso_string[:10], f"{iso_string[8:10]}/{iso_string[5:7]}/{iso_string[0:4]}", iso_string[11:16]

def calcular_probabilidades_poisson(lambda_home, lambda_away, max_gols=6):
    def poisson_prob(lmbda, k):
        return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
    
    prob_over_2_5 = 0.0
    prob_btts = 0.0
    prob_vitoria_home = 0.0
    prob_vitoria_away = 0.0
    
    for h in range(max_gols + 1):
        for a in range(max_gols + 1):
            p = poisson_prob(lambda_home, h) * poisson_prob(lambda_away, a)
            if h + a > 2.5: prob_over_2_5 += p
            if h > 0 and a > 0: prob_btts += p
            if h > a: prob_vitoria_home += p
            elif a > h: prob_vitoria_away += p
                
    return {
        'over_2_5': prob_over_2_5 * 100,
        'btts': prob_btts * 100,
        'vitoria_home': prob_vitoria_home * 100,
        'vitoria_away': prob_vitoria_away * 100
    }

st.sidebar.header("🏆 Competição Global")
opcao_liga = st.sidebar.radio("Escolha a competição:", list(LIGAS_MONITORADAS.values()), index=None)
LEAGUE_ID = [k for k, v in LIGAS_MONITORADAS.items() if v == opcao_liga][0] if opcao_liga else None

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

SEASON_EFETIVA = descobrir_temporada_valida(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO) if LEAGUE_ID else (SEASON - 1)

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

TEAM_IDS = buscar_times_por_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO) if LEAGUE_ID else {}

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Painel de Comando")
if LEAGUE_ID:
    time_principal = st.sidebar.selectbox("Time Principal", sorted(list(TEAM_IDS.keys())), index=None, placeholder="Selecione...")
    id_time1 = TEAM_IDS[time_principal] if time_principal else None
else:
    time_principal = None
    id_time1 = None

st.sidebar.markdown("---")
st.sidebar.markdown("**Desenvolvedor:** Thiago Oliveira De sá")

# --- FUNÇÕES DE DADOS ---
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
                'gf_home': float(gf.get('home') or 0), 'ga_home': float(ga.get('home') or 0),
                'gf_away': float(gf.get('away') or 0), 'ga_away': float(ga.get('away') or 0),
            }
    except: pass
    return {'jogos':0,'gols_feitos_media':0.0,'gols_sofridos_media':0.0,'gf_home':0.0,'ga_home':0.0,'gf_away':0.0,'ga_away':0.0}

stats_t1 = buscar_estatisticas_time(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO) if id_time1 and LEAGUE_ID else {}

# --- INTERFACE PRINCIPAL ---
if not LEAGUE_ID:
    st.title("⚽ Smart Tipster Pro - Painel Preditivo & IA")
    st.info("👈 Selecione uma competição na barra lateral para iniciar.")
else:
    st.title(f"⚽ Smart Tipster AI Pro - {opcao_liga}")
    
    aba_painel, aba_chat_direto = st.tabs(["📊 Painel Estatístico & Poisson", "💬 Entrada de Comandos & Chat IA"])
    
    with aba_painel:
        st.subheader(f"Raio-X: {time_principal if time_principal else 'Geral'}")
        if time_principal:
            c1, c2, c3 = st.columns(3)
            c1.metric("Jogos Disputados", stats_t1.get('jogos', 0))
            c2.metric("Média Gols Pró", f"{stats_t1.get('gols_feitos_media', 0):.2f}")
            c3.metric("Média Gols Sofridos", f"{stats_t1.get('gols_sofridos_media', 0):.2f}")
        else:
            st.info("Selecione um time na barra lateral.")

    with aba_chat_direto:
        st.subheader("💬 Central de Comandos e Análise Direta por IA")
        st.markdown("Digite abaixo sua instrução ou pergunta personalizada para o motor analítico:")
        
        # Duas entradas diretas no painel para comandos e perguntas livres
        pergunta_customizada = st.text_input("Comando / Pergunta rápida:", placeholder="Ex: Analise o comportamento ofensivo nas últimas partidas...")
        
        if st.button("🚀 Processar Comando com IA"):
            if not chat_ativo:
                st.error("⚠️ A IA do Gemini não está configurada ou a biblioteca está ausente.")
            elif not pergunta_customizada:
                st.warning("⚠️ Digite um comando ou pergunta antes de enviar.")
            else:
                with st.spinner("Processando comando analítico..."):
                    try:
                        prompt_sistema = f"Você é um tipster profissional e analista de trading esportivo. Competição ativa: {opcao_liga}. Time selecionado: {time_principal}. Dados estatísticos: {stats_t1}."
                        modelo = genai.GenerativeModel('gemini-1.5-flash', system_instruction=prompt_sistema)
                        resposta = modelo.generate_content(pergunta_customizada)
                        st.success("✅ Resposta da IA:")
                        st.markdown(resposta.text)
                    except Exception as e:
                        st.error(f"Erro ao processar com a IA: {e}")
