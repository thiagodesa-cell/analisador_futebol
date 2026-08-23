import json
import math
import time
from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

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

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v33_html"
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

def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    return requests.post(
        url, json={"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
    ).status_code == 200

# ==========================================
# FUNÇÕES DA API
# ==========================================
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
# DASHBOARD INTERATIVO EM HTML (10 MIN E HT SEPARADOS)
# ==========================================
st.markdown("---")
st.subheader("📊 Dashboard Interativo de Escanteios (HTML Personalizado)")

if TEAM_IDS:
    time_selecionado = st.selectbox("🔍 Escolha o time para gerar o Relatório HTML:", sorted(list(TEAM_IDS.keys()), key=str), index=None, key="select_html_time")
    if time_selecionado:
        id_time_selecionado = TEAM_IDS[time_selecionado]
        if st.button(f"Gerar Relatório HTML do {time_selecionado}"):
            with st.spinner("⏳ Extraindo eventos detalhados por minuto da API..."):
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
                            tipo_evento = ev.get("type")
                            team_obj = ev.get("team", {})
                            if tipo_evento and tipo_evento.lower() == "goal" and "corner" in str(ev.get("detail", "")).lower():
                                pass # Garantir apenas corners puros
                            
                            if (tipo_evento == "Corner" or tipo_evento == "corner") and team_obj.get("id") == id_time_selecionado:
                                time_info = ev.get("time", {})
                                minuto = int(time_info.get("elapsed", 0))
                                extra = int(time_info.get("extra", 0) or 0)
                                tempo_total = minuto + extra
                                
                                if tempo_total <= 10:
                                    cantos_10m += 1
                                if tempo_total <= 45:
                                    cantos_ht += 1
                        
                        dados_reais.append({
                            "adversario": adv_name, 
                            "cantos_10m": cantos_10m, 
                            "cantos_ht": cantos_ht
                        })
                except Exception as e:
                    st.error(f"⚠️ Erro ao processar requisição: {e}")

                linhas_tabela = ""
                if dados_reais:
                    for d in dados_reais:
                        linhas_tabela += f"""
                        <tr class="border-b border-gray-700 hover:bg-gray-800 transition-colors">
                            <td class="py-3 px-4 text-left font-medium text-gray-200">Vs {d['adversario']}</td>
                            <td class="py-3 px-4 text-center font-bold text-amber-400 text-base">{d['cantos_10m']}</td>
                            <td class="py-3 px-4 text-center font-bold text-blue-400 text-base">{d['cantos_ht']}</td>
                        </tr>
                        """
                else:
                    linhas_tabela = "<tr><td colspan='3' class='py-4 text-center text-gray-400'>Nenhum dado encontrado.</td></tr>"

                codigo_html = f"""
                <!DOCTYPE html>
                <html lang="pt-BR">
                <head>
                    <meta charset="UTF-8">
                    <script src="https://cdn.tailwindcss.com"></script>
                </head>
                <body class="bg-gray-950 flex justify-center p-4">
                    <div class="bg-gray-900 border border-gray-800 w-full max-w-xl rounded-2xl p-6 shadow-2xl text-center">
                        <div class="text-xl font-black mb-1 text-white tracking-wide">{time_selecionado}</div>
                        <div class="text-xs text-gray-400 uppercase tracking-wider mb-5">Histórico Analítico de Escanteios</div>
                        <div class="overflow-x-auto">
                            <table class="w-full text-sm text-gray-300">
                                <thead>
                                    <tr class="bg-gray-800 text-gray-300 uppercase text-xs tracking-wider border-b border-gray-700">
                                        <th class="py-3 px-4 text-left">Adversário</th>
                                        <th class="py-3 px-4 text-center">Até 10 Minutos</th>
                                        <th class="py-3 px-4 text-center">Primeiro Tempo (HT)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {linhas_tabela}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </body>
                </html>
                """
                components.html(codigo_html, height=450, scrolling=True)
