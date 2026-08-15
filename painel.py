import streamlit as st
import pandas as pd
import requests
import time
import math
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="Painel Pro - Global Trading & IA Preditiva v27 Ranking", layout="wide")

FUSO_BR = timezone(timedelta(hours=-3))
API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"
SEASON = datetime.now(FUSO_BR).year 
TELEGRAM_TOKEN = "8281259090:AAEggXJKpCMxRbhhrcCZymcmNUKWNoOPFfY"
TELEGRAM_CHAT_ID = "-1004464226419"

LIGAS_MONITORADAS = {
    71: "Brasileirão Série A", 72: "Brasileirão Série B", 73: "Copa do Brasil",
    128: "Campeonato Argentino", 39: "Premier League (Inglaterra)", 140: "La Liga (Espanha)",
    78: "Bundesliga (Alemanha)", 2: "UEFA Champions League", 3: "UEFA Liga Europa",
    848: "UEFA Conference League", 13: "Copa Libertadores", 11: "Copa Sudamericana"
}

def obter_chave_atualizacao():
    return datetime.now(FUSO_BR).strftime("%Y-%m-%d_%H")

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v27_ranking_tipster" 
DATA_HOJE_STR = datetime.now(FUSO_BR).strftime("%Y-%m-%d")

def converter_para_horario_brasilia(iso_string):
    try:
        dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        dt_local = dt_utc.astimezone(FUSO_BR)
        return dt_local.strftime("%Y-%m-%d"), dt_local.strftime("%d/%m/%Y"), dt_local.strftime("%H:%M")
    except Exception:
        return iso_string[:10], f"{iso_string[8:10]}/{iso_string[5:7]}/{iso_string[0:4]}", iso_string[11:16]

def calcular_probabilidades_poisson(lambda_home, lambda_away, max_gols=6):
    def poisson_prob(lmbda, k):
        return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
    
    prob_over_2_5 = prob_under_2_5 = prob_btts = 0.0
    prob_vitoria_home = prob_vitoria_away = prob_empate = 0.0
    
    for h in range(max_gols + 1):
        for a in range(max_gols + 1):
            p = poisson_prob(lambda_home, h) * poisson_prob(lambda_away, a)
            if h + a > 2.5: prob_over_2_5 += p
            else: prob_under_2_5 += p
            if h > 0 and a > 0: prob_btts += p
            if h > a: prob_vitoria_home += p
            elif a > h: prob_vitoria_away += p
            else: prob_empate += p
            
    total_1x2 = prob_vitoria_home + prob_vitoria_away + prob_empate
    if total_1x2 > 0:
        prob_vitoria_home = (prob_vitoria_home / total_1x2) * 100
        prob_vitoria_away = (prob_vitoria_away / total_1x2) * 100
        prob_empate = (prob_empate / total_1x2) * 100

    return {
        'over_2_5': prob_over_2_5 * 100, 'under_2_5': prob_under_2_5 * 100,
        'btts': prob_btts * 100, 'vitoria_home': prob_vitoria_home,
        'vitoria_away': prob_vitoria_away, 'empate': prob_empate
    }

st.sidebar.header("🏆 Seleção da Competição Global")
opcao_liga = st.sidebar.radio("Escolha qual campeonato deseja analisar:", list(LIGAS_MONITORADAS.values()), index=None)
LEAGUE_ID = [k for k, v in LIGAS_MONITORADAS.items() if v == opcao_liga][0] if opcao_liga else None

