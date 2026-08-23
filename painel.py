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

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v35_sofascore" 
DATA_HOJE_STR = datetime.now(FUSO_BR).strftime("%Y-%m-%d")

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

def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    return requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}).status_code == 200

# =========================================================
# MOTOR SOFASCORE RAPIDAPI
# =========================================================

@st.cache_data(persist="disk")
def buscar_jogos_ligas_monitoradas_por_data(data_str, key, cache_key):
    url = "https://sofascore.p.rapidapi.com/matches/get-by-date"
    querystring = {"date": data_str}
    headers = {'x-rapidapi-host': API_HOST, 'x-rapidapi-key': key}
    
    try:
        res = requests.get(url, headers=headers, params=querystring)
        if res.status_code != 200:
            st.error(f"🚨 ERRO DA API SOFASCORE (Status {res.status_code}): {res.text}")
            return []
            
        dados = res.json()
        jogos_validos = []
        lista_eventos = dados.get('events', []) if isinstance(dados, dict) else []
        
        for event in lista_eventos:
            liga_id = event.get('tournament', {}).get('uniqueTournament', {}).get('id')
            if liga_id in LIGAS_MONITORADAS and event.get('status', {}).get('type') == 'notstarted':
                dt_inicio = datetime.fromtimestamp(event.get('startTimestamp', 0), tz=FUSO_BR).strftime("%H:%M")
                jogos_validos.append({
                    'FixtureID': event.get('id'),
                    'LeagueID': liga_id, 
                    'Liga': LIGAS_MONITORADAS[liga_id],
                    'Mandante': event.get('homeTeam', {}).get('name'), 
                    'Visitante': event.get('awayTeam', {}).get('name'),
                    'HomeID': event.get('homeTeam', {}).get('id'), 
                    'AwayID': event.get('awayTeam', {}).get('id'),
                    'Horário': dt_inicio
                })
        return jogos_validos
    except Exception as e:
        st.error(f"🚨 ERRO INTERNO DO PYTHON: {e}")
        return []

@st.cache_data(persist="disk")
def buscar_estatisticas_time(team_id, league_id, key, data_cache):
    url = "https://sofascore.p.rapidapi.com/teams/get-statistics"
    querystring = {"teamId": team_id, "tournamentId": league_id}
    headers = {'x-rapidapi-host': API_HOST, 'x-rapidapi-key': key}
    
    try:
        stats = requests.get(url, headers=headers, params=querystring, timeout=10).json()
        dados = stats.get('statistics', {})
        return {
            'gf_home': dados.get('goalsScored', 1.3), 
            'ga_home': dados.get('goalsConceded', 1.0),
            'gf_away': dados.get('goalsScored', 1.1), 
            'ga_away': dados.get('goalsConceded', 1.2)
        }
    except: 
        return {'gf_home': 1.2, 'ga_home': 1.1, 'gf_away': 1.0, 'ga_away': 1.2}

@st.cache_data(persist="disk")
def buscar_metricas_completas_avancadas(team_id, key, data_cache):
    url = "https://sofascore.p.rapidapi.com/teams/get-last-matches"
    querystring = {"teamId": team_id, "page": "0"}
    headers = {'x-rapidapi-host': API_HOST, 'x-rapidapi-key': key}
    
    try:
        data = requests.get(url, headers=headers, params=querystring, timeout=10).json()
        eventos = data.get('events', [])[:8]
        
        c_pro, c_contra, s_tot, s_gol, faltas_lista = [], [], [], [], []
        
        for f in eventos:
            f_id = f.get('id')
            time.sleep(0.2) 
            url_stats = "https://sofascore.p.rapidapi.com/matches/get-statistics"
            res_stats = requests.get(url_stats, headers=headers, params={"matchId": f_id}).json()
            
            is_home = f.get('homeTeam', {}).get('id') == team_id
            
            if res_stats.get('statistics'):
                for periodo in res_stats['statistics']:
                    if periodo.get('period') == 'ALL':
                        for grupo in periodo.get('groups', []):
                            for item in grupo.get('statisticsItems', []):
                                nome = item.get('name')
                                val_home = float(item.get('home', 0))
                                val_away = float(item.get('away', 0))
                                
                                val_pro = val_home if is_home else val_away
                                val_contra = val_away if is_home else val_home
                                
                                if nome == 'Corner kicks':
                                    c_pro.append(val_pro)
                                    c_contra.append(val_contra)
                                elif nome == 'Total shots':
                                    s_tot.append(val_pro)
                                elif nome == 'Shots on target':
                                    s_gol.append(val_pro)
                                elif nome == 'Fouls':
                                    faltas_lista.append(val_pro)
                                    
        div = max(len(c_pro), 1)
        return {
            'corners_for': sum(c_pro)/div if c_pro else 4.8, 
            'corners_ag': sum(c_contra)/div if c_contra else 4.5,
            'shots_total': sum(s_tot)/max(len(s_tot), 1) if s_tot else 12.5,
            'shots_on_goal': sum(s_gol)/max(len(s_gol), 1) if s_gol else 4.2,
            'fouls': sum(faltas_lista)/max(len(faltas_lista), 1) if faltas_lista else 12.0
        }
    except: 
        return {'corners_for': 4.5, 'corners_ag': 4.5, 'shots_total': 12.0, 'shots_on_goal': 4.2, 'fouls': 13.5}

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Configurações de Análise IA")

