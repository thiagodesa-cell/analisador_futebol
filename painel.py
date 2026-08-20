import streamlit as st
import pandas as pd
import requests
import time
import math
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="Painel Pro - Tipster Ultimate Radar v33", layout="wide")

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

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v33_anti_travamento" 
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
        data = requests.get(url, headers=headers, timeout=10).json()
        for f in data.get('response', []):
            f_id = f['fixture']['id']
            time.sleep(0.1) 
            data_s = requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={f_id}", headers=headers, timeout=10).json()
            
            t_c = o_c = t_st = t_sg = t_f = 0
            if data_s.get('results', 0) > 0:
                for item in data_s['response']:
                    for s in item['statistics']:
                        val = s['value']
                        if val is not None:
                            if s['type'] == 'Corner Kicks':
                                if item['team']['id'] == team_id: t_c = int(val)
                                else: o_c = int(val)
                            elif s['type'] == 'Total Shots': 
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
def obter_arbitro_fator(referee_name, league_id, season, key, data_cache):
    if not referee_name: return 1.0
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}"
    try:
        res = requests.get(url, headers={'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}).json()
        cartoes_total = 0
        jogos_arbitro = 0
        for fix in res.get("response", []):
            if fix.get("fixture", {}).get("referee") and referee_name in fix.get("fixture", {}).get("referee"):
                if fix.get("fixture", {}).get("status", {}).get("short") == "FT":
                    jogos_arbitro += 1
                    cartoes_total += 5.0 
        if jogos_arbitro == 0: return 1.0
        media = cartoes_total / jogos_arbitro
        return 1.15 if media >= 5.0 else 0.85
    except: return 1.0

@st.cache_data(persist="disk")
def obter_jogador_alvo(team_id, league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/players?team={team_id}&league={league_id}&season={season}&page=1"
    try:
        time.sleep(0.1) 
        res = requests.get(url, headers={'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}).json()
        top_jogador = None
        max_amarelos = -1
        for item in res.get("response", []):
            stats = item["statistics"][0]
            amarelos = stats.get("cards", {}).get("yellow") or 0
            if amarelos > max_amarelos:
                max_amarelos = amarelos
                top_jogador = {
                    "nome": item["player"]["name"],
                    "amarelos": amarelos,
                }
        return top_jogador
    except: return None

@st.cache_data(persist="disk")
def buscar_jogos_ligas_monitoradas_por_data(data_str, key, cache_key):
    url = f"https://v3.football.api-sports.io/fixtures?date={data_str}"
    try:
        data = requests.get(url, headers={'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}).json()
        return [{
            'FixtureID': f['fixture']['id'],
            'Referee': f['fixture']['referee'],
            'LeagueID': f['league']['id'], 'Liga': LIGAS_MONITORADAS[f['league']['id']],
            'Mandante': f['teams']['home']['name'], 'Visitante': f['teams']['away']['name'],
            'HomeID': f['teams']['home']['id'], 'AwayID': f['teams']['away']['id'],
            'Horário': converter_para_horario_brasilia(f['fixture']['date'])[2]
        } for f in data.get('response', []) if f['league']['id'] in LIGAS_MONITORADAS and f['fixture']['status']['short'] in ['NS', 'TBD']]
    except: return []

if id_time1 and LEAGUE_ID:
    st.title(f"⚽ Painel Ultimate Radar v33 - {opcao_liga}")
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
        else: st.sidebar.warning("⚠️ Nenhum jogo com estatísticas robustas encontrado hoje.")

# ==========================================
# BOTÃO 2: CANTOS E CARTÕES
# ==========================================
if st.sidebar.button("🟨 Enviar Top Cantos e Cartões (Telegram)", key="btn_cantos_cartoes"):
    jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    
    if jogos_hoje:
        total_jogos = len(jogos_hoje)
        st.sidebar.info(f"🟨 {total_jogos} jogos encontrados. Analisando...")
        barra_progresso = st.sidebar.progress(0)
        texto_status = st.sidebar.empty()
        lista_pontuada = []
        
        for idx, j in enumerate(jogos_hoje):
            texto_status.markdown(f"⏳ **Aguarde... Analisando ({idx+1}/{total_jogos}):**\n{j['Mandante']} x {j['Visitante']}")
            try:
                m_h = buscar_metricas_completas_avancadas(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                m_a = buscar_metricas_completas_avancadas(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                
                score_cartoes = 0
                if m_h['corners_for'] + m_a['corners_for'] >= 9.0: score_cartoes += 1
                if m_h['fouls'] + m_a['fouls'] >= 26.5: score_cartoes += 2
                if m_h['corners_for'] >= 5.0: score_cartoes += 1
                if m_a['corners_for'] >= 4.0: score_cartoes += 1

                fator_arbitro = obter_arbitro_fator(j.get('Referee'), j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                cartoes_casa_proj = round(2.5 * fator_arbitro, 1)
                cartoes_fora_proj = round(1.5 * fator_arbitro, 1)

                alvo_casa = obter_jogador_alvo(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                alvo_fora = obter_jogador_alvo(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)

                lista_pontuada.append({
                    'score': score_cartoes, 'jogo': f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b> [{j['Horário']}]",
                    'cantos_casa': m_h['corners_for'], 'cantos_fora': m_a['corners_for'],
                    'cartoes_casa': cartoes_casa_proj, 'cartoes_fora': cartoes_fora_proj,
                    'alvo_casa': alvo_casa, 'alvo_fora': alvo_fora, 'h_nome': j['Mandante'], 'a_nome': j['Visitante']
                })
            except Exception: pass
            barra_progresso.progress((idx + 1) / total_jogos)

        texto_status.empty()
        barra_progresso.empty()
        lista_pontuada = sorted(lista_pontuada, key=lambda x: x['score'], reverse=True)[:6]

        if lista_pontuada:
            msg = f"🟨 <b>SMART TIPSTER: CANTOS E CARTÕES</b> 🟥\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
            for item in lista_pontuada:
                msg += f"{item['jogo']}\n\n🚩 <b>LINHA DE ESCANTEIOS:</b>\n"
                msg += f"🛡️ {item['h_nome']}: Mais de {item['cantos_casa']:.1f} Escanteios\n"
                msg += f"✈️ {item['a_nome']}: Mais de {item['cantos_fora']:.1f} Escanteios\n\n"
                msg += f"🟨 <b>LINHA DE CARTÕES:</b>\n"
                msg += f"🛡️ {item['h_nome']}: Mais de {item['cartoes_casa']} Cartões\n"
                msg += f"✈️ {item['a_nome']}: Mais de {item['cartoes_fora']} Cartões\n\n"
                msg += f"⚠️ <b>ALVO PARA CARTÃO:</b>\n"
                if item['alvo_casa']: msg += f"🎯 <b>{item['alvo_casa']['nome']}</b> - <i>{item['alvo_casa']['amarelos']} amarelos.</i>\n"
                if item['alvo_fora']: msg += f"🎯 <b>{item['alvo_fora']['nome']}</b> - <i>{item['alvo_fora']['amarelos']} amarelos.</i>\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            enviar_alerta_telegram(msg)
            st.sidebar.success("🟨 Relatório de Cartões enviado com sucesso!")
        else: st.sidebar.warning("⚠️ Nenhum jogo com estatísticas robustas encontrado.")

st.sidebar.markdown("---")

# ==========================================
# BOTÃO 3: CHANCE DUPLA (NOVO)
# ==========================================
if st.sidebar.button("🛡️ Enviar Chance Dupla (Telegram)", key="btn_chance_dupla"):
    jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    
    if jogos_hoje:
        total_jogos = len(jogos_hoje)
        st.sidebar.info(f"🛡️ {total_jogos} jogos encontrados. Analisando Chance Dupla...")
        barra_progresso = st.sidebar.progress(0)
        texto_status = st.sidebar.empty()
        lista_pontuada = []
        
        for idx, j in enumerate(jogos_hoje):
            texto_status.markdown(f"⏳ **Aguarde... Analisando ({idx+1}/{total_jogos}):**\n{j['Mandante']} x {j['Visitante']}")
            try:
                m_h = buscar_metricas_completas_avancadas(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                m_a = buscar_metricas_completas_avancadas(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                
                # TRAVA DE SEGURANÇA: IGNORA JOGOS COM DADOS ZERADOS NA API (0.0)
                if (m_h['shots_total'] + m_a['shots_total']) <= 1.0:
                    continue 

                chutes_casa = m_h['shots_total']
                chutes_fora = m_a['shots_total']
                
                if chutes_casa > chutes_fora + 2.5: sugestao = "1X (Mandante ou Empate)"
                elif chutes_fora > chutes_casa + 2.5: sugestao = "X2 (Visitante ou Empate)"
                else: sugestao = "12 (Qualquer um vence / Sem Empate)"

                score = 2
                if abs(chutes_casa - chutes_fora) > 4: score += 1

                lista_pontuada.append({
                    'score': score, 'jogo': f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b> [{j['Horário']}]",
                    'liga': f"🏆 {j['Liga']}", 'sugestao': sugestao, 'total_chutes': chutes_casa + chutes_fora
                })
            except Exception: pass
            barra_progresso.progress((idx + 1) / total_jogos)

        texto_status.empty()
        barra_progresso.empty()
        lista_pontuada = sorted(lista_pontuada, key=lambda x: x['total_chutes'], reverse=True)[:6]

        if lista_pontuada:
            msg = f"🛡️ <b>CHANCE DUPLA - ANÁLISE AUTOMÁTICA</b>\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
            for item in lista_pontuada:
                msg += f"{item['jogo']}\n{item['liga']} (Score: {item['score']} pts)\n"
                msg += f"🎯 <b>Entrada Sugerida:</b> {item['sugestao']}\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            enviar_alerta_telegram(msg)
            st.sidebar.success("🛡️ Alertas de Chance Dupla enviados com sucesso!")
        else: st.sidebar.warning("⚠️ Nenhum jogo validado para Chance Dupla hoje.")

# ==========================================
# BOTÃO 4: MERCADO DE GOLS (NOVO)
# ==========================================
if st.sidebar.button("⚽ Enviar Alertas de Gols (Telegram)", key="btn_gols"):
    jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    
    if jogos_hoje:
        total_jogos = len(jogos_hoje)
        st.sidebar.info(f"⚽ {total_jogos} jogos encontrados. Analisando Gols...")
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
                
                # TRAVA DE SEGURANÇA: IGNORA JOGOS ZERADOS
                if (m_h['shots_on_goal'] + m_a['shots_on_goal']) <= 1.0:
                    continue

                lambda_home = (s_h.get('gf_home', 1.0) + s_a.get('ga_away', 1.0)) / 2
                lambda_away = (s_a.get('gf_away', 1.0) + s_h.get('ga_home', 1.0)) / 2
                tot_gols_proj = lambda_home + lambda_away
                chutes_alvo_tot = m_h['shots_on_goal'] + m_a['shots_on_goal']

                if chutes_alvo_tot >= 8.5 and tot_gols_proj >= 2.5: sugestao = "Mais de 2.5 Gols (Over 2.5)"
                elif chutes_alvo_tot >= 6.5 and tot_gols_proj >= 1.5: sugestao = "Mais de 1.5 Gols (Over 1.5)"
                else: sugestao = "Ambas Equipes Marcam (BTTS)"

                score = 2
                if tot_gols_proj >= 3.0: score += 1

                lista_pontuada.append({
                    'score': score, 'jogo': f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b> [{j['Horário']}]",
                    'liga': f"🏆 {j['Liga']}", 'sugestao': sugestao, 'tot_gols_proj': tot_gols_proj
                })
            except Exception: pass
            barra_progresso.progress((idx + 1) / total_jogos)

        texto_status.empty()
        barra_progresso.empty()
        lista_pontuada = sorted(lista_pontuada, key=lambda x: x['tot_gols_proj'], reverse=True)[:6]

        if lista_pontuada:
            msg = f"⚽ <b>PROJEÇÃO DE GOLS - ANÁLISE AUTOMÁTICA</b>\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
            for item in lista_pontuada:
                msg += f"{item['jogo']}\n{item['liga']} (Score: {item['score']} pts)\n"
                msg += f"🎯 <b>Entrada Sugerida:</b> {item['sugestao']}\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            enviar_alerta_telegram(msg)
            st.sidebar.success("⚽ Alertas de Gols enviados com sucesso!")
        else: st.sidebar.warning("⚠️ Nenhum jogo validado para Gols hoje.")

# ==========================================
# BOTÃO 5: SUGESTÃO DE PLACAR EXATO (NOVO - SINCRONIZADO)
# ==========================================
if st.sidebar.button("🎯 Enviar Sugestão de Placar (Telegram)", key="btn_placar"):
    jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    
    if jogos_hoje:
        total_jogos = len(jogos_hoje)
        st.sidebar.info(f"🎯 {total_jogos} jogos encontrados. Cruzando dados para Placares...")
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
                
                # TRAVA DE SEGURANÇA CONTRA DADOS ZERADOS
                if (m_h['shots_total'] + m_a['shots_total']) <= 1.0:
                    continue

                # 1. PEGA A MÉDIA DE GOLS
                gols_base_casa = (s_h.get('gf_home', 1.0) + s_a.get('ga_away', 1.0)) / 2
                gols_base_fora = (s_a.get('gf_away', 1.0) + s_h.get('ga_home', 1.0)) / 2

                # 2. PEGA A MÉDIA DE CHUTES (Para cruzar os dados)
                chutes_casa = m_h['shots_total']
                chutes_fora = m_a['shots_total']
                alvo_casa = m_h['shots_on_goal']
                alvo_fora = m_a['shots_on_goal']

                # 3. CÁLCULO HÍBRIDO (50% Gols Históricos + 50% Poder de Chute)
                # Assumimos que a cada ~3.5 chutes no alvo, sai 1 gol
                xg_casa = (gols_base_casa * 0.5) + ((alvo_casa / 3.5) * 0.5)
                xg_fora = (gols_base_fora * 0.5) + ((alvo_fora / 3.5) * 0.5)

                placar_casa = round(xg_casa)
                placar_fora = round(xg_fora)

                # 4. TRAVA DE COERÊNCIA COM A CHANCE DUPLA
                if chutes_casa > chutes_fora + 2.5: 
                    # Lógica da Chance Dupla: 1X (Mandante ou Empate)
                    # Proíbe o visitante de vencer no placar sugerido
                    if placar_fora > placar_casa:
                        placar_casa = placar_fora 
                
                elif chutes_fora > chutes_casa + 2.5:
                    # Lógica da Chance Dupla: X2 (Visitante ou Empate)
                    # Proíbe o mandante de vencer no placar sugerido
                    if placar_casa > placar_fora:
                        placar_fora = placar_casa
                
                else:
                    # Lógica da Chance Dupla: 12 (Sem Empate)
                    # Tenta forçar um vencedor baseado em quem chuta mais no alvo
                    if placar_casa == placar_fora:
                        if alvo_casa > alvo_fora: placar_casa += 1
                        elif alvo_fora > alvo_casa: placar_fora += 1

                lista_pontuada.append({
                    'msg_placar': f"⚽ {j['Mandante']} {placar_casa} x {placar_fora} {j['Visitante']}",
                    'confianca': xg_casa + xg_fora # Ordena pelos jogos com maior tendência de gols
                })
            except Exception: pass
            barra_progresso.progress((idx + 1) / total_jogos)

        texto_status.empty()
        barra_progresso.empty()
        lista_pontuada = sorted(lista_pontuada, key=lambda x: x['confianca'], reverse=True)[:8]

        if lista_pontuada:
            msg = f"🎯 <b>SUGESTÃO DE PLACAR EXATO</b>\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            for item in lista_pontuada:
                msg += f"{item['msg_placar']}\n\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━\n"
            enviar_alerta_telegram(msg)
            st.sidebar.success("🎯 Sugestões de Placar enviadas com sucesso!")
        else: st.sidebar.warning("⚠️ Nenhum jogo validado para Sugestão de Placar hoje.")
