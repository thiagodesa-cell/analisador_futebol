import json
import math
import time
from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
import streamlit as st

# ==========================================
# CONFIGURAÇÕES INICIAIS DA PÁGINA
# ==========================================
st.set_page_config(page_title="Painel Pro - Tipster Ultimate Radar v33", layout="wide")

FUSO_BR = timezone(timedelta(hours=-3))
API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"
SEASON = datetime.now(FUSO_BR).year
TELEGRAM_TOKEN = "8281259090:AAEggXJKpCMxRbhhrcCZymcmNUKWNoOPFfY"
TELEGRAM_CHAT_ID = "-1004464226419"
RAPIDAPI_SOFASCORE_KEY = API_KEY_FIXA

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
    11: "Copa Sudamericana",
}

def obter_chave_atualizacao():
    return datetime.now(FUSO_BR).strftime("%Y-%m-%d_%H")

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v33_anti_travamento"
DATA_HOJE_STR = datetime.now(FUSO_BR).strftime("%Y-%m-%d")

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def converter_para_horario_brasilia(iso_string):
    try:
        dt_utc = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        dt_local = dt_utc.astimezone(FUSO_BR)
        return dt_local.strftime("%Y-%m-%d"), dt_local.strftime("%d/%m/%Y"), dt_local.strftime("%H:%M")
    except Exception:
        return iso_string[:10], f"{iso_string[8:10]}/{iso_string[5:7]}/{iso_string[0:4]}", iso_string[11:16]

def converter_fracao_para_decimal(frac_str):
    try:
        if not frac_str or "/" not in str(frac_str):
            return float(frac_str) if frac_str else "N/A"
        num, den = str(frac_str).split("/")
        valor_decimal = (float(num) / float(den)) + 1.0
        return f"{valor_decimal:.2f}"
    except Exception:
        return "N/A"