if st.sidebar.button("💎 Enviar Top Melhores Entradas (Telegram)", key="btn_bilhete_full"):
    jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    
    if jogos_hoje:
        total_jogos = len(jogos_hoje)
        st.sidebar.info(f"⚽ {total_jogos} jogos encontrados. Iniciando análise via Sofascore...")
        barra_progresso = st.sidebar.progress(0)
        texto_status = st.sidebar.empty()
        lista_pontuada = []
        
        for idx, j in enumerate(jogos_hoje): 
            texto_status.markdown(f"⏳ **Analisando ({idx+1}/{total_jogos}):**\n{j['Mandante']} x {j['Visitante']}")
            try:
                s_h = buscar_estatisticas_time(j['HomeID'], j['LeagueID'], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                s_a = buscar_estatisticas_time(j['AwayID'], j['LeagueID'], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                m_h = buscar_metricas_completas_avancadas(j['HomeID'], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                m_a = buscar_metricas_completas_avancadas(j['AwayID'], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                
                tot_gols = ((s_h.get('gf_home', 1.2) + s_a.get('ga_away', 1.2)) / 2) + ((s_a.get('gf_away', 1.2) + s_h.get('ga_home', 1.2)) / 2)
                c_tot = m_h['corners_for'] + m_a['corners_for']
                s_tot_game = m_h['shots_total'] + m_a['shots_total']
                s_gol_game = m_h['shots_on_goal'] + m_a['shots_on_goal']
                f_tot_game = m_h['fouls'] + m_a['fouls']
                
                chutes_ht_tot = (m_h['shots_total'] * 0.45) + (m_a['shots_total'] * 0.45) 
                
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
                    'h_cantos': f"{m_h['corners_for']:.1f}", 'a_nome': j['Visitante'], 'a_chutes': f"{m_a['shots_total']:.1f}", 
                    'a_alvo': f"{m_a['shots_on_goal']:.1f}", 'a_cantos': f"{m_a['corners_for']:.1f}"
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
                msg += f"   🛡️ <b>RAIO-X POR TIME:</b>\n"
                msg += f"   🏠 {item['h_nome']}: {item['h_chutes']} Chutes | {item['h_alvo']} no Alvo | {item['h_cantos']} Escanteios\n"
                msg += f"   ✈️ {item['a_nome']}: {item['a_chutes']} Chutes | {item['a_alvo']} no Alvo | {item['a_cantos']} Escanteios\n"
                msg += f"   ━━━━━━━━━━━━━━━━━━━━━\n\n"
            enviar_alerta_telegram(msg)
            st.sidebar.success("🔥 Raio-X avançado enviado com sucesso!")
        else: st.sidebar.warning("⚠️ Nenhum jogo com estatísticas suficientes hoje.")
    else:
        st.sidebar.warning("⚠️ Nenhum jogo agendado para as ligas monitoradas hoje.")

if st.sidebar.button("🛡️ Enviar Chance Dupla (Telegram)", key="btn_chance_dupla"):
    jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    
    if jogos_hoje:
        total_jogos = len(jogos_hoje)
        st.sidebar.info(f"🛡️ {total_jogos} jogos encontrados. Analisando Chance Dupla...")
        barra_progresso = st.sidebar.progress(0)
        texto_status = st.sidebar.empty()
        lista_pontuada = []
        
        for idx, j in enumerate(jogos_hoje):
            texto_status.markdown(f"⏳ **Analisando ({idx+1}/{total_jogos}):**\n{j['Mandante']} x {j['Visitante']}")
            try:
                m_h = buscar_metricas_completas_avancadas(j['HomeID'], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                m_a = buscar_metricas_completas_avancadas(j['AwayID'], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                
                chutes_casa = m_h['shots_total']
                chutes_fora = m_a['shots_total']
                
                if chutes_casa > chutes_fora + 2.5: sugestao = "1X (Mandante ou Empate)"
                elif chutes_fora > chutes_casa + 2.5: sugestao = "X2 (Visitante ou Empate)"
                else: sugestao = "12 (Qualquer um vence / Sem Empate)"

                score = 2 + (1 if abs(chutes_casa - chutes_fora) > 4 else 0)

                lista_pontuada.append({
                    'score': score, 'jogo': f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b> [{j['Horário']}]",
                    'liga': f"🏆 {j['Liga']}", 'sugestao': sugestao, 'total_chutes': chutes_casa + chutes_fora
                })
            except: pass
            barra_progresso.progress((idx + 1) / total_jogos)

        texto_status.empty()
        barra_progresso.empty()
        lista_pontuada = sorted(lista_pontuada, key=lambda x: x['total_chutes'], reverse=True)[:6]

        if lista_pontuada:
            msg = f"🛡️ <b>CHANCE DUPLA - ANÁLISE AUTOMÁTICA</b>\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
            for item in lista_pontuada:
                msg += f"{item['jogo']}\n{item['liga']}\n🎯 <b>Entrada Sugerida:</b> {item['sugestao']}\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            enviar_alerta_telegram(msg)
            st.sidebar.success("🛡️ Alertas de Chance Dupla enviados!")
        else: st.sidebar.warning("⚠️ Nenhum jogo validado hoje.")

if st.sidebar.button("⚽ Enviar Alertas de Gols (Telegram)", key="btn_gols"):
    jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    
    if jogos_hoje:
        total_jogos = len(jogos_hoje)
        st.sidebar.info(f"⚽ {total_jogos} jogos encontrados. Analisando Gols...")
        barra_progresso = st.sidebar.progress(0)
        texto_status = st.sidebar.empty()
        lista_pontuada = []
        
        for idx, j in enumerate(jogos_hoje):
            try:
                s_h = buscar_estatisticas_time(j['HomeID'], j['LeagueID'], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                s_a = buscar_estatisticas_time(j['AwayID'], j['LeagueID'], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                m_h = buscar_metricas_completas_avancadas(j['HomeID'], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                m_a = buscar_metricas_completas_avancadas(j['AwayID'], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                
                tot_gols_proj = ((s_h.get('gf_home', 1.0) + s_a.get('ga_away', 1.0)) / 2) + ((s_a.get('gf_away', 1.0) + s_h.get('ga_home', 1.0)) / 2)
                chutes_alvo_tot = m_h['shots_on_goal'] + m_a['shots_on_goal']

                if chutes_alvo_tot >= 8.5 and tot_gols_proj >= 2.5: sugestao = "Mais de 2.5 Gols (Over 2.5)"
                elif chutes_alvo_tot >= 6.5 and tot_gols_proj >= 1.5: sugestao = "Mais de 1.5 Gols (Over 1.5)"
                else: sugestao = "Ambas Equipes Marcam (BTTS)"

                lista_pontuada.append({
                    'score': tot_gols_proj, 'jogo': f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b> [{j['Horário']}]",
                    'liga': f"🏆 {j['Liga']}", 'sugestao': sugestao
                })
            except: pass
            barra_progresso.progress((idx + 1) / total_jogos)

        texto_status.empty()
        barra_progresso.empty()
        lista_pontuada = sorted(lista_pontuada, key=lambda x: x['score'], reverse=True)[:6]

        if lista_pontuada:
            msg = f"⚽ <b>PROJEÇÃO DE GOLS - ANÁLISE AUTOMÁTICA</b>\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
            for item in lista_pontuada:
                msg += f"{item['jogo']}\n{item['liga']}\n🎯 <b>Entrada Sugerida:</b> {item['sugestao']}\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            enviar_alerta_telegram(msg)
            st.sidebar.success("⚽ Alertas de Gols enviados!")

st.markdown("---")
st.title("⚽ Dashboard Operacional")
st.success("Motor de dados atualizado para o endpoint oficial do Sofascore (`/matches/get-by-date`). Selecione as opções na barra lateral para disparar os relatórios no Telegram.")
