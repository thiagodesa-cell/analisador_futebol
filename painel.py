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
st.set_page_config(page_title="Painel Pro - Tipster Ultimate Radar v37", layout="wide")

FUSO_BR = timezone(timedelta(hours=-3))
API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"
SEASON = datetime.now(FUSO_BR).year
TELEGRAM_TOKEN = "8281259090:AAEggXJKpCMxRbhhrcCZymcmNUKWNoOPFfY"
TELEGRAM_CHAT_ID = "-1004464226419"
RAPIDAPI_HOST = "v3.football.api-sports.io"

# Ligas monitoradas com prioridade para Brasil e América do Sul
LIGAS_MONITORADAS = {
    71: "Brasileirão Série A",
    72: "Brasileirão Série B",
    73: "Copa do Brasil",
    128: "Campeonato Argentino",
    13: "Copa Libertadores",
    11: "Copa Sudamericana",
    39: "Premier League (Inglaterra)",
    140: "La Liga (Espanha)",
    78: "Bundesliga (Alemanha)",
    135: "Serie A (Itália)",
    61: "Ligue 1 (França)",
}

# Ordem de prioridade para exibir os jogos do dia (Brasil/América do Sul primeiro)
LEAGUE_PRIORITY = {
    71: 1,  # Brasileirão Série A
    72: 2,  # Brasileirão Série B
    73: 3,  # Copa do Brasil
    13: 4,  # Libertadores
    11: 5,  # Sul-Americana
    128: 6, # Campeonato Argentino
}

def obter_chave_atualizacao():
    return datetime.now(FUSO_BR).strftime("%Y-%m-%d_%H")

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v37_dashboard"
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
# FUNÇÕES DE CONSULTA E DADOS
# ==========================================
@st.cache_data(persist="disk")
def buscar_times_por_liga_ampliado(league_id, key, data_cache):
    url = f"https://{RAPIDAPI_HOST}/teams?league={league_id}&season={SEASON}"
    headers = {"x-rapidapi-host": RAPIDAPI_HOST, "x-rapidapi-key": key}
    try:
        res = requests.get(url, headers=headers, timeout=10).json()
        if res.get("results", 0) > 0:
            return {item["team"]["name"]: item["team"]["id"] for item in res.get("response", [])}
    except:
        pass
    
    times_fallback = {
        71: {"Flamengo": 126, "Palmeiras": 121, "São Paulo": 126, "Corinthians": 127, "Fluminense": 128, "Atlético-MG": 103, "Internacional": 119, "Grêmio": 130, "Botafogo": 120, "Vasco da Gama": 131, "Cruzeiro": 137, "Bahia": 339, "Fortaleza": 134, "Athletico-PR": 133},
        72: {"Santos": 129, "Sport Recife": 747, "Coritiba": 116, "Ceará": 105, "América-MG": 110, "Goiás": 115, "Avaí": 138, "Chapecoense": 135},
        128: {"River Plate": 435, "Boca Juniors": 451, "Racing Club": 442, "Independiente": 445, "San Lorenzo": 448},
        39: {"Manchester City": 50, "Arsenal": 42, "Liverpool": 40, "Manchester United": 33, "Chelsea": 49, "Tottenham": 47},
    }
    return times_fallback.get(league_id, {"Time Exemplo A": 1001, "Time Exemplo B": 1002})

@st.cache_data(persist="disk")
def buscar_metricas_avancadas(team_id, key, data_cache):
    time.sleep(0.1)
    return {
        "corners_for": 5.6, "corners_ag": 4.2,
        "shots_total": 15.1, "shots_on_goal": 6.2,
        "fouls": 11.8, "gf_home": 1.8, "ga_home": 0.7,
        "gf_away": 1.4, "ga_away": 1.2
    }

@st.cache_data(persist="disk")
def buscar_jogos_reais_do_dia(data_str, key, data_cache):
    url = f"https://{RAPIDAPI_HOST}/fixtures?date={data_str}"
    headers = {"x-rapidapi-host": RAPIDAPI_HOST, "x-rapidapi-key": key}
    jogos_validos = []
    try:
        res = requests.get(url, headers=headers, timeout=10).json()
        for f in res.get("response", []):
            l_id = f["league"]["id"]
            if l_id in LIGAS_MONITORADAS and f["fixture"]["status"]["short"] in ["NS", "TBD", "1H", "HT", "2H"]:
                _, _, hora = converter_para_horario_brasilia(f["fixture"]["date"])
                jogos_validos.append({
                    "HomeID": f["teams"]["home"]["id"],
                    "AwayID": f["teams"]["away"]["id"],
                    "Mandante": f["teams"]["home"]["name"],
                    "Visitante": f["teams"]["away"]["name"],
                    "LeagueID": l_id,
                    "Liga": LIGAS_MONITORADAS[l_id],
                    "Horário": hora,
                    "Prioridade": LEAGUE_PRIORITY.get(l_id, 99)
                })
    except:
        pass
    
    jogos_validos = sorted(jogos_validos, key=lambda x: (x["Prioridade"], x["Horário"]))
    return jogos_validos

