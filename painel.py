import streamlit as st
import pandas as pd
import requests
import time
import math
from datetime import datetime, timedelta, timezone
import google.generativeai as genai

st.set_page_config(page_title="Painel Pro - Global Trading & Chat IA", layout="wide")

# --- CONFIGURAÇÃO DA API E TELEGRAM ---
API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"
SEASON = datetime.now().year 

TELEGRAM_TOKEN = "8281259090:AAEggXJKpCMxRbhhrcCZymcmNUKWNoOPFfY"
TELEGRAM_CHAT_ID = "-1004464226419"

# INSIRA SUA CHAVE DA API DO GEMINI AQUI (ou deixe configurada no ambiente)
GEMINI_API_KEY = "SUA_CHAVE_GEMINI_AQUI" 

if GEMINI_API_KEY != "SUA_CHAVE_GEMINI_AQUI":
    genai.configure(api_key=GEMINI_API_KEY)
    chat_model_disponivel = True
else:
    chat_model_disponivel = False

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

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v19_chat_ia"  
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
    prob_empate = 0.0
    
    for h in range(max_gols + 1):
        for a in range(max_gols + 1):
            p = poisson_prob(lambda_home, h) * poisson_prob(lambda_away, a)
            if h + a > 2.5: prob_over_2_5 += p
            if h > 0 and a > 0: prob_btts += p
            if h > a: prob_vitoria_home += p
            elif a > h: prob_vitoria_away += p
            else: prob_empate += p
                
    return {
        'over_2_5': prob_over_2_5 * 100,
        'btts': prob_btts * 100,
        'vitoria_home': prob_vitoria_home * 100,
        'vitoria_away': prob_vitoria_away * 100,
        'empate': prob_empate * 100
    }

st.sidebar.header("🏆 Seleção da Competição Global")
opcao_liga = st.sidebar.radio(
    "Escolha qual campeonato deseja analisar:",
    list(LIGAS_MONITORADAS.values()),
    index=None
)

LEAGUE_ID = [k for k, v in LIGAS_MONITORADAS.items() if v == opcao_liga][0] if opcao_liga else None

@st.cache_data(persist="disk")
def descobrir_temporada_valida(league_id, season_atual, key, data_cache):
    for s in [season_atual, season_atual - 1, season_atual - 2, season_atual - 3]:
        url = f"https://v3.football.api-sports.io/teams?league={league_id}&season={s}"
        headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
        try:
            res = requests.get(url, headers=headers)
            data = res.json()
            if data.get('results', 0) > 0: return s
        except: pass
    return season_atual

SEASON_EFETIVA = descobrir_temporada_valida(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO) if LEAGUE_ID else (SEASON - 1)

@st.cache_data(persist="disk")
def buscar_times_por_liga(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/teams?league={league_id}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        times_dict = {}
        if data.get('results', 0) > 0:
            for item in data['response']:
                times_dict[item['team']['name']] = item['team']['id']
            return times_dict
    except: pass
    return {}

TEAM_IDS = buscar_times_por_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO) if LEAGUE_ID else {}

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Configurações do Painel")
if LEAGUE_ID:
    times_disponiveis = sorted(list(TEAM_IDS.keys())) if TEAM_IDS else []
    time_principal = st.sidebar.selectbox("Escolha o Time Principal", times_disponiveis, index=None, placeholder="Selecione...")
    id_time1 = TEAM_IDS[time_principal] if time_principal else None
else:
    time_principal = None
    id_time1 = None

st.sidebar.markdown("---")
st.sidebar.markdown("**Desenvolvido por:** Thiago Oliveira De sá")

