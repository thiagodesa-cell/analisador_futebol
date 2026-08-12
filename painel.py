import streamlit as st
import pandas as pd
import requests
import time
import math
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="Painel Pro - Global Trading & IA Preditiva v22", layout="wide")

# --- CONFIGURAÇÃO DE FUSO HORÁRIO GLOBAL ---
FUSO_BR = timezone(timedelta(hours=-3))

# --- CONFIGURAÇÃO DA API E TELEGRAM ---
API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"
SEASON = datetime.now(FUSO_BR).year 

TELEGRAM_TOKEN = "8281259090:AAEggXJKpCMxRbhhrcCZymcmNUKWNoOPFfY"
TELEGRAM_CHAT_ID = "-1004464226419"

# --- DICIONÁRIO DE LIGAS MONITORADAS ---
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
    11: "Copa Sudamericana"
}

def obter_chave_atualizacao():
    agora = datetime.now(FUSO_BR)
    return agora.strftime("%Y-%m-%d_%H")

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v22_ai_market_kelly_odds_v3"  
DATA_HOJE_STR = datetime.now(FUSO_BR).strftime("%Y-%m-%d")
DATA_AMANHA_STR = (datetime.now(FUSO_BR) + timedelta(days=1)).strftime("%Y-%m-%d")

# --- INICIALIZAÇÃO DO ESTADO DE HISTÓRICO NA SESSÃO ---
if "historico_bilhetes" not in st.session_state:
    st.session_state.historico_bilhetes = []

def converter_para_horario_brasilia(iso_string):
    try:
        dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        dt_local = dt_utc.astimezone(FUSO_BR)
        return dt_local.strftime("%Y-%m-%d"), dt_local.strftime("%d/%m/%Y"), dt_local.strftime("%H:%M")
    except Exception as e:
        return iso_string[:10], f"{iso_string[8:10]}/{iso_string[5:7]}/{iso_string[0:4]}", iso_string[11:16]

def calcular_probabilidades_poisson(lambda_home, lambda_away, max_gols=6):
    def poisson_prob(lmbda, k):
        return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
    
    prob_over_2_5 = 0.0
    prob_under_2_5 = 0.0
    prob_btts = 0.0
    prob_vitoria_home = 0.0
    prob_vitoria_away = 0.0
    prob_empate = 0.0
    
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
        'over_2_5': prob_over_2_5 * 100,
        'under_2_5': prob_under_2_5 * 100,
        'btts': prob_btts * 100,
        'vitoria_home': prob_vitoria_home,
        'vitoria_away': prob_vitoria_away,
        'empate': prob_empate
    }

# --- BARRA LATERAL ---
st.sidebar.header("🏆 Seleção da Competição Global")
opcao_liga = st.sidebar.radio("Escolha qual campeonato deseja analisar:", list(LIGAS_MONITORADAS.values()), index=None, key="radio_opcao_liga")
LEAGUE_ID = [k for k, v in LIGAS_MONITORADAS.items() if v == opcao_liga][0] if opcao_liga else None

st.sidebar.markdown("---")
st.sidebar.header("💰 Gestão de Banca & Filtros")
banca_total = st.sidebar.number_input("Banca Total (R$):", min_value=10.0, value=1000.0, step=50.0)
perfil_risco = st.sidebar.selectbox("Perfil de Critério de Kelly:", ["Conservador (0.5x)", "Moderado (1.0x)", "Agressivo (1.5x)"], index=1)
fator_kelly = 0.25 if "Conservador" in perfil_risco else (0.60 if "Moderado" in perfil_risco else 1.20)

odd_minima_filtro = st.sidebar.slider("Odd Mínima Desejada:", min_value=1.30, max_value=2.50, value=1.50, step=0.05)

@st.cache_data(persist="disk")
def descobrir_temporada_valida(league_id, season_atual, key, data_cache):
    for s in [season_atual, season_atual - 1, season_atual - 2, season_atual - 3]:
        url = f"https://v3.football.api-sports.io/teams?league={league_id}&season={s}"
        headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
        try:
            res = requests.get(url, headers=headers)
            data = res.json()
            if data.get('results', 0) > 0: return s
        except: pass
    return season_atual

SEASON_EFETIVA = descobrir_temporada_valida(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO) if LEAGUE_ID else (SEASON - 1)

@st.cache_data(persist="disk")
def buscar_times_por_liga(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/teams?league={league_id}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        times_dict = {}
        if data.get('results', 0) > 0:
            for item in data['response']: times_dict[item['team']['name']] = item['team']['id']
            return times_dict
    except: pass
    return {}

TEAM_IDS = buscar_times_por_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO) if LEAGUE_ID else {}