def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    return requests.post(
        url, json={"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
    ).status_code == 200

# ==========================================
# FUNÇÕES DA API (SOFASCORE E API-SPORTS)
# ==========================================
@st.cache_data(ttl=300)
def buscar_odds_sofascore(match_id):
    url = "https://sofascore.p.rapidapi.com/matches/got-all-odds"
    headers = {
        "x-rapidapi-key": RAPIDAPI_SOFASCORE_KEY,
        "x-rapidapi-host": "sofascore.p.rapidapi.com",
    }
    params = {"matchId": match_id}
    odds = {"1": "N/D", "X": "N/D", "2": "N/D", "over25": "N/D", "under25": "N/D", "btts_sim": "N/D", "btts_nao": "N/D"}

    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        if res.status_code == 200:
            dados = res.json()
            for m in dados.get("markets", []):
                name, group = m.get("marketName"), m.get("choiceGroup")
                choices = m.get("choices", [])
                
                if name == "Full time":
                    for c in choices:
                        val = converter_fracao_para_decimal(c.get("fractionalValue"))
                        if c.get("name") == "1": odds["1"] = val
                        elif c.get("name") == "X": odds["X"] = val
                        elif c.get("name") == "2": odds["2"] = val
                elif name == "Match goals" and group == "2.5":
                    for c in choices:
                        val = converter_fracao_para_decimal(c.get("fractionalValue"))
                        if c.get("name") == "Over": odds["over25"] = val
                        elif c.get("name") == "Under": odds["under25"] = val
                elif name == "Both teams to score":
                    for c in choices:
                        val = converter_fracao_para_decimal(c.get("fractionalValue"))
                        if c.get("name") == "Yes": odds["btts_sim"] = val
                        elif c.get("name") == "No": odds["btts_nao"] = val
    except Exception:
        pass
    return odds

@st.cache_data(persist="disk")
def descobrir_temporada_valida(league_id, season_atual, key, data_cache):
    for s in [season_atual, season_atual - 1, season_atual - 2]:
        url = f"https://v3.football.api-sports.io/teams?league={league_id}&season={s}"
        try:
            res = requests.get(url, headers={"x-rapidapi-host": "v3.football.api-sports.io", "x-rapidapi-key": key})
            if res.json().get("results", 0) > 0: return s
        except: pass
    return season_atual

@st.cache_data(persist="disk")
def buscar_times_por_liga(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/teams?league={league_id}&season={season}"
    try:
        data = requests.get(url, headers={"x-rapidapi-host": "v3.football.api-sports.io", "x-rapidapi-key": key}).json()
        return {item["team"]["name"]: item["team"]["id"] for item in data.get("response", [])} if data.get("results", 0) > 0 else {}
    except:
        return {}

@st.cache_data(persist="disk")
def buscar_estatisticas_time(team_id, league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/teams/statistics?league={league_id}&season={season}&team={team_id}"
    try:
        stats = requests.get(url, headers={"x-rapidapi-host": "v3.football.api-sports.io", "x-rapidapi-key": key}).json()["response"]
        gf = stats.get("goals", {}).get("for", {}).get("average", {})
        ga = stats.get("goals", {}).get("against", {}).get("average", {})
        return {
            "gf_home": float(gf.get("home") or 1.2), "ga_home": float(ga.get("home") or 1.1),
            "gf_away": float(gf.get("away") or 1.0), "ga_away": float(ga.get("away") or 1.3),
        }
    except:
        return {"gf_home": 1.2, "ga_home": 1.1, "gf_away": 1.0, "ga_away": 1.3}

@st.cache_data(persist="disk")
def buscar_metricas_completas_avancadas(team_id, league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&team={team_id}&last=12"
    headers = {"x-rapidapi-host": "v3.football.api-sports.io", "x-rapidapi-key": key}
    c_pro, c_contra, s_tot, s_gol, faltas_lista = [], [], [], [], []

    try:
        data = requests.get(url, headers=headers, timeout=10).json()
        for f in data.get("response", []):
            f_id = f["fixture"]["id"]
            time.sleep(0.1)
            data_s = requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={f_id}", headers=headers, timeout=10).json()
            
            t_c = o_c = t_st = t_sg = t_f = 0
            for item in data_s.get("response", []):
                for s in item["statistics"]:
                    val = s["value"]
                    if val is not None:
                        if s["type"] == "Corner Kicks":
                            if item["team"]["id"] == team_id: t_c = int(val)
                            else: o_c = int(val)
                        elif s["type"] == "Total Shots":
                            if item["team"]["id"] == team_id: t_st = int(val)
                        elif s["type"] == "Shots on Goal":
                            if item["team"]["id"] == team_id: t_sg = int(val)
                        elif s["type"] == "Fouls":
                            if item["team"]["id"] == team_id: t_f = int(val)

            c_pro.append(t_c); c_contra.append(o_c)
            if t_st > 0: s_tot.append(t_st)
            if t_sg > 0: s_gol.append(t_sg)
            if t_f > 0: faltas_lista.append(t_f)

        div = max(len(c_pro), 1)
        return {
            "corners_for": sum(c_pro) / div, "corners_ag": sum(c_contra) / div,
            "shots_total": sum(s_tot) / max(len(s_tot), 1),
            "shots_on_goal": sum(s_gol) / max(len(s_gol), 1),
            "fouls": sum(faltas_lista) / max(len(faltas_lista), 1),
        }
    except:
        return {"corners_for": 4.5, "corners_ag": 4.5, "shots_total": 12.0, "shots_on_goal": 4.2, "fouls": 13.5}

@st.cache_data(persist="disk")
def buscar_jogos_ligas_monitoradas_por_data(data_str, key, cache_key):
    url = f"https://v3.football.api-sports.io/fixtures?date={data_str}"
    try:
        data = requests.get(url, headers={"x-rapidapi-host": "v3.football.api-sports.io", "x-rapidapi-key": key}).json()
        return [
            {
                "FixtureID": f["fixture"]["id"],
                "LeagueID": f["league"]["id"],
                "Liga": LIGAS_MONITORADAS[f["league"]["id"]],
                "Mandante": f["teams"]["home"]["name"],
                "Visitante": f["teams"]["away"]["name"],
                "HomeID": f["teams"]["home"]["id"],
                "AwayID": f["teams"]["away"]["id"],
                "Horário": converter_para_horario_brasilia(f["fixture"]["date"])[2],
            }
            for f in data.get("response", [])
            if f["league"]["id"] in LIGAS_MONITORADAS and f["fixture"]["status"]["short"] in ["NS", "TBD"]
        ]
    except: return []

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
st.sidebar.header("🏆 Seleção da Competição Global")
opcao_liga = st.sidebar.radio("Escolha qual campeonato deseja analisar:", list(LIGAS_MONITORADAS.values()), index=None)
LEAGUE_ID = ([k for k, v in LIGAS_MONITORADAS.items() if v == opcao_liga][0] if opcao_liga else None)
SEASON_EFETIVA = descobrir_temporada_valida(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO) if LEAGUE_ID else (SEASON - 1)
TEAM_IDS = buscar_times_por_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO) if LEAGUE_ID else {}

if id_time1 := TEAM_IDS.get(st.sidebar.selectbox("Escolha o Time (Mandante)", sorted(list(TEAM_IDS.keys())) if TEAM_IDS else [], index=None)):
    st.title(f"⚽ Painel Ultimate Radar v33 - {opcao_liga}")
    adversario = st.selectbox("Escolha o Time Adversário", [t for t in sorted(list(TEAM_IDS.keys())) if TEAM_IDS[t] != id_time1])

    if adversario:
        id_time2 = TEAM_IDS[adversario]
        stats_t1 = buscar_estatisticas_time(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        stats_t2 = buscar_estatisticas_time(id_time2, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        m_t1 = buscar_metricas_completas_avancadas(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        m_t2 = buscar_metricas_completas_avancadas(id_time2, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🎯 Projeção de Finalizações")
            st.markdown(f"- *Chutes Totais HT (1º T):* **{(m_t1['shots_total'] * 0.45):.1f}**")
            st.markdown(f"- *Expectativa de Gols:* **{((stats_t1['gf_home'] + stats_t2['ga_away'])/2 + (stats_t2['gf_away'] + stats_t1['ga_home'])/2):.2f}**")
        with col2:
            st.markdown("#### 🚩 Cantos & Faltas")
            st.markdown(f"- *Projeção de Escanteios:* **{(m_t1['corners_for'] + m_t2['corners_for']):.1f}**")
            st.markdown(f"- *Média de Faltas:* **{(m_t1['fouls'] + m_t2['fouls']):.1f}**")

st.sidebar.markdown("---")

# ==========================================
# BOTÕES DE ALERTAS
# ==========================================
jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, API_KEY_FIXA, CHAVE_ATUALIZACAO)

if st.sidebar.button("💎 1. Enviar Raio-X Completo", key="btn_rx"):
    if jogos_hoje:
        msg = f"💎 <b>SMART TIPSTER: RAIO-X COMPLETO DO DIA</b> 💎\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
        for j in jogos_hoje[:5]:
            m_h = buscar_metricas_completas_avancadas(j["HomeID"], j["LeagueID"], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            m_a = buscar_metricas_completas_avancadas(j["AwayID"], j["LeagueID"], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            msg += f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b> [{j['Horário']}]\n"
            msg += f"   🚩 Escanteios: ~{(m_h['corners_for'] + m_a['corners_for']):.1f} cantos\n"
            msg += f"   🎯 Chutes no Alvo: ~{(m_h['shots_on_goal'] + m_a['shots_on_goal']):.1f} no gol\n\n"
        enviar_alerta_telegram(msg)
        st.sidebar.success("🔥 Raio-X enviado!")
    else: st.sidebar.warning("Nenhum jogo encontrado.")

if st.sidebar.button("🟨 2. Enviar Top Cantos e Cartões", key="btn_cantos"):
    if jogos_hoje:
        msg = f"🟨 <b>SMART TIPSTER: CANTOS E CARTÕES</b> 🟥\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
        for j in jogos_hoje[:5]:
            m_h = buscar_metricas_completas_avancadas(j["HomeID"], j["LeagueID"], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            m_a = buscar_metricas_completas_avancadas(j["AwayID"], j["LeagueID"], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            total_cantos = m_h['corners_for'] + m_a['corners_for']
            sugestao = "Over 9.5 Cantos" if total_cantos >= 9.5 else "Under 10.5 Cantos"
            msg += f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b> [{j['Horário']}]\n"
            msg += f"   🚩 Projeção: {total_cantos:.1f} cantos ({sugestao})\n\n"
        enviar_alerta_telegram(msg)
        st.sidebar.success("🟨 Relatório enviado!")
    else: st.sidebar.warning("Nenhum jogo encontrado.")

if st.sidebar.button("🛡️ 3. Enviar Chance Dupla", key="btn_dupla"):
    if jogos_hoje:
        msg = f"🛡️ <b>CHANCE DUPLA - ANÁLISE AUTOMÁTICA</b>\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
        for j in jogos_hoje[:5]:
            s_h = buscar_estatisticas_time(j["HomeID"], j["LeagueID"], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            s_a = buscar_estatisticas_time(j["AwayID"], j["LeagueID"], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            forca_casa = s_h["gf_home"] - s_h["ga_home"]
            forca_fora = s_a["gf_away"] - s_a["ga_away"]
            dupla = "1X (Casa ou Empate)" if forca_casa >= forca_fora else "X2 (Empate ou Visitante)"
            msg += f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b>\n   🎯 <b>Sugestão:</b> {dupla}\n\n"
        enviar_alerta_telegram(msg)
        st.sidebar.success("🛡️ Alertas enviados!")

if st.sidebar.button("⚽ 4. Enviar Alertas de Gols", key="btn_gols"):
    if jogos_hoje:
        msg = f"⚽ <b>PROJEÇÃO DE GOLS - ANÁLISE AUTOMÁTICA</b>\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
        for j in jogos_hoje[:5]:
            s_h = buscar_estatisticas_time(j["HomeID"], j["LeagueID"], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            s_a = buscar_estatisticas_time(j["AwayID"], j["LeagueID"], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            media_gols = ((s_h["gf_home"] + s_a["ga_away"]) / 2) + ((s_a["gf_away"] + s_h["ga_home"]) / 2)
            sugestao_gols = "Over 2.5 & Ambas Marcam" if media_gols >= 2.5 else ("Over 1.5 Gols" if media_gols >= 1.8 else "Under 2.5 Gols")
            msg += f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b>\n   🎯 <b>Sugestão:</b> {sugestao_gols} (Exp: {media_gols:.2f})\n\n"
        enviar_alerta_telegram(msg)
        st.sidebar.success("⚽ Alertas enviados!")

if st.sidebar.button("🎯 5. Enviar Sugestão de Placar", key="btn_placar"):
    if jogos_hoje:
        msg = f"🎯 <b>SUGESTÃO DE PLACAR EXATO</b>\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
        for j in jogos_hoje[:5]:
            s_h = buscar_estatisticas_time(j["HomeID"], j["LeagueID"], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            s_a = buscar_estatisticas_time(j["AwayID"], j["LeagueID"], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            gols_h = max(0, round((s_h["gf_home"] + s_a["ga_away"]) / 2))
            gols_a = max(0, round((s_a["gf_away"] + s_h["ga_home"]) / 2))
            msg += f"⚽ <b>{j['Mandante']} {gols_h} x {gols_a} {j['Visitante']}</b>\n\n"
        enviar_alerta_telegram(msg)
        st.sidebar.success("🎯 Placares enviados!")

# ==========================================
# DASHBOARD INTERATIVO DE ESCANTEIOS (SEPARADO: 10 MIN E HT)
# ==========================================
st.markdown("---")
st.subheader("📊 Dashboard Interativo de Escanteios (Primeiros 10 min e Primeiro Tempo)")

if TEAM_IDS:
    time_selecionado = st.selectbox("🔍 Escolha o time para analisar o Histórico Detalhado de Cantos:", sorted(list(TEAM_IDS.keys())), index=None)
    if time_selecionado:
        id_time_selecionado = TEAM_IDS[time_selecionado]
        if st.button(f"Carregar Dashboard do {time_selecionado}"):
            with st.spinner("⏳ Analisando os minutos dos escanteios na API..."):
                url_fixtures = f"https://v3.football.api-sports.io/fixtures?team={id_time_selecionado}&season={SEASON_EFETIVA}&last=10"
                headers = {"x-rapidapi-host": "v3.football.api-sports.io", "x-rapidapi-key": API_KEY_FIXA}
                dados_reais = []
                try:
                    res_fix = requests.get(url_fixtures, headers=headers, timeout=10).json()
                    for f in res_fix.get("response", []):
                        f_id = f["fixture"]["id"]
                        is_home = f["teams"]["home"]["id"] == id_time_selecionado
                        adv_name = f["teams"]["away"]["name"] if is_home else f["teams"]["home"]["name"]
                        
                        time.sleep(0.1)
                        res_ev = requests.get(f"https://v3.football.api-sports.io/fixtures/events?fixture={f_id}", headers=headers, timeout=10).json()
                        
                        cantos_10m = 0
                        cantos_ht = 0
                        
                        for ev in res_ev.get("response", []):
                            if ev.get("type") == "Corner" and ev.get("team", {}).get("id") == id_time_selecionado:
                                minuto = int(ev.get("time", {}).get("elapsed", 0))
                                if minuto <= 10:
                                    cantos_10m += 1
                                if minuto <= 45:
                                    cantos_ht += 1
                        
                        dados_reais.append({
                            "Adversário": f"Vs {adv_name}",
                            "Até 10 min": cantos_10m,
                            "Primeiro Tempo (HT)": cantos_ht
                        })
                except:
                    st.error("⚠️ Erro ao buscar eventos na API.")
                
                if dados_reais:
                    df_cantos = pd.DataFrame(dados_reais)
                    st.markdown(f"### 📌 {time_selecionado} - Histórico de Cantos")
                    st.dataframe(df_cantos, use_container_width=True, hide_index=True)
                else:
                    st.warning("Nenhum dado encontrado para este time.")