# --- FUNÇÕES DE BUSCA DA API ---
@st.cache_data(persist="disk")
def buscar_estatisticas_time(team_id, league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/teams/statistics?league={league_id}&season={season}&team={team_id}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            stats = data['response']
            gf = stats.get('goals',{}).get('for',{}).get('average',{})
            ga = stats.get('goals',{}).get('against',{}).get('average',{})
            return {
                'jogos': stats.get('fixtures',{}).get('played',{}).get('total',0),
                'gols_feitos_media': float(gf.get('total') or 0), 'gols_sofridos_media': float(ga.get('total') or 0),
                'gf_home': float(gf.get('home') or 0), 'ga_home': float(ga.get('home') or 0),
                'gf_away': float(gf.get('away') or 0), 'ga_away': float(ga.get('away') or 0),
            }
    except: pass
    return {'jogos':0,'gols_feitos_media':0.0,'gols_sofridos_media':0.0,'gf_home':0.0,'ga_home':0.0,'gf_away':0.0,'ga_away':0.0}

stats_t1 = buscar_estatisticas_time(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO) if id_time1 and LEAGUE_ID else {}

# =========================================================================
# TELA PRINCIPAL & ABAS (COM O CHATBOT IA)
# =========================================================================
if not LEAGUE_ID:
    st.title("⚽ Smart Tipster Pro - Chatbot IA Integrado")
    st.info("👈 Selecione uma competição na barra lateral para liberar o painel preditivo e o chat com inteligência artificial.")
else:
    st.title(f"⚽ Smart Tipster AI - {opcao_liga}")
    
    aba_painel, aba_chat = st.tabs(["📊 Painel Estatístico & Poisson", "💬 Chat Analista IA (Gemini)"])
    
    with aba_painel:
        st.subheader(f"Raio-X: {time_principal if time_principal else 'Geral da Liga'}")
        if time_principal:
            c1, c2, c3 = st.columns(3)
            c1.metric("Jogos", stats_t1.get('jogos', 0))
            c2.metric("Média Gols Pró", f"{stats_t1.get('gols_feitos_media', 0):.2f}")
            c3.metric("Média Gols Sofridos", f"{stats_t1.get('gols_sofridos_media', 0):.2f}")
        else:
            st.info("Selecione um time na barra lateral para ver os detalhes.")

    with aba_chat:
        st.subheader("💬 Converse com o Especialista Virtual em Trading Esportivo")
        st.markdown("Faça perguntas livres sobre os jogos, probabilidades, gestão de banca ou tendências estatísticas.")
        
        if not chat_model_disponivel:
            st.warning("⚠️ Para ativar o Chatbot com IA real, insira sua chave da API do Google Gemini na variável `GEMINI_API_KEY` no topo do código.")
        else:
            # Inicializa o histórico de mensagens do chat na sessão do Streamlit
            if "messages" not in st.session_state:
                st.session_state.messages = []

            # Exibe o histórico de mensagens anteriores
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Entrada do usuário na caixa de chat
            if prompt_usuario := st.chat_input("Ex: Qual a melhor entrada para o jogo de hoje baseada em Poisson?"):
                st.session_state.messages.append({"role": "user", "content": prompt_usuario})
                with st.chat_message("user"):
                    st.markdown(prompt_usuario)

                with st.chat_message("assistant"):
                    with st.spinner("Analisando dados do painel e calculando cenários..."):
                        try:
                            # Contexto rico injetado para a IA responder baseada no sistema
                            contexto_sistema = f"""
                            Você é um assistente especialista em apostas esportivas e trader profissional chamado Smart Tipster.
                            A competição ativa no momento é: {opcao_liga} (Temporada {SEASON_EFETIVA}).
                            O time selecionado pelo usuário no painel é: {time_principal if time_principal else 'Nenhum específico'}.
                            Estatísticas atuais do time principal: {stats_t1}.
                            Responda de forma direta, técnica, focada em gestão de banca, análise de valor (edge), mercado de gols, cantos e probabilidades matemáticas.
                            """
                            
                            gemini_model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=contexto_sistema)
                            resposta_ia = gemini_model.generate_content(prompt_usuario)
                            texto_resposta = resposta_ia.text
                        except Exception as e:
                            texto_resposta = f"Desculpe, ocorreu um erro ao consultar o motor de IA: {e}"
                        
                        st.markdown(texto_resposta)
                st.session_state.messages.append({"role": "assistant", "content": texto_resposta})
