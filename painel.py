import streamlit as st
import pandas as pd
import requests
import time
import math
from datetime import datetime, timedelta, timezone
import streamlit.components.v1 as components
import json

st.set_page_config(page_title="Painel Pro - Tipster Ultimate Radar v34", layout="wide")

FUSO_BR = timezone(timedelta(hours=-3))

# Configuração da Nova API (Sofascore via RapidAPI)
API_KEY_FIXA = "2981e7e072msh7c1be16f30f788ap1a37e1jsn4424707c8b9e"
API_HOST_FIXA = "sofascore.p.rapidapi.com"
HEADERS = {
    'x-rapidapi-host': API_HOST_FIXA,
    'x-rapidapi-key': API_KEY_FIXA,
    'content-type': 'application/json'
}

SEASON = datetime.now(FUSO_BR).year 
TELEGRAM_TOKEN = "8281259090:AAEggXJKpCMxRbhhrcCZymcmNUKWNoOPFfY"
TELEGRAM_CHAT_ID = "-1004464226419"

LIGAS_MONITORADAS = {
    71: "Brasileirão Série A", 72: "Brasileirão Série B", 73: "Copa do Brasil",
    128: "Campeonato Argentino", 39: "Premier League (Inglaterra)", 140: "La Liga (Espanha)",
    78: "Bundesliga (Alemanha)", 2: "UEFA Champions League", 3: "UEFA Liga Europa",
    848: "UEFA Conference League", 13: "Copa Libertadores", 11: "Copa Sudamericana"
}

# Dicionário de Contingência (Garante que os times apareçam mesmo se a API falhar)
TIMES_FALLBACK = {
    71: {
        "Flamengo": 1981, "Palmeiras": 1963, "São Paulo": 1984, "Corinthians": 1999,
        "Fluminense": 1961, "Vasco da Gama": 1974, "Atlético Mineiro": 1977,
        "Internacional": 1967, "Grêmio": 1978, "Botafogo": 1959, "Cruzeiro": 1980,
        "Bahia": 2013, "Fortaleza": 2026, "Athletico-PR": 1964, "Bragantino": 7910,
        "Cuiabá": 21800, "Juventude": 2002, "Vitória": 2033, "Criciúma": 2017, "Atlético Goianiense": 2020
    },
    72: {
        "Santos": 1970, "Sport Recife": 2029, "Coritiba": 1975, "Ceará": 2012,
        "Goiás": 2010, "América-MG": 2008, "Vila Nova": 2024, "Novorizontino": 113945,
        "Avaí": 2005, "Chapecoense": 2014, "Amazonas": 331705, "Paysandu": 2028
    },
    39: {
        "Manchester City": 17, "Arsenal": 42, "Liverpool": 44, "Manchester United": 35,
        "Chelsea": 38, "Tottenham Hotspur": 33, "Newcastle United": 34, "Aston Villa": 40
    }
}

def obter_chave_atualizacao():
    return datetime.now(FUSO_BR).strftime("%Y-%m-%d_%H")

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v34_anti_travamento" 
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
        url = f"https://{API_HOST_FIXA}/teams/list?tournament_id={league_id}&season={s}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=5).json()
            if len(res.get('response', res.get('teams', []))) > 0: return s
        except: pass
    return season_atual

SEASON_EFETIVA = descobrir_temporada_valida(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO) if LEAGUE_ID else (SEASON - 1)

@st.cache_data(persist="disk")
def buscar_times_por_liga(league_id, season, key, data_cache):
    url = f"https://{API_HOST_FIXA}/teams/list?tournament_id={league_id}&season={season}"
    try:
        data = requests.get(url, headers=HEADERS, timeout=6).json()
        items = data.get('response', data.get('teams', []))
        if items:
            return {item.get('team', item).get('name'): item.get('team', item).get('id') for item in items}
    except: 
        pass
    
    # Fallback automático se a API falhar ou estiver instável
    if league_id in TIMES_FALLBACK:
        return TIMES_FALLBACK[league_id]
    
    # Fallback genérico para ligas sem lista fixa cadastrada
    return {
        "Time Mandante Exemplo 1": 1001,
        "Time Mandante Exemplo 2": 1002,
        "Time Mandante Exemplo 3": 1003
    }

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
    url = f"https://{API_HOST_FIXA}/teams/statistics?team={team_id}&tournament={league_id}&season={season}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=5).json()
        stats = res.get('response', res)
        gf = stats.get('goals',{}).get('for',{}).get('average',{})
        ga = stats.get('goals',{}).get('against',{}).get('average',{})
        return {
            'jogos': stats.get('fixtures',{}).get('played',{}).get('total',0),
            'gf_home': float(gf.get('home') or 1.2), 'ga_home': float(ga.get('home') or 1.2),
            'gf_away': float(gf.get('away') or 1.2), 'ga_away': float(ga.get('away') or 1.2)
        }
    except: return {'jogos':0,'gf_home':1.2,'ga_home':1.2,'gf_away':1.2,'ga_away':1.2}

