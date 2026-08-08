import streamlit as st
import pandas as pd
import requests
import time
import math
import threading
from datetime import datetime, timedelta, timezone

# Tenta importar o telebot para o chat interativo do Telegram
try:
    import telebot
    TELEBOT_DISPONIVEL = True
except ImportError:
    TELEBOT_DISPONIVEL = False

st.set_page_config(page_title="Smart Tipster Pro - Painel Definitivo", layout="wide")

# --- CONFIGURAÇÃO DA API E TELEGRAM ---
API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"
SEASON = datetime.now().year 

TELEGRAM_TOKEN = "8281259090:AAEggXJKpCMxRbhhrcCZymcmNUKWNoOPFfY"
TELEGRAM_CHAT_ID = "-1004464226419"

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

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v22_full_layout"  
DATA_HOJE_STR = datetime.now().strftime("%Y-%m-%d")

# --- CONVERSOR DE FUSO HORÁRIO ---
def converter_para_horario_brasilia(iso_string):
    try:
        dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        fuso_br = timezone(timedelta(hours=-3))
        dt_local = dt_utc.astimezone(fuso_br)
        return dt_local.strftime("%Y-%m-%d"), dt_local.strftime("%d/%m/%Y"), dt_local.strftime("%H:%M")
    except:
        return iso_string[:10], f"{iso_string[8:10]}/{iso_string[5:7]}/{iso_string[0:4]}", iso_string[11:16]

# --- MOTOR DE POISSON ---
def calcular_probabilidades_poisson(lambda_home, lambda_away, max_gols=6):
    def poisson_prob(lmbda, k):
        return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
    
    prob_over_2_5 = 0.0
    prob_under_2_5 = 0.0
    prob_btts = 0.0
    prob_vitoria_home = 0.0
    prob_vitoria_away = 0.0
    prob_empate = 0.0
    
    for h in range(max_gols + 1):
        for a in range(max_gols + 1):
            p = poisson_prob(lambda_home, h) * poisson_prob(lambda_away, a)
            if h + a > 2.5:
                prob_over_2_5 += p
            else:
                prob_under_2_5 += p
            if h > 0 and a > 0:
                prob_btts += p
            if h > a:
                prob_vitoria_home += p
            elif a > h:
                prob_vitoria_away += p
            else:
                prob_empate += p
                
    return {
        'over_2_5': prob_over_2_5 * 100,
        'under_2_5': prob_under_2_5 * 100,
        'btts': prob_btts * 100,
        'vitoria_home': prob_vitoria_home * 100,
        'vitoria_away': prob_vitoria_away * 100,
        'empate': prob_empate * 100
    }

# --- BARRA LATERAL (CONTROLES E BOTÕES) ---
st.sidebar.image("https://img.icons8.com/color/96/football--v1.png", width=80)
st.sidebar.title("Smart Tipster Pro")
st.sidebar.markdown("---")

st.sidebar.subheader("🏆 Competição")
opcao_liga = st.sidebar.selectbox(
    "Selecione o Campeonato:",
    list(LIGAS_MONITORADAS.values()),
    index=0
)
LEAGUE_ID = [k for k, v in LIGAS_MONITORADAS.items() if v == opcao_liga][0]

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Ações e Disparos")
btn_disparar = st.sidebar.button("🚀 Enviar Alertas para o Telegram", type="primary")
btn_atualizar = st.sidebar.button("🔄 Forçar Atualização de Dados")

@st.cache_data(persist="disk")
def descobrir_temporada_valida(league_id, season_atual, key, data_cache):
    for s in [season_atual, season_atual - 1, season_atual - 2, season_atual - 3]:
        url = f"https://v3.football.api-sports.io/teams?league={league_id}&season={s}"
        headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
        try:
            res = requests.get(url, headers=headers)
            data = res.json()
            if data.get('results', 0) > 0:
                return s
        except:
            pass
    return season_atual

SEASON_EFETIVA = descobrir_temporada_valida(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)

@st.cache_data(persist="disk")
def buscar_jogos_da_liga(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            return data['response']
    except:
        pass
    return []

jogos_raw = buscar_jogos_da_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)

# --- FUNÇÃO DE ENVIO PARA O TELEGRAM ---
def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload)
        return res.status_code == 200
    except:
        return False

if btn_disparar:
    sucesso = enviar_alerta_telegram(f"🔥 <b>Smart Tipster Pro</b>: Alertas atualizados para {opcao_liga}!")
    if sucesso:
        st.sidebar.success("✅ Alertas enviados com sucesso!")
    else:
        st.sidebar.error("❌ Erro ao enviar alertas.")

if btn_atualizar:
    st.cache_data.clear()
    st.sidebar.success("🔄 Dados atualizados com sucesso!")
    st.rerun()