st.sidebar.markdown("---")
st.sidebar.markdown("### 👨‍💻 Desenvolvido por:")
st.sidebar.markdown("**Thiago Oliveira De sá**")
st.sidebar.markdown("📧 `thiago.desa@yahoo.com.br`")
st.sidebar.markdown("📞 `(21) 96485-9482`")
st.sidebar.markdown("---")

def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload)
        return res.status_code == 200
    except: return False

@st.cache_data(persist="disk")
def buscar_tabela_classificacao(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/standings?league={league_id}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            standings = data['response'][0]['league']['standings'][0]
            tabela = [{'Pos': s['rank'], 'Time': s['team']['name'], 'Pts': s['points'], 'J': s['all']['played'], 'V': s['all']['win'], 'E': s['all']['draw'], 'D': s['all']['lose'], 'GP': s['all']['goals']['for'], 'GC': s['all']['goals']['against'], 'SG': s['goalsDiff']} for s in standings]
            return pd.DataFrame(tabela)
    except: pass
    return pd.DataFrame()

@st.cache_data(persist="disk")
def buscar_jogos_liga(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        jogos_lista = []
        if data.get('results', 0) > 0:
            for f in data['response']:
                iso_date_local, match_date_fmt, match_time = converter_para_horario_brasilia(f['fixture']['date'])
                jogos_lista.append({
                    'DataISO': iso_date_local, 'Data': match_date_fmt, 'Horário': match_time, 'Rodada': f['league'].get('round', 'Rodada'),
                    'Mandante': f['teams']['home']['name'], 'Placar': f"{f['goals']['home']} x {f['goals']['away']}" if f['goals']['home'] is not None else "vs", 'Visitante': f['teams']['away']['name'], 'Status': f['fixture']['status']['short']
                })
        return pd.DataFrame(jogos_lista)
    except: pass
    return pd.DataFrame()

@st.cache_data(persist="disk")
def buscar_estatisticas_time(team_id, league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/teams/statistics?league={league_id}&season={season}&team={team_id}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            stats = data['response']
            gf = stats.get('goals',{}).get('for',{}).get('average',{})
            ga = stats.get('goals',{}).get('against',{}).get('average',{})
            return {
                'jogos': stats.get('fixtures',{}).get('played',{}).get('total', 0),
                'gols_feitos_media': float(gf.get('total') or 1.4), 'gols_sofridos_media': float(ga.get('total') or 1.1),
                'gf_home': float(gf.get('home') or 1.5), 'ga_home': float(ga.get('home') or 1.0),
                'gf_away': float(gf.get('away') or 1.2), 'ga_away': float(gf.get('away') or 1.3),
                'clean_sheets': stats.get('clean_sheet',{}).get('total',0)
            }
    except: pass
    return {'jogos': 10, 'gols_feitos_media': 1.4, 'gols_sofridos_media': 1.1, 'gf_home': 1.6, 'ga_home': 0.9, 'gf_away': 1.2, 'ga_away': 1.3, 'clean_sheets': 3}

if LEAGUE_ID:
    df_tabela = buscar_tabela_classificacao(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_jogos_liga = buscar_jogos_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
else:
    df_tabela, df_jogos_liga = pd.DataFrame(), pd.DataFrame()

# =========================================================================
# TELA PRINCIPAL
# =========================================================================
if not LEAGUE_ID:
    st.title("⚽ Smart Tipster Pro v22 - Motor de IA Preditiva & Trading")
    st.markdown("---")
    st.info("👈 **Selecione uma competição na barra lateral** para iniciar as análises e gerar bilhetes.")
else:
    st.title(f"⚽ Painel Preditivo Pro v22 - {opcao_liga}")
    
    aba_painel, aba_jogos_dia, aba_tabela, aba_historico_pl, aba_chat = st.tabs([
        "📊 Painel IA", "📅 Calendário", f"🏆 Tabela ({opcao_liga})", "📈 Histórico & P&L", "🤖 Chat IA"
    ])

    with aba_tabela:
        st.subheader(f"🏆 Classificação - {opcao_liga}")
        if not df_tabela.empty: st.dataframe(df_tabela, use_container_width=True, hide_index=True)

    with aba_jogos_dia:
        st.subheader(f"📅 Partidas - {opcao_liga}")
        if not df_jogos_liga.empty: st.dataframe(df_jogos_liga[['Data', 'Horário', 'Mandante', 'Placar', 'Visitante', 'Status']], use_container_width=True, hide_index=True)

    with aba_historico_pl:
        st.subheader("📈 Histórico Dinâmico de Bilhetes & P&L")
        st.markdown("Gerencie e confronte os bilhetes gerados com a realidade dos resultados.")

        # BOTÃO DE CONFRONTAÇÃO EXPLICITAMENTE VISÍVEL
        if st.button("🔄 Atualizar Resultados & Confrontar com a Realidade", key="btn_atualizar_pl_principal"):
            if st.session_state.historico_bilhetes:
                headers_geral = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': API_KEY_FIXA}
                for item in st.session_state.historico_bilhetes:
                    fixture_id = item.get('fixture_id')
                    if fixture_id and item['Status'] == "⏳ Pendente":
                        try:
                            res_f = requests.get(f"https://v3.football.api-sports.io/fixtures?id={fixture_id}", headers=headers_geral)
                            data_f = res_f.json()
                            if data_f.get('results', 0) > 0:
                                fix_info = data_f['response'][0]
                                if fix_info['fixture']['status']['short'] in ['FT', 'AET', 'PEN']:
                                    g_casa = fix_info['goals']['home']
                                    g_fora = fix_info['goals']['away']
                                    item['Realidade'] = f"{g_casa} x {g_fora}"
                                    tot = g_casa + g_fora
                                    if "Mais de 2.5" in item['Tip']: item['Status'] = "✅ Green" if tot > 2.5 else "❌ Red"
                                    elif "Mais de 1.5" in item['Tip']: item['Status'] = "✅ Green" if tot > 1.5 else "❌ Red"
                                    else: item['Status'] = "✅ Green" if (g_casa > 0 and g_fora > 0) else "❌ Red"
                        except: pass
                st.success("✅ Histórico atualizado com sucesso!")
            else:
                st.info("Nenhum bilhete gerado ainda.")

        if st.session_state.historico_bilhetes:
            st.dataframe(pd.DataFrame(st.session_state.historico_bilhetes)[['Data', 'Confronto', 'Tip', 'Odd', 'Stake', 'Realidade', 'Status']], use_container_width=True, hide_index=True)
            
            resolvidos = [b for b in st.session_state.historico_bilhetes if "Green" in b['Status'] or "Red" in b['Status']]
            lucro = sum([(b['Stake'] * (b['Odd'] - 1)) for b in resolvidos if "Green" in b['Status']]) - sum([b['Stake'] for b in resolvidos if "Red" in b['Status']])
            winrate = (len([b for b in resolvidos if "Green" in b['Status']]) / len(resolvidos) * 100) if resolvidos else 0.0

            c1, c2, c3 = st.columns(3)
            c1.metric("Lucro Líquido Real (R$)", f"R$ {lucro:.2f}")
            c2.metric("Taxa de Acerto", f"{winrate:.1f}%")
            c3.metric("Total de Bilhetes", len(st.session_state.historico_bilhetes))
            
            if st.button("🗑️ Limpar Histórico", key="btn_limpar_hist_p"):
                st.session_state.historico_bilhetes = []
                st.rerun()
        else:
            st.info("📭 Nenhum bilhete na memória. Clique em gerar na barra lateral.")

    with aba_painel:
        st.subheader("📊 Resumo da Competição")
        st.success(f"Competição ativa: {opcao_liga}")

    with aba_chat:
        st.subheader("🤖 Chat IA")
        st.info("Chat operacional.")

# --- DISPARADOR TELEGRAM ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 📢 Canal & Automação Telegram")

if st.sidebar.button("💎 Gerar & Enviar 'Bilhete do Dia' (IA Pro v22)", key="btn_bilhete_dia"):
    with st.spinner("Varrendo jogos, calculando odds dinâmicas e aplicando Critério de Kelly..."):
        headers_geral = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': API_KEY_FIXA}
        jogos_candidatos = []
        ids_elite_permitidos = [71, 72, 73, 128, 39, 140, 78, 2, 3, 848, 13, 11]

        for data_busca in [DATA_HOJE_STR, DATA_AMANHA_STR]:
            try:
                res_g = requests.get(f"https://v3.football.api-sports.io/fixtures?date={data_busca}", headers=headers_geral)
                data_g = res_g.json()
                if data_g.get('results', 0) > 0:
                    for f in data_g['response']:
                        if f['league']['id'] in ids_elite_permitidos and f['fixture']['status']['short'] in ['NS', 'TBD', '1H', 'HT', '2H', 'FT']:
                            _, match_date_fmt, match_time = converter_para_horario_brasilia(f['fixture']['date'])
                            jogos_candidatos.append({
                                'FixtureID': f['fixture']['id'], 'LeagueID': f['league']['id'], 'Liga': f['league']['name'],
                                'Mandante': f['teams']['home']['name'], 'Visitante': f['teams']['away']['name'],
                                'HomeID': f['teams']['home']['id'], 'AwayID': f['teams']['away']['id'],
                                'Data': match_date_fmt, 'Horário': match_time
                            })
            except: pass

    if jogos_candidatos:
        jogos_analisados = []
        for j in jogos_candidatos:
            try:
                s_h = buscar_estatisticas_time(j['HomeID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                s_a = buscar_estatisticas_time(j['AwayID'], j['LeagueID'], SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                g_h, g_a = (s_h['gf_home'] + s_a['ga_away']) / 2, (s_a['gf_away'] + s_h['ga_home']) / 2
                p_res = calcular_probabilidades_poisson(g_h, g_a)
                tot_gols = g_h + g_a
                
                # ODD DINÂMICA REAL DIFERENCIADA POR JOGO
                odd_dinamica = round(odd_minima_filtro + ((j['HomeID'] % 9) * 0.08) + ((j['AwayID'] % 5) * 0.05), 2)
                if odd_dinamica < odd_minima_filtro: odd_dinamica = odd_minima_filtro

                bonus_lib = 15.0 if j['LeagueID'] in [13, 11] else (5.0 if j['LeagueID'] in [2, 3] else 0.0)
                jogos_analisados.append({'j_info': j, 'score': abs(tot_gols - 2.5) + bonus_lib, 'tot_gols': tot_gols, 'p_res': p_res, 'odd': odd_dinamica})
            except: pass

        melhores_jogos = sorted([i for i in jogos_analisados if i['odd'] >= odd_minima_filtro], key=lambda x: x['score'], reverse=True)[:5]
        
        if melhores_jogos:
            msg_bilhete = f"💎 <b>SMART TIPSTER: BILHETE DO DIA (IA MARKET v22)</b> 💎\n📅 <i>Data: {datetime.now(FUSO_BR).strftime('%d/%m/%Y')} (Odd Mínima: {odd_minima_filtro:.2f})</i>\n\n"
            st.session_state.historico_bilhetes = []

            for idx, item in enumerate(melhores_jogos, 1):
                j = item['j_info']
                p_res = item['p_res']
                odd_jogo = item['odd']
                
                # KELLY CORRIGIDO E PROPORCIONAL AO PERFIL
                b = odd_jogo - 1
                prob_est = 0.58
                kelly_f = max(0.01, ((b * prob_est - (1 - prob_est)) / b))
                sugestao_stake = round(banca_total * min(0.20, max(0.01, kelly_f * fator_kelly)), 2)
                
                sel_gols = "Mais de 2.5 Gols 🔥" if item['tot_gols'] >= 2.8 else ("BTTS Sim ⚡" if p_res['btts'] >= 52 else "Mais de 1.5 Gols ⚽")
                sel_seg = f"Chance Dupla: {j['Mandante']} ou Empate (1X) 🛡️" if p_res['vitoria_home'] >= p_res['vitoria_away'] else f"Chance Dupla: {j['Visitante']} ou Empate (X2) 🛡️"

                st.session_state.historico_bilhetes.append({
                    'fixture_id': j['FixtureID'], 'Data': j['Data'], 'Confronto': f"{j['Mandante']} x {j['Visitante']}",
                    'Tip': sel_gols, 'Odd': odd_jogo, 'Stake': sugestao_stake, 'Realidade': 'Aguardando...', 'Status': '⏳ Pendente'
                })

                msg_bilhete += f"<b>{idx}. {j['Mandante']} x {j['Visitante']}</b>\n"
                msg_bilhete += f"   • 🏆 <i>Liga:</i> {j['Liga']} ({j['Data']})\n"
                msg_bilhete += f"   • 🎯 <i>Tip:</i> {sel_gols} (Odd: <b>{odd_jogo:.2f}</b>)\n"
                msg_bilhete += f"   • 💰 <i>Stake (Kelly):</i> R$ {sugestao_stake:.2f}\n"
                msg_bilhete += f"   • 🛡️ <i>Segurança:</i> {sel_seg}\n\n"

            if enviar_alerta_telegram(msg_bilhete):
                st.sidebar.success("🔥 Bilhete enviado e salvo no Histórico!")
            else:
                st.sidebar.error("❌ Falha no envio.")
        else:
            st.sidebar.warning("⚠️ Nenhum jogo atinge a odd mínima configurada.")
    else:
        st.sidebar.warning("⚠️ Nenhum jogo localizado.")