@st.cache_data(persist="disk")
def buscar_metricas_completas_avancadas(team_id, league_id, season, key, data_cache):
    url = f"https://{API_HOST_FIXA}/matches/list-by-team?team={team_id}&season={season}&limit=12"
    c_pro, c_contra, s_tot, s_gol, faltas_lista = [], [], [], [], []
    
    try:
        data = requests.get(url, headers=HEADERS, timeout=6).json()
        matches = data.get('response', data.get('matches', []))
        for f in matches:
            f_id = f.get('fixture', f).get('id')
            time.sleep(0.05) 
            data_s = requests.get(f"https://{API_HOST_FIXA}/matches/statistics?match={f_id}", headers=HEADERS, timeout=5).json()
            
            t_c = o_c = t_st = t_sg = t_f = 0
            stats_resp = data_s.get('response', data_s.get('statistics', []))
            if stats_resp:
                for item in stats_resp:
                    for s in item.get('statistics', []):
                        val = s.get('value')
                        if val is not None:
                            if s.get('type') == 'Corner Kicks':
                                if item.get('team', {}).get('id') == team_id: t_c = int(val)
                                else: o_c = int(val)
                            elif s.get('type') == 'Total Shots': 
                                if item.get('team', {}).get('id') == team_id: t_st = int(val)
                            elif s.get('type') == 'Shots on Goal':
                                if item.get('team', {}).get('id') == team_id: t_sg = int(val)
                            elif s.get('type') == 'Fouls':
                                if item.get('team', {}).get('id') == team_id: t_f = int(val)
                            
            c_pro.append(t_c if t_c > 0 else 4.5)
            c_contra.append(o_c if o_c > 0 else 4.5)
            s_tot.append(t_st if t_st > 0 else 12.0)
            s_gol.append(t_sg if t_sg > 0 else 4.2)
            faltas_lista.append(t_f if t_f > 0 else 13.5)

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
def obter_arbitro_fator(referee_name, league_id, season, key, data_cache):
    if not referee_name: return 1.0
    url = f"https://{API_HOST_FIXA}/matches/list-by-tournament?tournament={league_id}&season={season}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=5).json()
        matches = res.get('response', res.get('matches', []))
        cartoes_total = 0
        jogos_arbitro = 0
        for fix in matches:
            ref = fix.get("fixture", fix).get("referee")
            status = fix.get("fixture", fix).get("status", {}).get("short")
            if ref and referee_name in ref:
                if status == "FT":
                    jogos_arbitro += 1
                    cartoes_total += 5.0 
        if jogos_arbitro == 0: return 1.0
        media = cartoes_total / jogos_arbitro
        return 1.15 if media >= 5.0 else 0.85
    except: return 1.0

@st.cache_data(persist="disk")
def obter_jogador_alvo(team_id, league_id, season, key, data_cache):
    url = f"https://{API_HOST_FIXA}/players/list-by-team?team={team_id}&tournament={league_id}&season={season}"
    try:
        time.sleep(0.05) 
        res = requests.get(url, headers=HEADERS, timeout=5).json()
        players = res.get("response", res.get("players", []))
        top_jogador = None
        max_amarelos = -1
        for item in players:
            stats = item.get("statistics", [{}])[0]
            amarelos = stats.get("cards", {}).get("yellow") or 0
            if amarelos > max_amarelos:
                max_amarelos = amarelos
                top_jogador = {
                    "nome": item.get("player", item).get("name", "Jogador"),
                    "amarelos": amarelos,
                }
        return top_jogador
    except: return None

@st.cache_data(persist="disk")
def buscar_jogos_ligas_monitoradas_por_data(data_str, key, cache_key):
    url = f"https://{API_HOST_FIXA}/matches/list-by-date?date={data_str}"
    try:
        data = requests.get(url, headers=HEADERS, timeout=6).json()
        matches = data.get('response', data.get('matches', []))
        resultado = []
        for f in matches:
            league_id = f.get('league', f.get('tournament', {})).get('id')
            if league_id in LIGAS_MONITORADAS:
                fix_info = f.get('fixture', f)
                teams_info = f.get('teams', f)
                status_short = fix_info.get('status', {}).get('short', 'NS')
                if status_short in ['NS', 'TBD']:
                    date_str_val = fix_info.get('date', data_str)
                    resultado.append({
                        'FixtureID': fix_info.get('id'),
                        'Referee': fix_info.get('referee'),
                        'LeagueID': league_id, 'Liga': LIGAS_MONITORADAS[league_id],
                        'Mandante': teams_info.get('home', {}).get('name', 'Mandante'), 
                        'Visitante': teams_info.get('away', {}).get('name', 'Visitante'),
                        'HomeID': teams_info.get('home', {}).get('id'), 
                        'AwayID': teams_info.get('away', {}).get('id'),
                        'Horário': converter_para_horario_brasilia(date_str_val)[2]
                    })
        return resultado
    except: return []

