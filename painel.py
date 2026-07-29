import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Painel Pro - Plantéis Completos Série A", layout="wide")

st.title("⚽ Painel Analisador Esportivo Pro - Elencos & H2H Real")
st.write("Dados extraídos da API-Football (Atualização Diária Automática às 08:00h).")

# --- CONFIGURAÇÃO DA API E TELEGRAM ---
API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"
LEAGUE_ID = 71  # ID Oficial do Brasileirão Série A na API
SEASON = datetime.now().year 

TELEGRAM_TOKEN = "8281259090:AAEggXJKpCMxRbhhrcCZymcmNUKWNoOPFfY"
TELEGRAM_CHAT_ID = "-1004464226419"  # ID do Telegram configurado

# --- LÓGICA DE ATUALIZAÇÃO ÀS 8H DA MANHÃ ---
def obter_chave_atualizacao():
    """Gera uma string que só muda às 8:00 da manhã de cada dia."""
    agora = datetime.now()
    if agora.hour < 8:
        return (agora - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        return agora.strftime("%Y-%m-%d")

CHAVE_ATUALIZACAO = obter_chave_atualizacao()

st.sidebar.success(f"✅ Painel Integrado via API (Temporada {SEASON})!")
st.sidebar.info(f"🔄 Última atualização dos dados base: {CHAVE_ATUALIZACAO} às 08:00")
st.sidebar.markdown("---")
st.sidebar.markdown("### 👨‍💻 Painel Desenvolvido por:")
st.sidebar.markdown("**Thiago Oliveira De sá**")
st.sidebar.markdown("📧 `thiago.desa@yahoo.com.br`")
st.sidebar.markdown("📞 `(21) 96485-9482`")
st.sidebar.markdown("---")


# --- FUNÇÃO DE ENVIO PARA O TELEGRAM ---
def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            return True
        else:
            st.sidebar.error(f"Erro Telegram: {res.text}")
            return False
    except Exception as e:
        st.sidebar.error(f"Falha ao conectar no Telegram: {e}")
        return False


# --- FUNÇÕES DE BUSCA NA API (COM CACHE DIÁRIO) ---

@st.cache_data
def buscar_times_serie_a(season, key, data_cache):
    url = f"https://v3.football.api-sports.io/teams?league={LEAGUE_ID}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        times_dict = {}
        
        if data.get('results', 0) > 0:
            for item in data['response']:
                nome_time = item['team']['name']
                id_time = item['team']['id']
                times_dict[nome_time] = id_time
            return times_dict
    except Exception as e:
        st.error(f"Erro ao buscar a lista de times: {e}")
        
    return {}

@st.cache_data
def buscar_estatisticas_time(team_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/teams/statistics?league={LEAGUE_ID}&season={season}&team={team_id}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            stats = data['response']
            goals_for = stats.get('goals', {}).get('for', {}).get('average', {}).get('total', '0')
            goals_against = stats.get('goals', {}).get('against', {}).get('average', {}).get('total', '0')
            jogos = stats.get('fixtures', {}).get('played', {}).get('total', 0)
            clean_sheets = stats.get('clean_sheet', {}).get('total', 0)
            
            return {
                'jogos': jogos,
                'gols_feitos_media': float(goals_for) if goals_for else 0.0,
                'gols_sofridos_media': float(goals_against) if goals_against else 0.0,
                'clean_sheets': clean_sheets
            }
    except Exception as e:
        st.error(f"Erro API (Stats Time): {e}")
        
    return {'jogos': 0, 'gols_feitos_media': 0.0, 'gols_sofridos_media': 0.0, 'clean_sheets': 0}

@st.cache_data
def buscar_scout_elenco_u5(team_id, season, key, data_cache):
    """Busca as estatísticas individuais dos jogadores e a forma do time nas últimas 5 partidas."""
    url_fixtures = f"https://v3.football.api-sports.io/fixtures?league={LEAGUE_ID}&season={season}&team={team_id}&last=5"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    
    forma_lista = []
    try:
        res_fix = requests.get(url_fixtures, headers=headers)
        data_fix = res_fix.json()
        if data_fix.get('results', 0) == 0:
            return pd.DataFrame(), "Sem dados"
        
        fixtures = data_fix['response']
        
        for f_item in reversed(fixtures):
            home_id = f_item['teams']['home']['id']
            home_winner = f_item['teams']['home']['winner']
            away_winner = f_item['teams']['away']['winner']
            
            if home_winner is None and away_winner is None:
                forma_lista.append("🟡")
            elif (home_id == team_id and home_winner is True) or (home_id != team_id and away_winner is True):
                forma_lista.append("🟢")
            else:
                forma_lista.append("🔴")
                
        forma_string = " ".join(forma_lista)
        player_data = {}
        
        for f_item in fixtures:
            f_id = f_item['fixture']['id']
            url_players = f"https://v3.football.api-sports.io/fixtures/players?fixture={f_id}"
            res_play = requests.get(url_players, headers=headers)
            data_play = res_play.json()
            
            if data_play.get('results', 0) > 0:
                for t_item in data_play['response']:
                    if t_item['team']['id'] == team_id:
                        for p_item in t_item['players']:
                            p_name = p_item['player']['name']
                            stats = p_item['statistics'][0] if p_item['statistics'] else {}
                            
                            minutes = stats.get('games', {}).get('minutes')
                            try:
                                mins = int(minutes) if minutes else 0
                            except:
                                mins = 0
                            
                            if mins > 0:
                                shots_total = stats.get('shots', {}).get('total') or 0
                                shots_on = stats.get('shots', {}).get('on') or 0
                                fouls_committed = stats.get('fouls', {}).get('committed') or 0
                                fouls_drawn = stats.get('fouls', {}).get('drawn') or 0
                                tackles = stats.get('tackles', {}).get('total') or 0
                                goals = stats.get('goals', {}).get('total') or 0
                                yellow = stats.get('cards', {}).get('yellow') or 0
                                red = stats.get('cards', {}).get('red') or 0
                                
                                if p_name not in player_data:
                                    player_data[p_name] = {
                                        'Posição': stats.get('games', {}).get('position', '-'),
                                        'Jogos (U5)': 0,
                                        'Gols': 0,
                                        'Finalizações': 0,
                                        'Chutes no Alvo': 0,
                                        'Faltas Cometidas': 0,
                                        'Faltas Sofridas': 0,
                                        'Desarmes': 0,
                                        'Amarelos': 0,
                                        'Vermelhos': 0
                                    }
                                
                                player_data[p_name]['Jogos (U5)'] += 1
                                player_data[p_name]['Gols'] += goals
                                player_data[p_name]['Finalizações'] += shots_total
                                player_data[p_name]['Chutes no Alvo'] += shots_on
                                player_data[p_name]['Faltas Cometidas'] += fouls_committed
                                player_data[p_name]['Faltas Sofridas'] += fouls_drawn
                                player_data[p_name]['Desarmes'] += tackles
                                player_data[p_name]['Amarelos'] += yellow
                                player_data[p_name]['Vermelhos'] += red
        
        rows = []
        for name, data in player_data.items():
            j = data['Jogos (U5)']
            if j > 0:
                rows.append({
                    'Jogador': name,
                    'Posição': data['Posição'],
                    'Jogos (U5)': f"{j}/5",
                    'Gols (Total U5)': data['Gols'],
                    'Finalizações Média': round(data['Finalizações'] / j, 2),
                    'Chutes no Alvo Média': round(data['Chutes no Alvo'] / j, 2),
                    'Faltas Cometidas Média': round(data['Faltas Cometidas'] / j, 2),
                    'Faltas Sofridas Média': round(data['Faltas Sofridas'] / j, 2),
                    'Desarmes Média': round(data['Desarmes'] / j, 2),
                    'Amarelos (Total U5)': data['Amarelos'],
                    'Vermelhos (Total U5)': data['Vermelhos']
                })
        
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values(by=['Gols (Total U5)', 'Finalizações Média'], ascending=[False, False])
        return df, forma_string
        
    except Exception as e:
        st.error(f"Erro API (Scout U5): {e}")
        return pd.DataFrame(), "Erro"

@st.cache_data
def buscar_h2h_api(id1, id2, key, data_cache):
    url = f"https://v3.football.api-sports.io/fixtures/headtohead?h2h={id1}-{id2}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if response.status_code == 200 and data.get('results', 0) > 0:
            fixtures = data['response']
            fixtures = sorted(fixtures, key=lambda x: x['fixture']['date'], reverse=True)[:6]
            
            h2h_lista = []
            for match in fixtures:
                data_jogo = match['fixture']['date'][:10]
                h2h_lista.append({
                    'Data': f"{data_jogo[8:10]}/{data_jogo[5:7]}/{data_jogo[0:4]}",
                    'Competição': match['league']['name'],
                    'Mandante': match['teams']['home']['name'],
                    'Placar': f"{match['goals']['home']} x {match['goals']['away']}",
                    'Visitante': match['teams']['away']['name']
                })
            return pd.DataFrame(h2h_lista), None
        return None, "Nenhum confronto recente retornado."
    except Exception as e:
        return None, f"Erro na conexão com a API: {e}"


# --- CARREGAMENTO INICIAL DOS TIMES ---
TEAM_IDS = buscar_times_serie_a(SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)

if not TEAM_IDS:
    st.warning(f"⚠️ Não foi possível carregar os times da temporada {SEASON}.")
    st.stop()


# --- INTERFACE E PROCESSAMENTO DO DASHBOARD (FOCO EM UM SÓ TIME NA SIDEBAR) ---
st.sidebar.header("⚙️ Configurações de Análise")
times_disponiveis = list(TEAM_IDS.keys())
times_disponiveis.sort() 

time_principal = st.sidebar.selectbox("Escolha o Time Principal para Análise", times_disponiveis)

with st.spinner("Extraindo e calculando dados reais da API..."):
    id_time1 = TEAM_IDS[time_principal]
    stats_t1 = buscar_estatisticas_time(id_time1, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_elenco_u5, string_forma_t1 = buscar_scout_elenco_u5(id_time1, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)


# --- SEÇÃO 1: DESEMPENHO COLETIVO ---
st.subheader(f"📊 Desempenho Coletivo (Temporada {SEASON}): {time_principal}")

st.markdown(f"**Forma Recente (Últimas 5 partidas):** {string_forma_t1}")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Jogos Disputados", stats_t1['jogos'])
with c2:
    st.metric("Média Gols Feitos", f"{stats_t1['gols_feitos_media']:.2f}")
with c3:
    st.metric("Média Gols Sofridos", f"{stats_t1['gols_sofridos_media']:.2f}")
with c4:
    st.metric("Jogos Sem Sofrer Gol", stats_t1['clean_sheets'])

st.markdown("---")


# --- SEÇÃO 2: SCOUT DO PLANTEL (DESIGN PREMIUM PRO - ÚLTIMOS 5 JOGOS) ---
st.subheader(f"👤 Scout do Plantel (Média das Últimas 5 Partidas): {time_principal}")
st.caption("Visualização Analítica Avançada com barras dinâmicas.")

if df_elenco_u5 is not None and not df_elenco_u5.empty:
    st.dataframe(
        df_elenco_u5, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Gols (Total U5)": st.column_config.NumberColumn("Gols (Total U5)", format="%d ⚽"),
            "Finalizações Média": st.column_config.ProgressColumn("Finalizações Média", min_value=0, max_value=5, format="%.2f"),
            "Chutes no Alvo Média": st.column_config.ProgressColumn("Chutes no Alvo Média", min_value=0, max_value=3, format="%.2f"),
            "Desarmes Média": st.column_config.ProgressColumn("Desarmes Média", min_value=0, max_value=6, format="%.2f"),
            "Amarelos (Total U5)": st.column_config.NumberColumn("Amarelos (Total U5)", format="%d 🟨"),
            "Vermelhos (Total U5)": st.column_config.NumberColumn("Vermelhos (Total U5)", format="%d 🟥"),
            "Faltas Cometidas Média": st.column_config.NumberColumn("Faltas Cometidas Média", format="%.2f ⏱️"),
            "Faltas Sofridas Média": st.column_config.NumberColumn("Faltas Sofridas Média", format="%.2f 🚀")
        }
    )
else:
    st.warning("Não há dados de scout disponíveis para as últimas 5 partidas deste clube no momento.")

st.markdown("---")


# --- SEÇÃO 3: SIMULADOR DE CONFRONTO DIRETO & HISTÓRICO (TOTALMENTE OPCIONAL) ---
st.subheader("🤖 Simulador de Confronto Direto & H2H")
usar_comparacao = st.checkbox("Ativar comparação e simulação contra um adversário")

adversario = None
if usar_comparacao:
    adversario = st.selectbox("Escolha o Time Adversário para Análise de Confronto", [t for t in times_disponiveis if t != time_principal])

    if adversario:
        id_time2 = TEAM_IDS[adversario]
        stats_t2 = buscar_estatisticas_time(id_time2, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)

        gols_t1 = (stats_t1['gols_feitos_media'] + stats_t2['gols_sofridos_media']) / 2
        gols_t2 = (stats_t2['gols_feitos_media'] + stats_t1['gols_sofridos_media']) / 2
        total_gols = gols_t1 + gols_t2

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.metric(f"Expec. Gols ({time_principal})", f"{gols_t1:.2f}")
        with sc2:
            st.metric(f"Expec. Gols ({adversario})", f"{gols_t2:.2f}")
        with sc3:
            st.metric("Total de Gols Esperados", f"{total_gols:.2f}")

        tendencia_texto = ""
        if total_gols >= 2.5:
            tendencia_texto = "Mais de 2.5 Gols 🔥"
            st.success(f"🔥 **Tendência:** Alta probabilidade de **Mais de 2.5 Gols**.")
        else:
            tendencia_texto = "Menos de 2.5 Gols 🛡️"
            st.warning(f"🛡️ **Tendência:** Jogo truncado, tendência de **Menos de 2.5 Gols**.")

        st.markdown(f"### 📜 Histórico Real de Confronto: {time_principal} vs {adversario}")

        df_h2h_real, erro_api = buscar_h2h_api(id_time1, id_time2, API_KEY_FIXA, CHAVE_ATUALIZACAO)

        if df_h2h_real is not None and not df_h2h_real.empty:
            st.dataframe(df_h2h_real, use_container_width=True, hide_index=True)
        else:
            st.info(erro_api if erro_api else "Sem dados recentes de H2H na API.")


# --- DISPARADOR DO TELEGRAM VIA SIDEBAR ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 📢 Enviar Análise para o Telegram")
if st.sidebar.button("🚀 Disparar Alerta Pré-Live"):
    if TELEGRAM_CHAT_ID == "DIGITE_SEU_ID_AQUI":
        st.sidebar.warning("⚠️ Insira o seu ID do Telegram no código antes de enviar!")
    else:
        if usar_comparacao and adversario:
            id_time2_tel = TEAM_IDS.get(adversario, list(TEAM_IDS.values())[0])
            stats_t2_tel = buscar_estatisticas_time(id_time2_tel, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            g_t1 = (stats_t1['gols_feitos_media'] + stats_t2_tel['gols_sofridos_media']) / 2
            g_t2 = (stats_t2_tel['gols_feitos_media'] + stats_t1['gols_sofridos_media']) / 2
            t_gols = g_t1 + g_t2
            tend_tel = "Mais de 2.5 Gols 🔥" if t_gols >= 2.5 else "Menos de 2.5 Gols 🛡️"

            msg_telegram = f"""🚨 <b>RAIO-X PRÉ-LIVE PRO</b> 🚨

⚽ <b>{time_principal} x {adversario}</b>
🏆 Competição: Brasileirão Série A

📊 <b>MÉDIAS NA TEMPORADA:</b>
• Gols Feitos ({time_principal}): {stats_t1['gols_feitos_media']:.2f}/j
• Gols Sofridos ({time_principal}): {stats_t1['gols_sofridos_media']:.2f}/j
• Gols Feitos ({adversario}): {stats_t2_tel['gols_feitos_media']:.2f}/j
• Gols Sofridos ({adversario}): {stats_t2_tel['gols_sofridos_media']:.2f}/j

🤖 <b>PROJEÇÃO E TENDÊNCIAS:</b>
• Expec. Gols {time_principal}: {g_t1:.2f}
• Expec. Gols {adversario}: {g_t2:.2f}
• Total Estimado: {t_gols:.2f}
• Tendência de Gols: <b>{tend_tel}</b>

📈 <i>Dica: Acesse o Painel Streamlit para conferir o scout completo!</i>"""
        else:
            msg_telegram = f"""🚨 <b>RAIO-X DO PLANTEL - PRO</b> 🚨

⚽ <b>Time: {time_principal}</b>
🏆 Competição: Brasileirão Série A

📊 <b>MÉDIAS NA TEMPORADA:</b>
• Jogos Disputados: {stats_t1['jogos']}
• Média Gols Feitos: {stats_t1['gols_feitos_media']:.2f}/j
• Média Gols Sofridos: {stats_t1['gols_sofridos_media']:.2f}/j
• Jogos Sem Sofrer Gol: {stats_t1['clean_sheets']}

📈 <i>Dica: Acesse o Painel Streamlit para conferir o scout completo do elenco!</i>"""
        
        with st.sidebar.spinner("Enviando..."):
            sucesso = enviar_alerta_telegram(msg_telegram)
            if sucesso:
                st.sidebar.success("🎉 Alerta enviado com sucesso para o Telegram!")
