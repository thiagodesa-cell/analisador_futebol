import streamlit as st
import pandas as pd
import requests
import time
import math
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="Painel Pro - Tipster Ultimate Radar v30", layout="wide")

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

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v30_ultimate_radar" 
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
def buscar_metricas_completas_avancadas(team_id, league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&team={team_id}&last=12"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    
    c_pro, c_contra, s_tot, s_gol, faltas_lista = [], [], [], [], []
    
    try:
        data = requests.get(url, headers=headers).json()
        for f in data.get('response', []):
            f_id = f['fixture']['id']
            is_home = (f['teams']['home']['id'] == team_id)
            time.sleep(0.12)
            data_s = requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={f_id}", headers=headers).json()
            
            t_c = o_c = t_st = t_sg = t_f = 0
            if data_s.get('results', 0) > 0:
                for item in data_s['response']:
                    for s in item['statistics']:
                        val = s['value']
                        if val is not None:
                            if s['type'] == 'Corner Kicks':
                                if item['team']['id'] == team_id: t_c = int(val)
                                else: o_c = int(val)
                            elif s['type'] == 'Shots Total':
                                if item['team']['id'] == team_id: t_st = int(val)
                            elif s['type'] == 'Shots on Goal':
                                if item['team']['id'] == team_id: t_sg = int(val)
                            elif s['type'] == 'Fouls':
                                if item['team']['id'] == team_id: t_f = int(val)
                            
            c_pro.append(t_c)
            c_contra.append(o_c)
            if t_st > 0: s_tot.append(t_st)
            if t_sg > 0: s_gol.append(t_sg)
            if t_f > 0: faltas_lista.append(t_f)

        div = max(len(c_pro), 1)
        return {
            'corners_for': sum(c_pro)/div, 'corners_ag': sum(c_contra)/div,
            'shots_total': sum(s_tot)/max(len(s_tot), 1),
            'shots_on_goal': sum(s_gol)/max(len(s_gol), 1),
            'fouls': sum(faltas_lista)/max(len(faltas_lista), 1)
        }
    except: 
        return {'corners_for': 4.5, 'corners_ag': 4.5, 'shots_total': 12.0, 'shots_on_goal': 4.2, 'fouls': 13.5}

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
    st.title(f"⚽ Painel Ultimate Radar v30 - {opcao_liga}")
    stats_t1 = buscar_estatisticas_time(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    metrics_t1 = buscar_metricas_completas_avancadas(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)

    st.subheader("🤖 Simulador Completo (Chutes, Cantos e Mercado de Faltas)")
    adversario = st.selectbox("Escolha o Time Adversário", [t for t in sorted(list(TEAM_IDS.keys())) if t != time_principal])
    
    if adversario:
        id_time2 = TEAM_IDS[adversario]
        stats_t2 = buscar_estatisticas_time(id_time2, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        metrics_t2 = buscar_metricas_completas_avancadas(id_time2, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        
        gols_t1 = (stats_t1['gf_home'] + stats_t2['ga_away']) / 2
        gols_t2 = (stats_t2['gf_away'] + stats_t1['ga_home']) / 2
        total_gols = gols_t1 + gols_t2
        
        chutes_ht_t1 = metrics_t1['shots_total'] * 0.45
        chutes_alvo_t1 = metrics_t1['shots_on_goal']
        cantos_jogo = metrics_t1['corners_for'] + metrics_t2['corners_for']
        faltas_jogo = metrics_t1['fouls'] + metrics_t2['fouls']
        
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            with st.container(border=True):
                st.markdown("#### 🎯 Projeção de Finalizações")
                st.markdown(f"- *Chutes Totais HT (1º T):* **{chutes_ht_t1:.1f}**")
                st.markdown(f"- *Chutes no Alvo Médios:* **{chutes_alvo_t1:.1f}**")
                st.markdown(f"- *Expectativa de Gols (Poisson):* **{total_gols:.2f}**")
        with col_res2:
            with st.container(border=True):
                st.markdown("#### 🚩 Cantos & Faltas")
                st.markdown(f"- *Projeção de Escanteios:* **{cantos_jogo:.1f}**")
                st.markdown(f"- *Média Estimada de Faltas:* **{faltas_jogo:.1f}**")
                if faltas_jogo >= 26.5:
                    st.success("🪓 **Radar Ativado:** Cenário de Guerra! Ideal para apostar em faltas de zagueiros/volantes.")

# --- DISPARADOR TELEGRAM COM RADAR DE AGRESSIVIDADE ---
st.sidebar.markdown("---")
if st.sidebar.button("💎 Enviar Top 6 Melhores Entradas (Telegram)", key="btn_bilhete_full"):
    with st.spinner("Varrendo todos os jogos e ativando Radares de Faltas..."):
        jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        
        if jogos_hoje:
            lista_pontuada = []
            
            for j in jogos_hoje: 
                try:
                    s_h = buscar_estatisticas_time(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                    s_a = buscar_estatisticas_time(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                    m_h = buscar_metricas_completas_avancadas(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                    m_a = buscar_metricas_completas_avancadas(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                    
                    tot_gols = ((s_h.get('gf_home', 1.2) + s_a.get('ga_away', 1.2)) / 2) + ((s_a.get('gf_away', 1.2) + s_h.get('ga_home', 1.2)) / 2)
                    c_tot = m_h['corners_for'] + m_a['corners_for']
                    s_tot_game = m_h['shots_total'] + m_a['shots_total']
                    s_gol_game = m_h['shots_on_goal'] + m_a['shots_on_goal']
                    f_tot_game = m_h['fouls'] + m_a['fouls']
                    
                    chutes_ht_h = m_h['shots_total'] * 0.45
                    chutes_ht_a = m_a['shots_total'] * 0.45
                    
                    # Sistema de Pontuação atualizado (Faltas ganham peso)
                    score = 2
                    if c_tot >= 9.0: score += 1
                    if s_tot_game >= 22.0: score += 1
                    if s_gol_game >= 7.0: score += 1
                    if tot_gols >= 2.2: score += 1
                    if f_tot_game >= 26.5: score += 1 # Ponto extra se o jogo for muito agressivo
                    
                    lista_pontuada.append({
                        'score': score,
                        'jogo': f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b> [{j['Horário']}]",
                        'liga': f"🏆 {j['Liga']}",
                        'cantos': f"{c_tot:.1f}",
                        'chutes_tot': f"{s_tot_game:.1f}",
                        'chutes_gol': f"{s_gol_game:.1f}",
                        'faltas': f"{f_tot_game:.1f}",
                        'chutes_ht': f"{max(chutes_ht_h, chutes_ht_a):.1f}"
                    })
                except Exception: continue
            
            # Pega os TOP 6 melhores jogos
            lista_pontuada = sorted(lista_pontuada, key=lambda x: x['score'], reverse=True)[:6]
            
            if lista_pontuada:
                msg = f"💎 <b>SMART TIPSTER: RAIO-X COMPLETO DO DIA</b> 💎\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n🎯 <i>Métricas de Chutes, Cantos e Radar de Faltas:</i>\n\n"
                
                for item in lista_pontuada:
                    msg += f"{item['jogo']}\n"
                    msg += f"   • {item['liga']} (Score: {item['score']} pts)\n"
                    msg += f"   🔥 <b>1º Tempo (Chutes):</b> ~{item['chutes_ht']} finalizações\n"
                    msg += f"   🎯 <b>Chutes no Alvo:</b> ~{item['chutes_gol']} no gol\n"
                    msg += f"   📊 <b>Chutes Totais:</b> ~{item['chutes_tot']}\n"
                    msg += f"   🚩 <b>Escanteios:</b> ~{item['cantos']} cantos\n"
                    
                    # O Gatilho de Faltas formatado no Telegram
                    if float(item['faltas']) >= 26.5:
                        msg += f"   🪓 <b>Cenário de Guerra:</b> ~{item['faltas']} faltas! Excelente para buscar 'Mais de 1.5 Faltas' em Zagueiros/Volantes.\n\n"
                    else:
                        msg += f"   ⚠️ <b>Faltas Estimadas:</b> ~{item['faltas']} faltas\n\n"
                
                if enviar_alerta_telegram(msg): 
                    st.sidebar.success("🔥 Raio-X completo e Radares enviados ao Telegram com sucesso!")
                else: 
                    st.sidebar.error("❌ Erro ao enviar para o Telegram.")
            else:
                st.sidebar.warning("⚠️ Nenhum jogo encontrado para hoje.")
        else:
            st.sidebar.warning("⚠️ Não há partidas agendadas nas ligas monitoradas.")