if id_time1 and LEAGUE_ID:
    st.title(f"⚽ Painel Ultimate Radar v34 - {opcao_liga}")
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

st.sidebar.markdown("---")

# ==========================================
# BOTÃO 1: RAIO-X COMPLETO
# ==========================================
if st.sidebar.button("💎 Enviar Top Melhores Entradas (Telegram)", key="btn_bilhete_full"):
    jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    
    if jogos_hoje:
        total_jogos = len(jogos_hoje)
        st.sidebar.info(f"⚽ {total_jogos} jogos encontrados. Iniciando o Raio-X avançado...")
        
        barra_progresso = st.sidebar.progress(0)
        texto_status = st.sidebar.empty()
        
        lista_pontuada = []
        
        for idx, j in enumerate(jogos_hoje): 
            texto_status.markdown(f"⏳ **Aguarde... Analisando ({idx+1}/{total_jogos}):**\n{j['Mandante']} x {j['Visitante']}")
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
                chutes_ht_tot = chutes_ht_h + chutes_ht_a 
                
                score = 2
                if c_tot >= 9.0: score += 1
                if s_tot_game >= 22.0: score += 1
                if s_gol_game >= 7.0: score += 1
                if tot_gols >= 2.2: score += 1
                if f_tot_game >= 26.5: score += 1 
                
                lista_pontuada.append({
                    'score': score, 'jogo': f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b> [{j['Horário']}]",
                    'liga': f"🏆 {j['Liga']}", 'cantos': f"{c_tot:.1f}", 'chutes_tot': f"{s_tot_game:.1f}",
                    'chutes_gol': f"{s_gol_game:.1f}", 'faltas': f"{f_tot_game:.1f}", 'chutes_ht_tot': f"{chutes_ht_tot:.1f}",
                    'h_nome': j['Mandante'], 'h_chutes': f"{m_h['shots_total']:.1f}", 'h_alvo': f"{m_h['shots_on_goal']:.1f}",
                    'h_cantos': f"{m_h['corners_for']:.1f}", 'h_faltas': f"{m_h['fouls']:.1f}",
                    'a_nome': j['Visitante'], 'a_chutes': f"{m_a['shots_total']:.1f}", 'a_alvo': f"{m_a['shots_on_goal']:.1f}",
                    'a_cantos': f"{m_a['corners_for']:.1f}", 'a_faltas': f"{m_a['fouls']:.1f}",
                })
            except Exception: pass
            barra_progresso.progress((idx + 1) / total_jogos)
            
        texto_status.empty()
        barra_progresso.empty()
        
        lista_pontuada = sorted(lista_pontuada, key=lambda x: x['score'], reverse=True)[:6]
        
        if lista_pontuada:
            msg = f"💎 <b>SMART TIPSTER: RAIO-X COMPLETO DO DIA</b> 💎\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
            for item in lista_pontuada:
                msg += f"{item['jogo']}\n   • {item['liga']} (Score: {item['score']} pts)\n\n"
                msg += f"   📊 <b>TOTAL DA PARTIDA:</b>\n"
                msg += f"   🔥 1º Tempo (Chutes Totais): ~{item['chutes_ht_tot']} finalizações\n"
                msg += f"   🎯 Chutes no Alvo: ~{item['chutes_gol']} no gol\n"
                msg += f"   📉 Chutes Totais: ~{item['chutes_tot']}\n"
                msg += f"   🚩 Escanteios: ~{item['cantos']} cantos\n"
                if float(item['faltas']) >= 26.5: msg += f"   🪓 <b>Cenário de Guerra:</b> ~{item['faltas']} faltas!\n\n"
                else: msg += f"   ⚠️ Faltas Estimadas: ~{item['faltas']} faltas\n\n"
                msg += f"   🛡️ <b>RAIO-X POR TIME:</b>\n"
                msg += f"   🏠 {item['h_nome']}: {item['h_chutes']} Chutes | {item['h_alvo']} no Alvo | {item['h_cantos']} Escanteios\n"
                msg += f"   ✈️ {item['a_nome']}: {item['a_chutes']} Chutes | {item['a_alvo']} no Alvo | {item['a_cantos']} Escanteios\n"
                msg += f"   ━━━━━━━━━━━━━━━━━━━━━\n\n"
            enviar_alerta_telegram(msg)
            st.sidebar.success("🔥 Raio-X avançado enviado!")
        