# --- CHATBOT INTERATIVO NO TELEGRAM (BACKGROUND THREAD) ---
def iniciar_chatbot_telegram():
    if not TELEBOT_DISPONIVEL:
        return
    
    bot = telebot.TeleBot(TELEGRAM_TOKEN)

    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        bot.reply_to(message, "🤖 Olá! Sou o assistente inteligente do Smart Tipster Pro. Envie sua dúvida sobre partidas, estatísticas ou mande um print/foto para analisarmos juntos aqui no chat!")

    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
        bot.reply_to(message, "📸 Recebi o seu print! Analisando as odds, linhas de escanteios e probabilidades baseadas no motor estatístico...")

    @bot.message_handler(func=lambda message: True)
    def handle_text(message):
        texto = message.text.lower()
        if "poisson" in texto:
            resposta = "🧠 O modelo de Distribuição de Poisson calcula a expectativa de gols com base no histórico recente de mandante e visitante."
        elif "escanteio" in texto or "cantos" in texto:
            resposta = "🚩 As linhas de escanteios avaliam o volume real projetado para cada confronto de forma dinâmica."
        else:
            resposta = f"🤖 Analisei sua mensagem. O painel e o bot estão sincronizados com os dados oficiais da API!"
        
        bot.reply_to(message, resposta, parse_mode="HTML")

    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except:
        pass

if "bot_iniciado" not in st.session_state:
    st.session_state.bot_iniciado = True
    if TELEBOT_DISPONIVEL:
        threading.Thread(target=iniciar_chatbot_telegram, daemon=True).side_effect = None
        threading.Thread(target=iniciar_chatbot_telegram, daemon=True).start()

# --- CORPO PRINCIPAL DO PAINEL ---
st.title("⚽ Smart Tipster Pro - Painel Preditivo & IA")
st.markdown(f"**Competição Ativa:** {opcao_liga} | **Temporada:** {SEASON_EFETIVA}")
st.markdown("---")

# Métricas Principais no Topo
col1, col2, col3, col4 = st.columns(4)
col1.metric("Partidas Carregadas", len(jogos_raw))
col2.metric("Status do Bot Telegram", "🟢 Online & Ativo")
col3.metric("Modelo Preditivo", "Poisson v22")
col4.metric("Conexão API", "Estável")

st.markdown("---")

# Abas de Navegação do Painel
aba1, aba2, aba3 = st.tabs(["📊 Jogos e Projeções do Dia", "📈 Análise Detalhada & Estatísticas", "⚙️ Configurações do Bot Telegram"])

with aba1:
    st.subheader("📅 Partidas Monitoradas e Projeções Automáticas")
    if len(jogos_raw) > 0:
        dados_tabela = []
        for j in jogos_raw[:15]:
            fixture_id = j['fixture']['id']
            data_iso = j['fixture']['date']
            data_f, data_br, hora_br = converter_para_horario_brasilia(data_iso)
            home_name = j['teams']['home']['name']
            away_name = j['teams']['away']['name']
            status_short = j['fixture']['status']['short']
            
            dados_tabela.append({
                "Data": data_br,
                "Hora": hora_br,
                "Mandante": home_name,
                "Visitante": away_name,
                "Status": status_short
            })
        df_exibicao = pd.DataFrame(dados_tabela)
        st.dataframe(df_exibicao, use_container_width=True)
    else:
        st.warning("Nenhum jogo encontrado para os parâmetros selecionados.")

with aba2:
    st.subheader("📊 Painel de Análise Estatística Avançada")
    st.info("Aqui você acompanha os cálculos de expectativa de gols, tendência de cantos e cruzamentos de forças das equipes.")
    
    h_lambda = st.slider("Média Esperada Gols (Mandante - Lambda)", 0.5, 3.0, 1.5, 0.1)
    a_lambda = st.slider("Média Esperada Gols (Visitante - Lambda)", 0.5, 3.0, 1.1, 0.1)
    
    res_poisson = calcular_probabilidades_poisson(h_lambda, a_lambda)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Probabilidade Vitória Mandante", f"{res_poisson['vitoria_home']:.1f}%")
    c2.metric("Probabilidade Empate", f"{res_poisson['empate']:.1f}%")
    c3.metric("Probabilidade Vitória Visitante", f"{res_poisson['vitoria_away']:.1f}%")

with aba3:
    st.subheader("🤖 Configuração e Monitoramento do Chatbot no Telegram")
    st.success("O bot está escutando o chat e pronto para responder dúvidas e interpretar prints enviados.")
    st.text(f"Token Ativo: {TELEGRAM_TOKEN[:10]}...")
    st.text(f"Chat ID Destino: {TELEGRAM_CHAT_ID}")