@st.cache_data(persist="disk")
def descobrir_temporada_valida(league_id, season_atual, key, data_cache):
    for s in [season_atual, season_atual - 1, season_atual - 2]:
        url = f"https://v3.football.api-sports.io/teams?league={league_id}&season={s}"
        try:
            if requests.get(url, headers={'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}).json().get('results', 0) > 0: return s
        except: pass
    return season_atual

SEASON_EFETIVA = descobrir_temporada_valida(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO) if LEAGUE_ID else (SEASON - 1)

@st.cache_data(persist="disk")
def buscar_times_por_liga(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/teams?league={league_id}&season={season}"
    try:
        data = requests.get(url, headers={'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}).json()
        return {item['team']['name']: item['team']['id'] for item in data['response']} if data.get('results', 0) > 0 else {}
    except: return {}

TEAM_IDS = buscar_times_por_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO) if LEAGUE_ID else {}

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Configurações de Análise IA")

if LEAGUE_ID:
    times_disponiveis = sorted(list(TEAM_IDS.keys())) if TEAM_IDS else []
    time_principal = st.sidebar.selectbox("Escolha o Time (Mandante/Favorito)", times_disponiveis, index=None)
    id_time1 = TEAM_IDS[time_principal] if time_principal else None
else:
    time_principal = id_time1 = None
    st.sidebar.info("📌 Selecione uma competição acima.")

def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    return requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}).status_code == 200

@st.cache_data(persist="disk")
def buscar_estatisticas_time(team_id, league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/teams/statistics?league={league_id}&season={season}&team={team_id}"
    try:
        stats = requests.get(url, headers={'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}).json()['response']
        gf, ga = stats.get('goals',{}).get('for',{}).get('average',{}), stats.get('goals',{}).get('against',{}).get('average',{})
        return {
            'jogos': stats.get('fixtures',{}).get('played',{}).get('total',0),
            'gf_home': float(gf.get('home') or 0), 'ga_home': float(ga.get('home') or 0),
            'gf_away': float(gf.get('away') or 0), 'ga_away': float(ga.get('away') or 0)
        }
    except: return {'jogos':0,'gf_home':0.0,'ga_home':0.0,'gf_away':0.0,'ga_away':0.0}

@st.cache_data(persist="disk")
def buscar_medias_escanteios_e_chutes_inteligente(team_id, league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&team={team_id}&last=12"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    
    cantos_pro_casa, cantos_contra_casa, chutes_casa = [], [], []
    cantos_pro_fora, cantos_contra_fora, chutes_fora = [], [], []
    
    try:
        data = requests.get(url, headers=headers).json()
        for f in data.get('response', []):
            f_id = f['fixture']['id']
            is_home = (f['teams']['home']['id'] == team_id)
            time.sleep(0.12)
            data_s = requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={f_id}", headers=headers).json()
            
            t_corners = o_corners = t_shots = 0
            if data_s.get('results', 0) > 0:
                for item in data_s['response']:
                    for s in item['statistics']:
                        if s['type'] == 'Corner Kicks' and s['value'] is not None:
                            if item['team']['id'] == team_id: t_corners = int(s['value'])
                            else: o_corners = int(s['value'])
                        elif s['type'] == 'Shots Total' and s['value'] is not None:
                            if item['team']['id'] == team_id: t_shots = int(s['value'])
                            
            if is_home:
                cantos_pro_casa.append(t_corners)
                cantos_contra_casa.append(o_corners)
                if t_shots > 0: chutes_casa.append(t_shots)
            else:
                cantos_pro_fora.append(t_corners)
                cantos_contra_fora.append(o_corners)
                if t_shots > 0: chutes_fora.append(t_shots)

        return {
            'corners_for_home': sum(cantos_pro_casa)/max(len(cantos_pro_casa),1), 
            'corners_ag_home': sum(cantos_contra_casa)/max(len(cantos_contra_casa),1),
            'corners_for_away': sum(cantos_pro_fora)/max(len(cantos_pro_fora),1), 
            'corners_ag_away': sum(cantos_contra_fora)/max(len(cantos_contra_fora),1),
            'media_chutes_home': sum(chutes_casa)/max(len(chutes_casa),1),
            'media_chutes_away': sum(chutes_fora)/max(len(chutes_fora),1)
        }
    except: 
        return {
            'corners_for_home': 4.5, 'corners_ag_home': 4.5, 
            'corners_for_away': 4.0, 'corners_ag_away': 5.0,
            'media_chutes_home': 12.0, 'media_chutes_away': 11.0
        }

@st.cache_data(persist="disk")
def buscar_jogos_ligas_monitoradas_por_data(data_str, key, cache_key):
    url = f"https://v3.football.api-sports.io/fixtures?date={data_str}"
    try:
        data = requests.get(url, headers={'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}).json()
        return [{
            'LeagueID': f['league']['id'], 'Liga': LIGAS_MONITORADAS[f['league']['id']],
            'Mandante': f['teams']['home']['name'], 'Visitante': f['teams']['away']['name'],
            'HomeID': f['teams']['home']['id'], 'AwayID': f['teams']['away']['id'],
            'Horário': converter_para_horario_brasilia(f['fixture']['date'])[2]
        } for f in data.get('response', []) if f['league']['id'] in LIGAS_MONITORADAS and f['fixture']['status']['short'] in ['NS', 'TBD']]
    except: return []

if id_time1 and LEAGUE_ID:
    st.title(f"⚽ Painel Preditivo v27 Smart Ranking - {opcao_liga}")
    stats_t1 = buscar_estatisticas_time(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    metrics_t1 = buscar_medias_escanteios_e_chutes_inteligente(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)

    st.subheader("🤖 Simulador Inteligente com Sistema de Notas H2H")
    adversario = st.selectbox("Escolha o Time Adversário", [t for t in sorted(list(TEAM_IDS.keys())) if t != time_principal])
    
    if adversario:
        id_time2 = TEAM_IDS[adversario]
        stats_t2 = buscar_estatisticas_time(id_time2, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        metrics_t2 = buscar_medias_escanteios_e_chutes_inteligente(id_time2, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        
        gols_t1 = (stats_t1['gf_home'] + stats_t2['ga_away']) / 2
        gols_t2 = (stats_t2['gf_away'] + stats_t1['ga_home']) / 2
        probs_poisson = calcular_probabilidades_poisson(gols_t1, gols_t2)
        total_gols = gols_t1 + gols_t2
        
        chutes_ht_t1 = (metrics_t1['media_chutes_home'] * 0.45)
        chutes_ht_t2 = (metrics_t2['media_chutes_away'] * 0.45)
        
        c_proj_t1 = (metrics_t1['corners_for_home'] + metrics_t2['corners_ag_away']) / 2
        c_proj_t2 = (metrics_t2['corners_for_away'] + metrics_t1['corners_ag_home']) / 2
        escanteios_jogo = c_proj_t1 + c_proj_t2
        
        # Sistema de Pontuação (Ranking Individual)
        nota_jogo = 0
        destaques = []
        if chutes_ht_t1 >= 4.5 or chutes_ht_t2 >= 4.5:
            nota_jogo += 3
            time_alvo = time_principal if chutes_ht_t1 >= chutes_ht_t2 else adversario
            destaques.append(f"🎯 1º Tempo - {time_alvo} Mais de 4.5/5.5 Chutes")
        if escanteios_jogo >= 9.5:
            nota_jogo += 2
            destaques.append("🍒 Cereja do Bolo: Mais de 1.5 Escanteios no 1º Tempo / Pressão HT")
        if total_gols >= 2.5:
            nota_jogo += 2
            destaques.append("⚡ Projeção Over 2.5 Gols / Linhas Asiáticas")

        col_res1, col_res2 = st.columns(2)
        
        with col_res1:
            with st.container(border=True):
                st.markdown(f"#### 📊 Nota de Oportunidade: `{nota_jogo} / 7 pts`")
                for d in destaques:
                    st.markdown(f"- {d}")

        with col_res2:
            with st.container(border=True):
                st.markdown("#### 📈 Métricas de Volume")
                st.markdown(f"- *Chutes HT Mandante/Visitante:* **{max(chutes_ht_t1, chutes_ht_t2):.1f}**")
                st.markdown(f"- *Projeção de Cantos:* **{escanteios_jogo:.1f}**")

# --- DISPARADOR TELEGRAM: RANKING DOS MELHORES 4-5 JOGOS DO DIA ---
st.sidebar.markdown("---")
if st.sidebar.button("💎 Enviar Top 5 Melhores Entradas (Telegram)", key="btn_bilhete_ranking"):
    with st.spinner("Varrendo e pontuando as melhores oportunidades do dia..."):
        jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        
        if jogos_hoje:
            lista_pontuada = []
            
            for j in jogos_hoje: 
                try:
                    s_h = buscar_estatisticas_time(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                    s_a = buscar_estatisticas_time(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                    m_h = buscar_medias_escanteios_e_chutes_inteligente(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                    m_a = buscar_medias_escanteios_e_chutes_inteligente(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                    
                    g_h_calc = (s_h.get('gf_home', 1.2) + s_a.get('ga_away', 1.2)) / 2
                    g_a_calc = (s_a.get('gf_away', 1.2) + s_h.get('ga_home', 1.2)) / 2
                    
                    chutes_ht_mandante = m_h['media_chutes_home'] * 0.45
                    chutes_ht_visitante = m_a['media_chutes_away'] * 0.45
                    tot_c_calc = ((m_h['corners_for_home'] + m_a['corners_ag_away']) / 2) + ((m_a['corners_for_away'] + m_h['corners_ag_home']) / 2)
                    tot_gols = g_h_calc + g_a_calc
                    
                    pontos = 0
                    sugestoes_jogo = []
                    
                    if chutes_ht_mandante >= 4.5:
                        pontos += 3
                        sugestoes_jogo.append(f"🎯 1º T - {j['Mandante']} (Casa) Mais de 4.5/5.5 Chutes 🔥")
                    elif chutes_ht_visitante >= 4.5:
                        pontos += 3
                        sugestoes_jogo.append(f"🎯 1º T - {j['Visitante']} (Fora) Mais de 4.5/5.5 Chutes 🔥")
                        
                    if tot_c_calc >= 9.5:
                        pontos += 2
                        sugestoes_jogo.append("🍒 Cereja do Bolo: Mais de 1.5 Escanteios HT / Pressão")
                        
                    if tot_gols >= 2.4:
                        pontos += 1
                        sugestoes_jogo.append("⚡ Tendência de Gols (Over 2.5)")
                        
                    if pontos > 0:
                        lista_pontuada.append({
                            'score': pontos,
                            'jogo': f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b> [{j['Horário']}]",
                            'liga': f"🏆 {j['Liga']}",
                            'sugestoes': sugestoes_jogo
                        })
                except Exception: continue
            
            # Ordena do maior score para o menor e pega os TOP 5 para garantir volume saudável
            lista_pontuada = sorted(lista_pontuada, key=lambda x: x['score'], reverse=True)[:5]
            
            if lista_pontuada:
                msg_bilhete = f"💎 <b>SMART TIPSTER: TOP 5 OPORTUNIDADES DO DIA</b> 💎\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n🎯 <i>Ranking inteligente baseado em volume e pressão!</i>\n\n"
                
                for item in lista_pontuada:
                    msg_bilhete += f"{item['jogo']}\n"
                    msg_bilhete += f"   • {item['liga']} (Score: {item['score']} pts)\n"
                    for s in item['sugestoes']:
                        msg_bilhete += f"   • {s}\n"
                    msg_bilhete += "\n"
                
                if enviar_alerta_telegram(msg_bilhete): st.sidebar.success("🔥 Top 5 Melhores Entradas enviadas ao Telegram!")
                else: st.sidebar.error("❌ Erro ao enviar para o Telegram.")
            else:
                st.sidebar.warning("⚠️ Nenhuma oportunidade pontuou o suficiente hoje.")
        else:
            st.sidebar.warning("⚠️ Não há jogos hoje nas ligas monitoradas.")