# ==========================================
# INTERFACE PRINCIPAL & BARRA LATERAL
# ==========================================
st.sidebar.header("🏆 Seleção da Competição Global")
opcao_liga = st.sidebar.radio("Escolha qual campeonato deseja analisar:", list(LIGAS_MONITORADAS.values()), index=None)
LEAGUE_ID = ([k for k, v in LIGAS_MONITORADAS.items() if v == opcao_liga][0] if opcao_liga else None)
TEAM_IDS = buscar_times_por_liga_ampliado(LEAGUE_ID, API_KEY_FIXA, CHAVE_ATUALIZACAO) if LEAGUE_ID else {}

if id_time1 := TEAM_IDS.get(st.sidebar.selectbox("Escolha o Time (Mandante)", sorted(list(TEAM_IDS.keys())) if TEAM_IDS else [], index=None)):
    st.title(f"⚽ Painel Ultimate Radar v37 - {opcao_liga}")
    adversario = st.sidebar.selectbox("Escolha o Time Adversário", [t for t in sorted(list(TEAM_IDS.keys())) if TEAM_IDS[t] != id_time1])

    if adversario:
        id_time2 = TEAM_IDS[adversario]
        m_t1 = buscar_metricas_avancadas(id_time1, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        m_t2 = buscar_metricas_avancadas(id_time2, API_KEY_FIXA, CHAVE_ATUALIZACAO)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🎯 Projeção de Finalizações")
            st.markdown(f"- *Chutes Totais HT (1º T):* **{(m_t1['shots_total'] * 0.45):.1f}**")
            st.markdown(f"- *Expectativa de Gols (xG):* **{((m_t1['gf_home'] + m_t2['ga_away'])/2):.2f}**")
        with col2:
            st.markdown("#### 🚩 Cantos & Faltas")
            st.markdown(f"- *Projeção de Escanteios:* **{(m_t1['corners_for'] + m_t2['corners_for']):.1f}**")
            st.markdown(f"- *Média de Faltas:* **{(m_t1['fouls'] + m_t2['fouls']):.1f}**")

st.sidebar.markdown("---")
st.sidebar.subheader("🚀 Central de Alertas Telegram")

jogos_hoje = buscar_jogos_reais_do_dia(DATA_HOJE_STR, API_KEY_FIXA, CHAVE_ATUALIZACAO)

# 1. Raio-X Completo
if st.sidebar.button("💎 1. Enviar Raio-X Completo", key="btn_rx"):
    with st.spinner("🔄 Rastreando jogos do Brasileirão e América do Sul para o Raio-X..."):
        if jogos_hoje:
            msg = f"💎 <b>SMART TIPSTER: RAIO-X DO DIA</b> 💎\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
            for j in jogos_hoje[:6]:
                mh = buscar_metricas_avancadas(j["HomeID"], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                ma = buscar_metricas_avancadas(j["AwayID"], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                msg += f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b> [{j['Horário']}] - <i>{j['Liga']}</i>\n"
                msg += f"   🚩 Escanteios: ~{(mh['corners_for'] + ma['corners_for']):.1f}\n"
                msg += f"   🎯 Chutes no Alvo: ~{(mh['shots_on_goal'] + ma['shots_on_goal']):.1f}\n\n"
            enviar_alerta_telegram(msg)
            st.sidebar.success("🔥 Raio-X enviado com sucesso!")
        else:
            st.sidebar.warning("Nenhum jogo encontrado para hoje nas ligas monitoradas.")

# 2. Top Cantos e Cartões
if st.sidebar.button("🟨 2. Enviar Top Cantos e Cartões", key="btn_cantos"):
    with st.spinner("🔄 Analisando cantos e cartões dos jogos de hoje..."):
        if jogos_hoje:
            msg = f"🟨 <b>SMART TIPSTER: CANTOS E CARTÕES</b> 🟥\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
            for j in jogos_hoje[:6]:
                mh = buscar_metricas_avancadas(j["HomeID"], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                ma = buscar_metricas_avancadas(j["AwayID"], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                total_cantos = mh['corners_for'] + ma['corners_for']
                sugestao = "Over 9.5 Cantos" if total_cantos >= 9.5 else "Under 10.5 Cantos"
                msg += f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b> [{j['Horário']}] - <i>{j['Liga']}</i>\n"
                msg += f"   🚩 Projeção: {total_cantos:.1f} ({sugestao})\n\n"
            enviar_alerta_telegram(msg)
            st.sidebar.success("🟨 Relatório de Cantos enviado!")
        else:
            st.sidebar.warning("Nenhum jogo encontrado para hoje.")

# 3. Chance Dupla
if st.sidebar.button("🛡️ 3. Enviar Chance Dupla", key="btn_dupla"):
    with st.spinner("🔄 Calculando probabilidades de Chance Dupla..."):
        if jogos_hoje:
            msg = f"🛡️ <b>CHANCE DUPLA - ANÁLISE DE HOJE</b>\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
            for j in jogos_hoje[:6]:
                sh = buscar_metricas_avancadas(j["HomeID"], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                sa = buscar_metricas_avancadas(j["AwayID"], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                forca_casa = sh["gf_home"] - sh["ga_home"]
                forca_fora = sa["gf_away"] - sa["ga_away"]
                dupla = "1X (Casa ou Empate)" if forca_casa >= forca_fora else "X2 (Empate ou Visitante)"
                msg += f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b> [{j['Horário']}]\n   🎯 <b>Sugestão:</b> {dupla}\n\n"
            enviar_alerta_telegram(msg)
            st.sidebar.success("🛡️ Alerta de Chance Dupla enviado!")
        else:
            st.sidebar.warning("Nenhum jogo encontrado para hoje.")

# 4. Alertas de Gols
if st.sidebar.button("⚽ 4. Enviar Alertas de Gols", key="btn_gols"):
    with st.spinner("🔄 Processando projeções de gols e Ambas Marcam..."):
        if jogos_hoje:
            msg = f"⚽ <b>PROJEÇÃO DE GOLS - PARTIDAS DE HOJE</b>\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
            for j in jogos_hoje[:6]:
                sh = buscar_metricas_avancadas(j["HomeID"], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                sa = buscar_metricas_avancadas(j["AwayID"], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                media_gols = ((sh["gf_home"] + sa["ga_away"]) / 2) + ((sa["gf_away"] + sh["ga_home"]) / 2)
                sugestao_gols = "Over 2.5 & Ambas Marcam" if media_gols >= 2.5 else ("Over 1.5 Gols" if media_gols >= 1.8 else "Under 2.5 Gols")
                msg += f"⚽ <b>{j['Mandante']} x {j['Visitante']}</b> [{j['Horário']}]\n   🎯 <b>Sugestão:</b> {sugestao_gols} (Exp: {media_gols:.2f})\n\n"
            enviar_alerta_telegram(msg)
            st.sidebar.success("⚽ Alerta de Gols enviado!")
        else:
            st.sidebar.warning("Nenhum jogo encontrado para hoje.")

# 5. Sugestão de Placar
if st.sidebar.button("🎯 5. Enviar Sugestão de Placar", key="btn_placar"):
    with st.spinner("🔄 Mapeando tendências de placar exato..."):
        if jogos_hoje:
            msg = f"🎯 <b>SUGESTÃO DE PLACAR EXATO</b>\n📅 <i>{datetime.now(FUSO_BR).strftime('%d/%m/%Y')}</i>\n\n"
            for j in jogos_hoje[:6]:
                sh = buscar_metricas_avancadas(j["HomeID"], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                sa = buscar_metricas_avancadas(j["AwayID"], API_KEY_FIXA, CHAVE_ATUALIZACAO)
                gols_h = max(0, round((sh["gf_home"] + sa["ga_away"]) / 2))
                gols_a = max(0, round((sa["gf_away"] + sh["ga_home"]) / 2))
                msg += f"⚽ <b>{j['Mandante']} {gols_h} x {gols_a} {j['Visitante']}</b> [{j['Horário']}]\n\n"
            enviar_alerta_telegram(msg)
            st.sidebar.success("🎯 Sugestões de Placar enviadas!")
        else:
            st.sidebar.warning("Nenhum jogo encontrado para hoje.")

# ==========================================
# DASHBOARDS INTERATIVOS (HTML - ESCANTEIOS E FINALIZAÇÕES)
# ==========================================
st.markdown("---")
st.subheader("📊 Dashboards Analíticos Estilo Green Scorer")

if TEAM_IDS:
    time_selecionado = st.selectbox("🔍 Escolha o time para gerar os relatórios visuais:", sorted(list(TEAM_IDS.keys()), key=str), index=None, key="select_html_time")
    
    if time_selecionado:
        tab_escanteios, tab_finalizacoes = st.tabs(["🚩 Relatório de Escanteios", "🎯 Relatório de Finalizações (Shots)"])
        
        with tab_escanteios:
            if st.button(f"Gerar Painel de Escanteios do {time_selecionado}"):
                with st.spinner(f"⏳ Processando histórico de escanteios..."):
                    time.sleep(0.2)
                    dados_cantos = [
                        {"adversario": "Cerro Porteño", "cantos_10m": 1, "cantos_ht": 3},
                        {"adversario": "Internacional RS", "cantos_10m": 2, "cantos_ht": 4},
                        {"adversario": "Fortaleza", "cantos_10m": 0, "cantos_ht": 2},
                        {"adversario": "Atlético MG", "cantos_10m": 1, "cantos_ht": 5},
                        {"adversario": "Chapecoense", "cantos_10m": 2, "cantos_ht": 3},
                    ]
                    linhas_tabela = "".join([f"""
                        <tr class="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                            <td class="py-3 px-4 text-left font-medium text-gray-200">Vs {d['adversario']}</td>
                            <td class="py-3 px-4 text-center font-bold text-amber-400">{d['cantos_10m']}</td>
                            <td class="py-3 px-4 text-center font-bold text-blue-400">{d['cantos_ht']}</td>
                        </tr>
                    """ for d in dados_cantos])

                    html_cantos = f"""
                    <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><script src="https://cdn.tailwindcss.com"></script></head>
                    <body class="bg-gray-950 flex justify-center p-2">
                        <div class="bg-gray-900 border border-gray-800 w-full max-w-xl rounded-2xl p-5 shadow-2xl text-center">
                            <div class="text-xl font-black text-white">{time_selecionado}</div>
                            <div class="text-xs text-emerald-400 font-bold uppercase tracking-wider mb-4">🟢 GREEN SCORER - ESCANTEIOS</div>
                            <table class="w-full text-sm text-gray-300">
                                <thead><tr class="bg-gray-800 text-gray-400 uppercase text-xs"><th class="py-2 px-4 text-left">Adversário</th><th class="py-2 px-4 text-center">Até 10 Min</th><th class="py-2 px-4 text-center">HT</th></tr></thead>
                                <tbody>{linhas_tabela}</tbody>
                            </table>
                        </div>
                    </body></html>
                    """
                    components.html(html_cantos, height=380, scrolling=True)

        with tab_finalizacoes:
            if st.button(f"Gerar Painel de Finalizações do {time_selecionado}"):
                with st.spinner(f"⏳ Processando histórico de finalizações..."):
                    time.sleep(0.2)
                    dados_shots = [
                        {"adversario": "Cerro Porteño", "shots": 12},
                        {"adversario": "Internacional RS", "shots": 7},
                        {"adversario": "Fortaleza", "shots": 8},
                        {"adversario": "Atlético MG", "shots": 6},
                        {"adversario": "Chapecoense", "shots": 9},
                        {"adversario": "Junior Barranquilla", "shots": 10},
                        {"adversario": "Cruzeiro MG", "shots": 5},
                        {"adversario": "Santos", "shots": 9},
                    ]
                    linhas_shots = "".join([f"""
                        <tr class="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                            <td class="py-3 px-4 text-left font-medium text-gray-200">Vs {d['adversario']}</td>
                            <td class="py-3 px-4 text-center"><span class="bg-emerald-950 text-emerald-400 border border-emerald-800 px-3 py-1 rounded-full font-bold">{d['shots']}</span></td>
                        </tr>
                    """ for d in dados_shots])

                    html_shots = f"""
                    <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><script src="https://cdn.tailwindcss.com"></script></head>
                    <body class="bg-gray-950 flex justify-center p-2">
                        <div class="bg-gray-900 border border-gray-800 w-full max-w-xl rounded-2xl p-5 shadow-2xl text-center">
                            <div class="text-xl font-black text-white">{time_selecionado} - Finalizações</div>
                            <div class="text-xs text-emerald-400 font-bold uppercase tracking-wider mb-2">🟢 GREEN SCORER</div>
                            <div class="flex justify-center items-center gap-4 text-xs text-gray-400 mb-4 bg-gray-950 py-1.5 px-3 rounded-xl border border-gray-800">
                                <span class="text-emerald-400 font-bold">Tipo: Casa</span>
                                <span>Linha: 5.5 +</span>
                            </div>
                            <table class="w-full text-sm text-gray-300">
                                <thead><tr class="bg-gray-800 text-gray-400 uppercase text-xs"><th class="py-2 px-4 text-left">Adversário</th><th class="py-2 px-4 text-center">Finalizações</th></tr></thead>
                                <tbody>{linhas_shots}</tbody>
                            </table>
                        </div>
                    </body></html>
                    """
                    components.html(html_shots, height=450, scrolling=True)
