import streamlit as st
import pandas as pd
import requests
import time
import math
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="Painel Pro - Tipster Ultimate Radar (Sofascore)", layout="wide")

FUSO_BR = timezone(timedelta(hours=-3))
API_KEY_FIXA = "2981e7e072msh7c1be16f30f788ap1a37e1jsn4424707c8b9e"
API_HOST = "sofascore.p.rapidapi.com"

TELEGRAM_TOKEN = "8281259090:AAEggXJKpCMxRbhhrcCZymcmNUKWNoOPFfY"
TELEGRAM_CHAT_ID = "-1004464226419"

LIGAS_MONITORADAS = {
    325: "Brasileirão Série A", 390: "Brasileirão Série B", 393: "Copa do Brasil",
    155: "Campeonato Argentino", 17: "Premier League (Inglaterra)", 8: "La Liga (Espanha)",
    35: "Bundesliga (Alemanha)", 7: "UEFA Champions League", 679: "UEFA Liga Europa",
    1703: "UEFA Conference League", 384: "Copa Libertadores", 386: "Copa Sudamericana"
}

def obter_chave_atualizacao():
    return datetime.now(FUSO_BR).strftime("%Y-%m-%d_%H")

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v34_debug" 
DATA_HOJE_STR = datetime.now(FUSO_BR).strftime("%Y-%m-%d")

st.sidebar.header("🏆 Seleção da Competição Global")
opcao_liga = st.sidebar.radio("Escolha qual campeonato deseja analisar:", list(LIGAS_MONITORADAS.values()), index=None)

# =========================================================
# MOTOR COM "MODO DEDO DURO" ATIVADO
# =========================================================

@st.cache_data(persist="disk")
def buscar_jogos_ligas_monitoradas_por_data(data_str, key, cache_key):
    url = "https://sofascore.p.rapidapi.com/matches/v2/get-date"
    querystring = {"date": data_str}
    headers = {'x-rapidapi-host': API_HOST, 'x-rapidapi-key': key}
    
    try:
        res = requests.get(url, headers=headers, params=querystring)
        
        # Se a API barrar, o erro vai aparecer gigante na sua tela
        if res.status_code != 200:
            st.error(f"🚨 ERRO DA API SOFASCORE (Status {res.status_code}): {res.text}")
            return []
            
        dados = res.json()
        jogos_validos = []
        for event in dados.get('events', []):
            liga_id = event.get('tournament', {}).get('uniqueTournament', {}).get('id')
            if liga_id in LIGAS_MONITORADAS and event.get('status', {}).get('type') == 'notstarted':
                dt_inicio = datetime.fromtimestamp(event.get('startTimestamp', 0), tz=FUSO_BR).strftime("%H:%M")
                jogos_validos.append({
                    'FixtureID': event.get('id'), 'LeagueID': liga_id, 'Liga': LIGAS_MONITORADAS[liga_id],
                    'Mandante': event.get('homeTeam', {}).get('name'), 'Visitante': event.get('awayTeam', {}).get('name'),
                    'HomeID': event.get('homeTeam', {}).get('id'), 'AwayID': event.get('awayTeam', {}).get('id'),
                    'Horário': dt_inicio
                })
        return jogos_validos
    except Exception as e:
        st.error(f"🚨 ERRO INTERNO DO PYTHON: {e}")
        return []

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Configurações de Análise IA")

if st.sidebar.button("💎 Enviar Top Melhores Entradas (Telegram)", key="btn_bilhete_full"):
    jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    
    if not jogos_hoje:
        st.sidebar.error("❌ O código rodou, mas a lista de jogos voltou vazia. Verifique a mensagem de erro vermelha no painel principal (se houver) ou confirme se há jogos nas ligas selecionadas hoje.")
    else:
        st.sidebar.success(f"✅ {len(jogos_hoje)} jogos encontrados! (O resto da análise começaria aqui...)")

st.markdown("---")
st.title("⚽ Dashboard Inicializado (Modo Debug)")
st.info("Clique no primeiro botão azul na barra lateral. Se houver algum problema de comunicação com a RapidAPI, uma caixa vermelha vai aparecer aqui embaixo detalhando o erro.")
