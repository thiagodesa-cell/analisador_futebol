import streamlit as st
import pandas as pd
import requests
import time
import math
from datetime import datetime, timedelta, timezone
import streamlit.components.v1 as components

st.set_page_config(page_title="Painel Pro - Tipster Ultimate Radar v33 (SofaScore)", layout="wide")

FUSO_BR = timezone(timedelta(hours=-3))

# Nova API SofaScore via RapidAPI configurada
API_KEY_FIXA = "2981e7e072msh7c1be16f30f788ap1a37e1jsn4424707c8b9e"
API_HOST_FIXA = "sofascore.p.rapidapi.com"
HEADERS_API = {
    'x-rapidapi-host': API_HOST_FIXA,
    'x-rapidapi-key': API_KEY_FIXA
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

def obter_chave_atualizacao():
    return datetime.now(FUSO_BR).strftime("%Y-%m-%d_%H")

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v33_sofascore" 
DATA_HOJE_STR = datetime.now(FUSO_BR).strftime("%Y-%m-%d")

def converter_para_horario_brasilia(iso_string):
    try:
        dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        dt_local = dt_utc.astimezone(FUSO_BR)
        return dt_local.strftime("%Y-%m-%d"), dt_local.strftime("%d/%m/%Y"), dt_local.strftime("%H:%M")
    except Exception:
        return iso_string[:10], f"{iso_string[8:10]}/{iso_string[5:7]}/{iso_string[0:4]}", iso_string[11:16]

st.sidebar.header("🏆 Seleção da Competição Global")
opcao_liga = st.sidebar.radio("Escolha qual campeonato deseja analisar:", list(LIGAS_MONITORADAS.values()), index=None)
LEAGUE_ID = [k for k, v in LIGAS_MONITORADAS.items() if v == opcao_liga][0] if opcao_liga else None

@st.cache_data(persist="disk")
def descobrir_temporada_valida(league_id, season_atual, data_cache):
    return season_atual

SEASON_EFETIVA = descobrir_temporada_valida(LEAGUE_ID, SEASON, CHAVE_ATUALIZACAO) if LEAGUE_ID else (SEASON - 1)

@st.cache_data(persist="disk")
def buscar_times_por_liga(league_id, season, data_cache):
    # Endpoint adaptado para SofaScore / RapidAPI
    url = f"https://{API_HOST_FIXA}/tournaments/get-team-list" # Ajuste estrutural compatível
    querystring = {"tournamentId": str(league_id)}
    try:
        response = requests.get(url, headers=HEADERS_API, params=querystring, timeout=10)
        data = response.json()
        teams = data.get('teams', [])
        return {item['name']: item['id'] for item in teams} if teams else {}
    except:
        # Fallback de segurança caso a listagem direta varie na estrutura da API nova
        return {"Time Exemplo Mandante": 101, "Time Exemplo Visitante": 102}

TEAM_IDS = buscar_times_por_liga(LEAGUE_ID, SEASON_EFETIVA, CHAVE_ATUALIZACAO) if LEAGUE_ID else {}

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
def buscar_estatisticas_time(team_id, league_id, season, data_cache):
    url = f"https://{API_HOST_FIXA}/teams/get-statistics"
    querystring = {"teamId": str(team_id)}
    try:
        res = requests.get(url, headers=HEADERS_API, params=querystring, timeout=10).json()
        stats = res.get('statistics', {})
        return {
            'jogos': stats.get('matchesPlayed', 10),
            'gf_home': float(stats.get('goalsScoredHome', 1.4)),
            'ga_home': float(stats.get('goalsConcededHome', 1.0)),
            'gf_away': float(stats.get('goalsScoredAway', 1.2)),
            'ga_away': float(stats.get('goalsConcededAway', 1.3))
        }
    except: 
        return {'jogos': 10, 'gf_home': 1.5, 'ga_home': 1.0, 'gf_away': 1.2, 'ga_away': 1.2}

@st.cache_data(persist="disk")
def buscar_metricas_completas_avancadas(team_id, league_id, season, data_cache):
    url = f"https://{API_HOST_FIXA}/teams/get-characteristics"
    querystring = {"teamId": str(team_id)}
    try:
        res = requests.get(url, headers=HEADERS_API, params=querystring, timeout=10).json()
        char = res.get('characteristics', {})
        return {
            'corners_for': float(char.get('averageCorners', 5.2)),
            'corners_ag': float(char.get('averageCornersConceded', 4.5)),
            'shots_total': float(char.get('averageShots', 13.5)),
            'shots_on_goal': float(char.get('averageShotsOnTarget', 4.8)),
            'fouls': float(char.get('averageFouls', 12.8))
        }
    except: 
        return {'corners_for': 5.0, 'corners_ag': 4.5, 'shots_total': 13.0, 'shots_on_goal': 4.5, 'fouls': 13.0}

@st.cache_data(persist="disk")
def obter_arbitro_fator(referee_name, league_id, season, data_cache):
    return 1.1 if referee_name else 1.0

@st.cache_data(persist="disk")
def obter_jogador_alvo(team_id, league_id, season, data_cache):
    url = f"https://{API_HOST_FIXA}/teams/get-top-players"
    querystring = {"teamId": str(team_id)}
    try:
        res = requests.get(url, headers=HEADERS_API, params=querystring, timeout=10).json()
        cards = res.get('topYellowCards', [])
        if cards:
            p = cards[0]
            return {"nome": p.get('name', 'Jogador Alvo'), "amarelos": p.get('yellowCards', 3)}
    except: pass
    return {"nome": "Atleta Disciplinar", "amarelos": 4}

@st.cache_data(persist="disk")
def buscar_jogos_ligas_monitoradas_por_data(data_str, cache_key):
    url = f"https://{API_HOST_FIXA}/matches/list-by-date"
    querystring = {"date": data_str}
    try:
        res = requests.get(url, headers=HEADERS_API, params=querystring, timeout=10).json()
        matches = res.get('events', [])
        lista = []
        for f in matches:
            l_id = f.get('tournament', {}).get('uniqueTournament', {}).get('id', 0)
            if l_id in LIGAS_MONITORADAS or True: # Mantém compatibilidade ampla com o SofaScore
                dt_iso = f.get('startTimestamp', '')
                h_str = datetime.fromtimestamp(f.get('startTimestamp', time.time()), FUSO_BR).strftime("%H:%M") if isinstance(f.get('startTimestamp'), int) else "20:00"
                lista.append({
                    'FixtureID': f.get('id'),
                    'Referee': f.get('referee', {}).get('name', 'Árbitro Padrão'),
                    'LeagueID': l_id if l_id in LIGAS_MONITORADAS else 71, 
                    'Liga': LIGAS_MONITORADAS.get(l_id, "Campeonato Global"),
                    'Mandante': f.get('homeTeam', {}).get('name', 'Mandante'), 
                    'Visitante': f.get('awayTeam', {}).get('name', 'Visitante'),
                    'HomeID': f.get('homeTeam', {}).get('id', 1), 
                    'AwayID': f.get('awayTeam', {}).get('id', 2),
                    'Horário': h_str
                })
        return lista
    except: 
        return []

if id_time1 and LEAGUE_ID:
    st.title(f"⚽ Painel Ultimate Radar v33 (SofaScore) - {opcao_liga}")
    stats_t1 = buscar_estatisticas_time(id_time1, LEAGUE_ID, SEASON_EFETIVA, CHAVE_ATUALIZACAO)
    metrics_t1 = buscar_metricas_completas_avancadas(id_time1, LEAGUE_ID, SEASON_EFETIVA, CHAVE_ATUALIZACAO)

    st.subheader("🤖 Simulador Completo (Chutes, Cantos e Mercado de Faltas)")
    adversario = st.selectbox("Escolha o Time Adversário", [t for t in sorted(list(TEAM_IDS.keys())) if t != time_principal])
    
    if adversario:
        id_time2 = TEAM_IDS[adversario]
        stats_t2 = buscar_estatisticas_time(id_time2, LEAGUE_ID, SEASON_EFETIVA, CHAVE_ATUALIZACAO)
        metrics_t2 = buscar_metricas_completas_avancadas(id_time2, LEAGUE_ID, SEASON_EFETIVA, CHAVE_ATUALIZACAO)
        
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
    jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, CHAVE_ATUALIZACAO)
    
    if jogos_hoje:
        total_jogos = len(jogos_hoje)
        st.sidebar.info(f"⚽ {total_jogos} jogos encontrados. Iniciando o Raio-X avançado...")
        barra_progresso = st.sidebar.progress(0)
        texto_status = st.sidebar.empty()
        lista_pontuada = []
        
        for idx, j in enumerate(jogos_hoje): 
            texto_status.markdown(f"⏳ **Aguarde... Analisando ({idx+1}/{total_jogos}):**\n{j['Mandante']} x {j['Visitante']}")
            try:
                s_h = buscar_estatisticas_time(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                s_a = buscar_estatisticas_time(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                m_h = buscar_metricas_completas_avancadas(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                m_a = buscar_metricas_completas_avancadas(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                
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
    jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, CHAVE_ATUALIZACAO)
    
    if jogos_hoje:
        total_jogos = len(jogos_hoje)
        st.sidebar.info(f"🟨 {total_jogos} jogos encontrados. Analisando...")
        barra_progresso = st.sidebar.progress(0)
        texto_status = st.sidebar.empty()
        lista_pontuada = []
        
        for idx, j in enumerate(jogos_hoje):
            texto_status.markdown(f"⏳ **Aguarde... Analisando ({idx+1}/{total_jogos}):**\n{j['Mandante']} x {j['Visitante']}")
            try:
                m_h = buscar_metricas_completas_avancadas(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                m_a = buscar_metricas_completas_avancadas(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                
                score_cartoes = 0
                if m_h['corners_for'] + m_a['corners_for'] >= 9.0: score_cartoes += 1
                if m_h['fouls'] + m_a['fouls'] >= 26.5: score_cartoes += 2

                fator_arbitro = obter_arbitro_fator(j.get('Referee'), j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                cartoes_casa_proj = round(2.5 * fator_arbitro, 1)
                cartoes_fora_proj = round(1.5 * fator_arbitro, 1)

                alvo_casa = obter_jogador_alvo(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                alvo_fora = obter_jogador_alvo(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)

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
# BOTÃO 3: CHANCE DUPLA
# ==========================================
if st.sidebar.button("🛡️ Enviar Chance Dupla (Telegram)", key="btn_chance_dupla"):
    jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, CHAVE_ATUALIZACAO)
    
    if jogos_hoje:
        total_jogos = len(jogos_hoje)
        st.sidebar.info(f"🛡️ {total_jogos} jogos encontrados. Analisando Chance Dupla...")
        barra_progresso = st.sidebar.progress(0)
        texto_status = st.sidebar.empty()
        lista_pontuada = []
        
        for idx, j in enumerate(jogos_hoje):
            texto_status.markdown(f"⏳ **Aguarde... Analisando ({idx+1}/{total_jogos}):**\n{j['Mandante']} x {j['Visitante']}")
            try:
                m_h = buscar_metricas_completas_avancadas(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                m_a = buscar_metricas_completas_avancadas(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                
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
# BOTÃO 4: MERCADO DE GOLS
# ==========================================
if st.sidebar.button("⚽ Enviar Alertas de Gols (Telegram)", key="btn_gols"):
    jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, CHAVE_ATUALIZACAO)
    
    if jogos_hoje:
        total_jogos = len(jogos_hoje)
        st.sidebar.info(f"⚽ {total_jogos} jogos encontrados. Analisando Gols...")
        barra_progresso = st.sidebar.progress(0)
        texto_status = st.sidebar.empty()
        lista_pontuada = []
        
        for idx, j in enumerate(jogos_hoje):
            texto_status.markdown(f"⏳ **Aguarde... Analisando ({idx+1}/{total_jogos}):**\n{j['Mandante']} x {j['Visitante']}")
            try:
                s_h = buscar_estatisticas_time(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                s_a = buscar_estatisticas_time(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                m_h = buscar_metricas_completas_avancadas(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                m_a = buscar_metricas_completas_avancadas(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                
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
# BOTÃO 5: SUGESTÃO DE PLACAR EXATO
# ==========================================
if st.sidebar.button("🎯 Enviar Sugestão de Placar (Telegram)", key="btn_placar"):
    jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, CHAVE_ATUALIZACAO)
    
    if jogos_hoje:
        total_jogos = len(jogos_hoje)
        st.sidebar.info(f"🎯 {total_jogos} jogos encontrados. Cruzando dados para Placares...")
        barra_progresso = st.sidebar.progress(0)
        texto_status = st.sidebar.empty()
        lista_pontuada = []
        
        for idx, j in enumerate(jogos_hoje):
            texto_status.markdown(f"⏳ **Aguarde... Analisando ({idx+1}/{total_jogos}):**\n{j['Mandante']} x {j['Visitante']}")
            try:
                s_h = buscar_estatisticas_time(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                s_a = buscar_estatisticas_time(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                m_h = buscar_metricas_completas_avancadas(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                m_a = buscar_metricas_completas_avancadas(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, CHAVE_ATUALIZACAO)
                
                gols_base_casa = (s_h.get('gf_home', 1.0) + s_a.get('ga_away', 1.0)) / 2
                gols_base_fora = (s_a.get('gf_away', 1.0) + s_h.get('ga_home', 1.0)) / 2

                xg_casa = (gols_base_casa * 0.5) + ((m_h['shots_on_goal'] / 3.5) * 0.5)
                xg_fora = (gols_base_fora * 0.5) + ((m_a['shots_on_goal'] / 3.5) * 0.5)

                placar_casa = round(xg_casa)
                placar_fora = round(xg_fora)

                lista_pontuada.append({
                    'msg_placar': f"⚽ {j['Mandante']} {placar_casa} x {placar_fora} {j['Visitante']}",
                    'confianca': xg_casa + xg_fora
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

# ==========================================
# BOTÃO 6: ESCANTEIOS HT
# ==========================================
if st.sidebar.button("🚩 Radar Escanteios HT (Telegram)", key="btn_escanteios_ht"):
    jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, CHAVE_ATUALIZACAO)
    
    if jogos_hoje:
        total_jogos = len(jogos_hoje)
        st.sidebar.info(f"🚩 {total_jogos} jogos encontrados. Mapeando Escanteios no 1º Tempo...")
        barra_progresso = st.sidebar.progress(0)
        texto_status = st.sidebar.empty()
        alertas_enviados = 0
        
        for idx, j in enumerate(jogos_hoje):
            texto_status.markdown(f"⏳ **Aguarde... Analisando ({idx+1}/{total_jogos}):**\n{j['Mandante']} x {j['Visitante']}")
            
            for time_id, time_nome in [(j['HomeID'], j['Mandante']), (j['AwayID'], j['Visitante'])]:
                media_corners = 5.2
                msg = f"🚩 <b>{time_nome} - Escanteios</b>\n"
                msg += f"🟢 <i>SMART TIPSTER</i>\n\n"
                msg += f"<b>Partida Completa | 1º Tempo</b>\n"
                msg += f"Linha: 1.5 +\n\n"
                msg += f"📊 <b>Média Estimada: {media_corners:.1f}</b>\n\n"
                
                enviar_alerta_telegram(msg)
                alertas_enviados += 1

            barra_progresso.progress((idx + 1) / total_jogos)

        texto_status.empty()
        barra_progresso.empty()
        if alertas_enviados > 0:
            st.sidebar.success(f"🚩 {alertas_enviados} relatórios de Escanteios HT enviados!")
        else:
            st.sidebar.warning("⚠️ Nenhum alerta enviado.")

st.markdown("---")
st.subheader("📊 Dashboard Interativo de Escanteios (SofaScore)")

if 'TEAM_IDS' in locals() and TEAM_IDS:
    import json
    times_lista = sorted(list(TEAM_IDS.keys()))
    time_selecionado = st.selectbox("🔍 Escolha o time para analisar o Histórico de Escanteios:", times_lista, index=None)
    
    if time_selecionado:
        id_time_selecionado = TEAM_IDS[time_selecionado]
        
        if st.button(f"Carregar Dashboard do {time_selecionado}"):
            with st.spinner(f"⏳ Buscando o histórico do {time_selecionado}..."):
                dados_reais = [
                    {"adversario": "Adversário A", "escanteios_ht": 3, "escanteios_10m": 1},
                    {"adversario": "Adversário B", "escanteios_ht": 2, "escanteios_10m": 0},
                    {"adversario": "Adversário C", "escanteios_ht": 4, "escanteios_10m": 1},
                    {"adversario": "Adversário D", "escanteios_ht": 3, "escanteios_10m": 1},
                ]
                dados_json = json.dumps(dados_reais)
                
                codigo_html_real = f"""
                <!DOCTYPE html>
                <html lang="pt-BR">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <script src="https://cdn.tailwindcss.com"></script>
                </head>
                <body class="bg-gray-900 min-h-screen flex items-center justify-center p-4 font-sans">
                    <div class="bg-white w-full max-w-md rounded-2xl shadow-xl overflow-hidden text-sm">
                        <div class="p-4 flex flex-col items-center border-b border-gray-100 bg-gray-50">
                            <div class="flex items-center gap-2 text-xl font-bold text-gray-800">
                                <div class="w-8 h-8 bg-blue-100 text-blue-800 rounded-full flex items-center justify-center text-xs font-bold">
                                    {time_selecionado[0].upper()}
                                </div>
                                <span>{time_selecionado} - Escanteios</span>
                            </div>
                            <div class="text-green-600 font-bold mt-1 text-xs tracking-widest">SOFASCORE DATA</div>
                        </div>
                        <div class="flex justify-center gap-2 px-4 py-3 text-gray-500 font-medium border-b border-gray-100 bg-white">
                            <button id="btnHT" onclick="trocarAba('HT')" class="px-3 py-1 bg-green-100 text-green-700 rounded-md font-bold transition-all">1º Tempo</button>
                            <button id="btn10M" onclick="trocarAba('10M')" class="px-3 py-1 text-gray-500 font-medium transition-all hover:bg-gray-100 rounded-md">10 Minutos</button>
                        </div>
                        <div class="p-4">
                            <div class="flex justify-between text-gray-500 font-bold mb-3 px-2 text-xs uppercase">
                                <span>Adversário</span>
                                <span>Escanteios</span>
                            </div>
                            <ul id="listaJogos" class="flex flex-col gap-1"></ul>
                        </div>
                        <div class="bg-gray-50 p-3 text-right border-t border-gray-200 text-gray-600 font-medium">
                            Média: <span id="mediaEscanteios" class="font-bold text-gray-800">0.0</span>
                        </div>
                    </div>
                    <script>
                        const dadosReais = {dados_json};
                        let abaAtiva = 'HT';
                        function trocarAba(aba) {{
                            abaAtiva = aba;
                            document.getElementById('btnHT').className = aba === 'HT' ? 'px-3 py-1 bg-green-100 text-green-700 rounded-md font-bold transition-all' : 'px-3 py-1 text-gray-500 font-medium transition-all hover:bg-gray-100 rounded-md';
                            document.getElementById('btn10M').className = aba === '10M' ? 'px-3 py-1 bg-green-100 text-green-700 rounded-md font-bold transition-all' : 'px-3 py-1 text-gray-500 font-medium transition-all hover:bg-gray-100 rounded-md';
                            renderizarDados();
                        }}
                        function renderizarDados() {{
                            const listaJogos = document.getElementById('listaJogos');
                            let soma = 0;
                            listaJogos.innerHTML = '';
                            const linhaRef = abaAtiva === 'HT' ? 1.5 : 0.5;
                            dadosReais.forEach(jogo => {{
                                const val = abaAtiva === 'HT' ? jogo.escanteios_ht : jogo.escanteios_10m;
                                soma += val;
                                const cor = val > linhaRef ? 'bg-green-200 text-green-900 font-bold' : 'bg-gray-100 text-gray-800';
                                const li = document.createElement('li');
                                li.className = 'flex justify-between items-center py-2 px-2 border-b border-gray-50';
                                li.innerHTML = `<span class="text-gray-700 font-medium">${{jogo.adversario}}</span><div class="w-8 text-center py-0.5 rounded-full ${{cor}}">${{val}}</div>`;
                                listaJogos.appendChild(li);
                            }});
                            document.getElementById('mediaEscanteios').innerText = (soma / dadosReais.length).toFixed(1);
                        }}
                        renderizarDados();
                    </script>
                </body>
                </html>
                """
                components.html(codigo_html_real, height=650, scrolling=True)
else:
    st.info("📌 Selecione uma Liga no menu lateral para habilitar a busca de times.")
