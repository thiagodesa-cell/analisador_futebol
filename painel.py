import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="Painel Pro - Global Trading & Futebol", layout="wide")

# --- CONFIGURAÇÃO DA API E TELEGRAM ---
API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"
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

# --- BOTÃO DE SELEÇÃO DE LIGA NA BARRA LATERAL ---
st.sidebar.header("🏆 Seleção da Competição Global")
opcao_liga = st.sidebar.radio(
    "Escolha qual campeonato deseja analisar:",
    [
        "Brasileirão Série A", 
        "Brasileirão Série B", 
        "Campeonato Argentino",
        "Premier League (Inglaterra)",
        "La Liga (Espanha)",
        "Bundesliga (Alemanha)"
    ]
)

# Define o ID dinamicamente com base na liga escolhida
if opcao_liga == "Brasileirão Série A":
    LEAGUE_ID = 71
elif opcao_liga == "Brasileirão Série B":
    LEAGUE_ID = 72
elif opcao_liga == "Campeonato Argentino":
    LEAGUE_ID = 128
elif opcao_liga == "Premier League (Inglaterra)":
    LEAGUE_ID = 39
elif opcao_liga == "La Liga (Espanha)":
    LEAGUE_ID = 140
else:
    LEAGUE_ID = 78  # Bundesliga (Alemanha)

st.sidebar.success(f"✅ Ativo: {opcao_liga} (Temporada {SEASON})!")
st.sidebar.info(f"🔄 Última atualização base: {CHAVE_ATUALIZACAO} às 08:00")
st.sidebar.markdown("---")
st.sidebar.markdown("### 👨‍💻 Painel Desenvolvido por:")
st.sidebar.markdown("**Thiago Oliveira De sá**")
st.sidebar.markdown("📧 `thiago.desa@yahoo.com.br`")
st.sidebar.markdown("📞 `(21) 96485-9482`")
st.sidebar.markdown("---")

# Título dinâmico na tela principal
st.title(f"⚽ Painel Analisador Esportivo Pro - {opcao_liga}")
st.write(f"Dados integrados em tempo real via API-Football para a competição {opcao_liga}.")


# --- FUNÇÃO DE ENVIO PARA O TELEGRAM ---
def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
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


# --- FUNÇÕES DE BUSCA NA API (COM CACHE DIÁRIO ISOLADO) ---

@st.cache_data
def buscar_times_por_liga(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/teams?league={league_id}&season={season}"
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
def buscar_tabela_classificacao(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/standings?league={league_id}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            standings = data['response'][0]['league']['standings'][0]
            tabela = []
            for s in standings:
                tabela.append({
                    'Pos': s['rank'],
                    'Time': s['team']['name'],
                    'Pts': s['points'],
                    'J': s['all']['played'],
                    'V': s['all']['win'],
                    'E': s['all']['draw'],
                    'D': s['all']['lose'],
                    'GP': s['all']['goals']['for'],
                    'GC': s['all']['goals']['against'],
                    'SG': s['goalsDiff']
                })
            return pd.DataFrame(tabela)
    except Exception as e:
        st.error(f"Erro ao buscar tabela de classificação: {e}")
    return pd.DataFrame()

@st.cache_data
def buscar_jogos_liga(league_id, season, key, data_cache):
    """Busca todos os confrontos da temporada para montar o calendário e jogos do dia."""
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            fixtures = data['response']
            jogos_lista = []
            for f in fixtures:
                date_str = f['fixture']['date']
                match_date = date_str[:10]
                match_time = date_str[11:16]
                status = f['fixture']['status']['short']
                
                home_name = f['teams']['home']['name']
                away_name = f['teams']['away']['name']
                
                goals_home = f['goals']['home']
                goals_away = f['goals']['away']
                
                if goals_home is not None and goals_away is not None:
                    placar_str = f"{goals_home} x {goals_away}"
                else:
                    placar_str = "vs"
                
                round_name = f['league'].get('round', 'Rodada')
                
                jogos_lista.append({
                    'Data': f"{match_date[8:10]}/{match_date[5:7]}/{match_date[0:4]}",
                    'Horário': match_time,
                    'Rodada': round_name,
                    'Mandante': home_name,
                    'Placar': placar_str,
                    'Visitante': away_name,
                    'Status': status,
                    'Raw_Date': match_date
                })
            return pd.DataFrame(jogos_lista)
    except Exception as e:
        st.error(f"Erro ao buscar os jogos da liga: {e}")
    return pd.DataFrame()

@st.cache_data
def buscar_dados_arbitros(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            fixtures = data['response']
            ref_data = {}
            for f in fixtures:
                ref = f['fixture']['referee']
                if not ref:
                    ref = "Não Divulgado / Desconhecido"
                
                status = f['fixture']['status']['short']
                if status in ['FT', 'AET', 'PEN', '1H', '2H', 'HT', 'ET']: 
                    home_team = f['teams']['home']['name']
                    away_team = f['teams']['away']['name']
                    match_date = f['fixture']['date'][:10]
                    
                    if ref not in ref_data:
                        ref_data[ref] = {
                            'Jogos': 0,
                            'Partidas_Detalhes': []
                        }
                    ref_data[ref]['Jogos'] += 1
                    ref_data[ref]['Partidas_Detalhes'].append({
                        'Data': f"{match_date[8:10]}/{match_date[5:7]}/{match_date[0:4]}",
                        'Confronto': f"{home_team} x {away_team}"
                    })
            
            rows = []
            for ref, info in ref_data.items():
                rows.append({
                    'Árbitro': ref,
                    'Jogos Apitados': info['Jogos'],
                    'Últimos Confrontos': ", ".join([p['Confronto'] for p in info['Partidas_Detalhes'][:3]]) + ("..." if len(info['Partidas_Detalhes']) > 3 else "")
                })
            
            df_ref = pd.DataFrame(rows)
            if not df_ref.empty:
                df_ref = df_ref.sort_values(by='Jogos Apitados', ascending=False)
            return df_ref
    except Exception as e:
        st.error(f"Erro ao buscar árbitros: {e}")
    return pd.DataFrame()

@st.cache_data
def buscar_medias_escanteios(team_id, league_id, season, key, data_cache):
    url_fixtures = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&team={team_id}&last=10"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    
    cantos_pro_casa, cantos_contra_casa = [], []
    cantos_pro_fora, cantos_contra_fora = [], []
    detalhes_partidas_cantos = []
    
    try:
        res = requests.get(url_fixtures, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            fixtures = data['response']
            for f in fixtures:
                f_id = f['fixture']['id']
                home_id = f['teams']['home']['id']
                away_name = f['teams']['away']['name']
                home_name = f['teams']['home']['name']
                match_date = f['fixture']['date'][:10]
                is_home = (home_id == team_id)
                
                url_stats = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={f_id}"
                
                # Proteção de cadência de requisição
                time.sleep(0.2)
                res_stats = requests.get(url_stats, headers=headers)
                data_stats = res_stats.json()
                
                if data_stats.get('results', 0) > 0:
                    team_corners, opponent_corners = 0, 0
                    for team_stat_item in data_stats['response']:
                        t_id = team_stat_item['team']['id']
                        stats_list = team_stat_item['statistics']
                        corners_val = 0
                        for stat in stats_list:
                            if stat['type'] == 'Corner Kicks':
                                val = stat['value']
                                try:
                                    corners_val = int(val) if val is not None else 0
                                except:
                                    corners_val = 0
                        
                        if t_id == team_id:
                            team_corners = corners_val
                        else:
                            opponent_corners = corners_val
                    
                    if is_home:
                        cantos_pro_casa.append(team_corners)
                        cantos_contra_casa.append(opponent_corners)
                    else:
                        cantos_pro_fora.append(team_corners)
                        cantos_contra_fora.append(opponent_corners)
                        
                    detalhes_partidas_cantos.append({
                        'Data': f"{match_date[8:10]}/{match_date[5:7]}/{match_date[0:4]}",
                        'Adversário': away_name if is_home else home_name,
                        'Mando': 'Casa' if is_home else 'Fora',
                        'Cantos Pró': team_corners,
                        'Cantos Contra': opponent_corners,
                        'Total na Partida': team_corners + opponent_corners
                    })
                        
        cf_home = sum(cantos_pro_casa) / len(cantos_pro_casa) if cantos_pro_casa else 0.0
        ca_home = sum(cantos_contra_casa) / len(cantos_contra_casa) if cantos_contra_casa else 0.0
        cf_away = sum(cantos_pro_fora) / len(cantos_pro_fora) if cantos_pro_fora else 0.0
        ca_away = sum(cantos_contra_fora) / len(cantos_contra_fora) if cantos_contra_fora else 0.0
        
        todos_pro = cantos_pro_casa + cantos_pro_fora
        todos_contra = cantos_contra_casa + cantos_contra_fora
        cf_geral = sum(todos_pro) / len(todos_pro) if todos_pro else 0.0
        ca_geral = sum(todos_contra) / len(todos_contra) if todos_contra else 0.0
        
        df_historico_cantos = pd.DataFrame(detalhes_partidas_cantos)
        
        return {
            'corners_for_geral': cf_geral, 'corners_ag_geral': ca_geral,
            'corners_for_home': cf_home, 'corners_ag_home': ca_home,
            'corners_for_away': cf_away, 'corners_ag_away': ca_away,
            'df_historico': df_historico_cantos
        }
    except Exception as e:
        return {
            'corners_for_geral': 0.0, 'corners_ag_geral': 0.0, 
            'corners_for_home': 0.0, 'corners_ag_home': 0.0, 
            'corners_for_away': 0.0, 'corners_ag_away': 0.0,
            'df_historico': pd.DataFrame()
        }

@st.cache_data
def buscar_estatisticas_time(team_id, league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/teams/statistics?league={league_id}&season={season}&team={team_id}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            stats = data['response']
            
            goals_for = stats.get('goals', {}).get('for', {}).get('average', {}).get('total', '0')
            goals_against = stats.get('goals', {}).get('against', {}).get('average', {}).get('total', '0')
            
            gf_home = stats.get('goals', {}).get('for', {}).get('average', {}).get('home', '0')
            ga_home = stats.get('goals', {}).get('against', {}).get('average', {}).get('home', '0')
            
            gf_away = stats.get('goals', {}).get('for', {}).get('average', {}).get('away', '0')
            ga_away = stats.get('goals', {}).get('against', {}).get('average', {}).get('away', '0')
            
            jogos = stats.get('fixtures', {}).get('played', {}).get('total', 0)
            clean_sheets = stats.get('clean_sheet', {}).get('total', 0)
            
            gf_min = stats.get('goals', {}).get('for', {}).get('minute', {})
            ga_min = stats.get('goals', {}).get('against', {}).get('minute', {})
            yellow_cards_data = stats.get('cards', {}).get('yellow', {})
            
            intervals = ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "91-105", "106-120"]
            min_data = []
            card_data = []
            
            for interv in intervals:
                f_obj = gf_min.get(interv, {}) if gf_min.get(interv) else {}
                a_obj = ga_min.get(interv, {}) if ga_min.get(interv) else {}
                y_obj = yellow_cards_data.get(interv, {}) if isinstance(yellow_cards_data.get(interv), dict) else {}
                
                f_val = f_obj.get('total') if f_obj.get('total') is not None else 0
                a_val = a_obj.get('total') if a_obj.get('total') is not None else 0
                y_val = y_obj.get('total') if y_obj.get('total') is not None else 0
                
                min_data.append({
                    'Intervalo': f"{interv} min",
                    'Gols Feitos': int(f_val),
                    'Gols Sofridos': int(a_val)
                })
                
                card_data.append({
                    'Intervalo': f"{interv} min",
                    'Cartões Amarelos': int(y_val)
                })
            
            df_minutagem = pd.DataFrame(min_data)
            df_cartoes = pd.DataFrame(card_data)
            
            return {
                'jogos': jogos,
                'gols_feitos_media': float(goals_for) if goals_for else 0.0,
                'gols_sofridos_media': float(goals_against) if goals_against else 0.0,
                'gf_home': float(gf_home) if gf_home else 0.0,
                'ga_home': float(ga_home) if ga_home else 0.0,
                'gf_away': float(gf_away) if gf_away else 0.0,
                'ga_away': float(ga_away) if ga_away else 0.0,
                'clean_sheets': clean_sheets,
                'df_minutagem': df_minutagem,
                'df_cartoes': df_cartoes
            }
    except Exception as e:
        st.error(f"Erro API (Stats Time): {e}")
        
    return {
        'jogos': 0, 'gols_feitos_media': 0.0, 'gols_sofridos_media': 0.0,
        'gf_home': 0.0, 'ga_home': 0.0, 'gf_away': 0.0, 'ga_away': 0.0, 'clean_sheets': 0,
        'df_minutagem': pd.DataFrame(), 'df_cartoes': pd.DataFrame()
    }

@st.cache_data
def buscar_scout_elenco_u5(team_id, league_id, season, key, data_cache):
    url_fixtures = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&team={team_id}&last=5"
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
            
            # Proteção de cadência de requisição
            time.sleep(0.2)
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


# --- CARREGAMENTO INICIAL DINÂMICO DOS TIMES E DADOS ---
TEAM_IDS = buscar_times_por_liga(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)

if not TEAM_IDS:
    st.warning(f"⚠️ Não foi possível carregar os times da competição selecionada ({opcao_liga}).")
    st.stop()

st.sidebar.header("⚙️ Configurações de Análise")
times_disponiveis = list(TEAM_IDS.keys())
times_disponiveis.sort() 

time_principal = st.sidebar.selectbox("Escolha o Time", times_disponiveis)

with st.spinner(f"Extraindo dados reais de {opcao_liga}..."):
    id_time1 = TEAM_IDS[time_principal]
    stats_t1 = buscar_estatisticas_time(id_time1, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    corners_t1 = buscar_medias_escanteios(id_time1, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_elenco_u5, string_forma_t1 = buscar_scout_elenco_u5(id_time1, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_tabela = buscar_tabela_classificacao(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_arbitros = buscar_dados_arbitros(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_jogos_liga = buscar_jogos_liga(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)


# --- ABAS DE NAVEGAÇÃO SUPERIOR ---
aba_painel, aba_jogos_dia, aba_arbitros, aba_tabela = st.tabs([
    "📊 Painel de Análise & Elenco", 
    "📅 Jogos & Rodada", 
    "⚖️ Árbitros", 
    f"🏆 Tabela ({opcao_liga})"
])

with aba_tabela:
    st.subheader(f"🏆 Classificação Atual - {opcao_liga} ({SEASON})")
    if not df_tabela.empty:
        st.dataframe(
            df_tabela, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Pos": st.column_config.NumberColumn("Pos", format="%d º"),
                "Pts": st.column_config.NumberColumn("Pts", format="%d pts"),
                "SG": st.column_config.NumberColumn("SG", format="%d")
            }
        )
    else:
        st.warning("Tabela de classificação indisponível no momento.")

with aba_jogos_dia:
    st.subheader(f"📅 Calendário e Partidas da Rodada - {opcao_liga}")
    st.caption("Consulte os confrontos da competição, horários e placares em tempo real.")
    
    if not df_jogos_liga.empty:
        data_hoje_str = datetime.now().strftime("%d/%m/%Y")
        
        filtro_opcao = st.radio(
            "Filtrar visualização:",
            ["Ver Apenas Jogos de Hoje", "Ver Todos os Jogos da Temporada"],
            horizontal=True
        )
        
        df_exibir = df_jogos_liga.copy()
        if filtro_opcao == "Ver Apenas Jogos de Hoje":
            df_exibir = df_exibir[df_exibir['Data'] == data_hoje_str]
            if df_exibir.empty:
                st.info(f"Nenhuma partida programada para hoje ({data_hoje_str}) nesta liga. Alterne para 'Ver Todos os Jogos da Temporada' para conferir o calendário completo.")
        
        if not df_exibir.empty:
            st.dataframe(
                df_exibir[['Data', 'Horário', 'Rodada', 'Mandante', 'Placar', 'Visitante', 'Status']],
                use_container_width=True,
                hide_index=True
            )
    else:
        st.warning("Calendário de jogos indisponível no momento.")

with aba_arbitros:
    st.subheader(f"⚖️ Perfil dos Árbitros - {opcao_liga}")
    st.caption("Relação de árbitros atuantes na competição e histórico de partidas recentes apitadas.")
    if not df_arbitros.empty:
        st.dataframe(
            df_arbitros,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Jogos Apitados": st.column_config.NumberColumn("Jogos Apitados", format="%d 🟨")
            }
        )
    else:
        st.warning("Dados de arbitragem indisponíveis no momento.")

with aba_painel:
    # --- DESEMPENHO COLETIVO ---
    st.subheader(f"📊 Desempenho Coletivo: {time_principal}")
    st.markdown(f"**Forma Recente (Últimas 5 partidas):** {string_forma_t1}")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Jogos Disputados", stats_t1['jogos'])
    with c2:
        st.metric("Média Gols Feitos (Geral)", f"{stats_t1['gols_feitos_media']:.2f}")
    with c3:
        st.metric("Média Gols Sofridos (Geral)", f"{stats_t1['gols_sofridos_media']:.2f}")
    with c4:
        st.metric("Jogos Sem Sofrer Gol", stats_t1['clean_sheets'])

    st.markdown("##### 🏟️ Recorte de Mando de Campo (Gols)")
    cc1, cc2, cc3, cc4 = st.columns(4)
    with cc1:
        st.metric("GF em Casa", f"{stats_t1['gf_home']:.2f}")
    with cc2:
        st.metric("GC em Casa", f"{stats_t1['ga_home']:.2f}")
    with cc3:
        st.metric("GF Fora", f"{stats_t1['gf_away']:.2f}")
    with cc4:
        st.metric("GC Fora", f"{stats_t1['ga_away']:.2f}")

    st.markdown("---")

    # --- MÉDIAS E HISTÓRICO DE ESCANTEIOS ---
    st.subheader(f"🚩 Estatísticas e Histórico de Escanteios (Corners): {time_principal}")
    
    co1, co2, co3, co4, co5, co6 = st.columns(6)
    with co1:
        st.metric("Cantos Pró (Geral)", f"{corners_t1['corners_for_geral']:.2f}")
    with co2:
        st.metric("Cantos Contra (Geral)", f"{corners_t1['corners_ag_geral']:.2f}")
    with co3:
        st.metric("Pró (Casa)", f"{corners_t1['corners_for_home']:.2f}")
    with co4:
        st.metric("Contra (Casa)", f"{corners_t1['corners_ag_home']:.2f}")
    with co5:
        st.metric("Pró (Fora)", f"{corners_t1['corners_for_away']:.2f}")
    with co6:
        st.metric("Contra (Fora)", f"{corners_t1['corners_ag_away']:.2f}")

    st.markdown("##### 📈 Linhas Reais por Jogo (Últimas Partidas)")
    df_hist_cantos = corners_t1.get('df_historico', pd.DataFrame())
    if not df_hist_cantos.empty:
        st.dataframe(
            df_hist_cantos,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Cantos Pró": st.column_config.NumberColumn("Cantos Pró", format="%d 🚩"),
                "Cantos Contra": st.column_config.NumberColumn("Cantos Contra", format="%d 🛡️"),
                "Total na Partida": st.column_config.NumberColumn("Total na Partida", format="%d ⚽")
            }
        )
    else:
        st.info("Histórico de partidas de escanteios indisponível.")

    st.markdown("---")

    # --- MINUTAGEM DE GOLS & CARTÕES ---
    col_min1, col_min2 = st.columns(2)

    with col_min1:
        st.subheader("⏱️ Minutagem de Gols")
        df_min = stats_t1.get('df_minutagem', pd.DataFrame())
        if not df_min.empty:
            max_f = int(df_min['Gols Feitos'].max()) if not pd.isna(df_min['Gols Feitos'].max()) else 5
            max_s = int(df_min['Gols Sofridos'].max()) if not pd.isna(df_min['Gols Sofridos'].max()) else 5
            st.dataframe(
                df_min,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Gols Feitos": st.column_config.ProgressColumn("Gols Feitos", min_value=0, max_value=max(max_f, 5), format="%d ⚽"),
                    "Gols Sofridos": st.column_config.ProgressColumn("Gols Sofridos", min_value=0, max_value=max(max_s, 5), format="%d 🛡️")
                }
            )
        else:
            st.info("Dados indisponíveis.")

    with col_min2:
        st.subheader("🟨 Minutagem de Cartões")
        df_car = stats_t1.get('df_cartoes', pd.DataFrame())
        if not df_car.empty:
            max_c = int(df_car['Cartões Amarelos'].max()) if not pd.isna(df_car['Cartões Amarelos'].max()) else 5
            st.dataframe(
                df_car,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Cartões Amarelos": st.column_config.ProgressColumn("Cartões Amarelos", min_value=0, max_value=max(max_c, 5), format="%d 🟨")
                }
            )
        else:
            st.info("Dados indisponíveis.")

    st.markdown("---")

    # --- SCOUT DO PLANTEL ---
    st.subheader(f"👤 Scout do Plantel (Média Móvel U5): {time_principal}")

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
        st.warning("Não há dados de scout disponíveis para as últimas 5 partidas.")

    st.markdown("---")

    # --- SIMULADOR DE CONFRONTO DIRETO & HISTÓRICO H2H ---
    st.subheader("🤖 Simulador de Confronto Direto & H2H")
    usar_comparacao = st.checkbox("Ativar comparação e simulação contra um adversário")

    adversario = None
    if usar_comparacao:
        adversario = st.selectbox("Escolha o Time Adversário para Análise", [t for t in times_disponiveis if t != time_principal])

        if adversario:
            id_time2 = TEAM_IDS[adversario]
            stats_t2 = buscar_estatisticas_time(id_time2, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            corners_t2 = buscar_medias_escanteios(id_time2, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            df_elenco_u5_t2, _ = buscar_scout_elenco_u5(id_time2, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)

            gols_t1 = (stats_t1['gf_home'] + stats_t2['ga_away']) / 2
            gols_t2 = (stats_t2['gf_away'] + stats_t1['ga_home']) / 2
            total_gols = gols_t1 + gols_t2
            
            escanteios_jogo = (corners_t1['corners_for_home'] + corners_t2['corners_for_away']) / 2

            sc1, sc2, sc3, sc4 = st.columns(4)
            with sc1:
                st.metric(f"Expec. Gols ({time_principal})", f"{gols_t1:.2f}")
            with sc2:
                st.metric(f"Expec. Gols ({adversario})", f"{gols_t2:.2f}")
            with sc3:
                st.metric("Total de Gols Esperados", f"{total_gols:.2f}")
            with sc4:
                st.metric("Média Estimada de Cantos", f"{escanteios_jogo:.1f}")

            if total_gols >= 2.5:
                st.success(f"🔥 **Tendência:** Alta probabilidade de **Mais de 2.5 Gols**.")
            else:
                st.warning(f"🛡️ **Tendência:** Jogo truncado, tendência de **Menos de 2.5 Gols**.")

            # --- SMART TIPSTER ---
            st.markdown("---")
            st.markdown("### 💡 Smart Tipster: Sugestões de Apostas Automatizadas")
            st.caption("Dicas geradas cirurgicamente com base nos dados estatísticos cruzados da API para este confronto.")

            tip_c1, tip_c2 = st.columns(2)

            with tip_c1:
                with st.container(border=True):
                    st.markdown("#### ⚽ Mercado de Gols & Jogo")
                    if total_gols >= 2.5:
                        st.markdown(f"- **Sugestão Principal:** `Mais de 2.5 Gols` (Expec: {total_gols:.2f})")
                        st.markdown(f"- **Linha de Segurança:** `Mais de 1.5 Gols`")
                    else:
                        st.markdown(f"- **Sugestão Principal:** `Menos de 2.5 Gols` (Expec: {total_gols:.2f})")
                        st.markdown(f"- **Linha Alternativa:** `Menos de 3.5 Gols`")
                    
                    btts_check = (stats_t1['gols_feitos_media'] > 0.8) and (stats_t2['gols_feitos_media'] > 0.8)
                    if btts_check:
                        st.markdown("- **Ambas Marcam (BTTS):** `Sim` (Ambos possuem boa média ofensiva)")
                    else:
                        st.markdown("- **Ambas Marcam (BTTS):** `Não / Jogo Truncado`")

                with st.container(border=True):
                    st.markdown("#### 🚩 Mercado de Escanteios (Corners)")
                    st.markdown(f"- **Média Estimada no Jogo:** `~{escanteios_jogo:.1f} cantos`")
                    if escanteios_jogo >= 10.0:
                        st.markdown("- **Sugestão:** `Mais de 9.5 Escanteios` 🔥")
                        st.markdown("- **Linha Conservadora:** `Mais de 8.5 Escanteios`")
                    elif escanteios_jogo >= 8.5:
                        st.markdown("- **Sugestão:** `Mais de 8.5 Escanteios` ⚡")
                        st.markdown("- **Linha Conservadora:** `Mais de 7.5 Escanteios`")
                    else:
                        st.markdown("- **Sugestão:** `Menos de 10.5 Escanteios` 🛡️")

            with tip_c2:
                with st.container(border=True):
                    st.markdown("#### 🟨 Cartões & Faltas Coletivas")
                    st.markdown("- **Tendência de Disciplina:** Jogo intenso nas disputas de meio-campo.")
                    st.markdown("- **Sugestão:** `Mais de 4.5 Cartões Amarelos na Partida`")
                    st.markdown("- **Faltas:** Expectativa de alta intensidade e interrupções.")

                with st.container(border=True):
                    st.markdown("#### 🔥 Criar Aposta / Múltipla (Odd Maior)")
                    combo_gols = "Mais de 1.5 Gols" if total_gols >= 1.8 else "Menos de 3.5 Gols"
                    combo_cantos = "Mais de 7.5 Escanteios"
                    st.markdown(f"Combinando estatísticas para buscar uma **Odd Turbinada**:")
                    st.markdown(f"1. `{combo_gols}`")
                    st.markdown(f"2. `{combo_cantos}`")
                    st.markdown(f"3. `Ambos os times com pelo menos 1 escanteio em cada tempo`")
                    st.markdown(f"💡 *Gestão de banca sempre em primeiro lugar!*")

            # --- RAIO-X AVANÇADO DE PLAYER PROPS ---
            st.markdown("---")
            with st.container(border=True):
                st.markdown("#### 🎯 Raio-X Avançado de Player Props (Scout U5)")
                st.caption("Destaques individuais detalhados para finalizações, desarmes, faltas e cartões de cada equipe.")
                
                tab_p1, tab_p2 = st.tabs([f"⚽ {time_principal}", f"🛡️ {adversario}"])
                
                with tab_p1:
                    df_p = df_elenco_u5
                    if df_p is not None and not df_p.empty:
                        pp_c1, pp_c2 = st.columns(2)
                        with pp_c1:
                            st.markdown("**🎯 Top 4 Finalizadores (Chutes/Jogo):**")
                            top_fin = df_p.sort_values(by='Finalizações Média', ascending=False).head(4)
                            for _, row in top_fin.iterrows():
                                st.markdown(f"- **{row['Jogador']}**: {row['Finalizações Média']} fin. (*{row['Chutes no Alvo Média']} no alvo*)")
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.markdown("**🛡️ Top Desarmadores (Roubadas):**")
                            top_des = df_p.sort_values(by='Desarmes Média', ascending=False).head(3)
                            for _, row in top_des.iterrows():
                                st.markdown(f"- **{row['Jogador']}**: {row['Desarmes Média']} desarmes/j")
                        
                        with pp_c2:
                            st.markdown("**🟨 Mais Faltas Cometidas & Amarelos:**")
                            top_fal = df_p.sort_values(by='Faltas Cometidas Média', ascending=False).head(3)
                            for _, row in top_fal.iterrows():
                                st.markdown(f"- **{row['Jogador']}**: {row['Faltas Cometidas Média']} faltas/j | **{row['Amarelos (Total U5)']} 🟨**")
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.markdown("**⚡ Alvos (Sofrem Mais Faltas):**")
                            top_sof = df_p.sort_values(by='Faltas Sofridas Média', ascending=False).head(3)
                            for _, row in top_sof.iterrows():
                                st.markdown(f"- **{row['Jogador']}**: {row['Faltas Sofridas Média']} sofridas/j")
                    else:
                        st.info("Sem dados de scout disponíveis para este time.")

                with tab_p2:
                    df_p2 = df_elenco_u5_t2
                    if df_p2 is not None and not df_p2.empty:
                        pp_c3, pp_c4 = st.columns(2)
                        with pp_c3:
                            st.markdown("**🎯 Top 4 Finalizadores (Chutes/Jogo):**")
                            top_fin2 = df_p2.sort_values(by='Finalizações Média', ascending=False).head(4)
                            for _, row in top_fin2.iterrows():
                                st.markdown(f"- **{row['Jogador']}**: {row['Finalizações Média']} fin. (*{row['Chutes no Alvo Média']} no alvo*)")
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.markdown("**🛡️ Top Desarmadores (Roubadas):**")
                            top_des2 = df_p2.sort_values(by='Desarmes Média', ascending=False).head(3)
                            for _, row in top_des2.iterrows():
                                st.markdown(f"- **{row['Jogador']}**: {row['Desarmes Média']} desarmes/j")
                        
                        with pp_c4:
                            st.markdown("**🟨 Mais Faltas Cometidas & Amarelos:**")
                            top_fal2 = df_p2.sort_values(by='Faltas Cometidas Média', ascending=False).head(3)
                            for _, row in top_fal2.iterrows():
                                st.markdown(f"- **{row['Jogador']}**: {row['Faltas Cometidas Média']} faltas/j | **{row['Amarelos (Total U5)']} 🟨**")
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.markdown("**⚡ Alvos (Sofrem Mais Faltas):**")
                            top_sof2 = df_p2.sort_values(by='Faltas Sofridas Média', ascending=False).head(3)
                            for _, row in top_sof2.iterrows():
                                st.markdown(f"- **{row['Jogador']}**: {row['Faltas Sofridas Média']} sofridas/j")
                    else:
                        st.info("Sem dados de scout disponíveis para o time adversário.")

            st.markdown("---")
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
            corners_t2_tel = buscar_medias_escanteios(id_time2_tel, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            stats_t2_tel = buscar_estatisticas_time(id_time2_tel, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            g_t1 = (stats_t1['gf_home'] + stats_t2_tel['ga_away']) / 2
            g_t2 = (stats_t2_tel['gf_away'] + stats_t1['ga_home']) / 2
            t_gols = g_t1 + g_t2
            tend_tel = "Mais de 2.5 Gols 🔥" if t_gols >= 2.5 else "Menos de 2.5 Gols 🛡️"

            msg_telegram = f"""🚨 <b>RAIO-X PRÉ-LIVE PRO (SMART TIPSTER)</b> 🚨

⚽ <b>{time_principal} x {adversario}</b>
🏆 Competição: {opcao_liga}

📊 <b>MÉDIAS DE MANDO & ESCANTEIOS:</b>
• Cantos Pró {time_principal} (Casa): {corners_t1['corners_for_home']:.2f}
• Cantos Pró {adversario} (Fora): {corners_t2_tel['corners_for_away']:.2f}

🤖 <b>PROJEÇÃO E TENDÊNCIAS:</b>
• Expec. Gols {time_principal}: {g_t1:.2f}
• Expec. Gols {adversario}: {g_t2:.2f}
• Total Estimado: {t_gols:.2f}
• Tendência de Gols: <b>{tend_tel}</b>

📈 <i>Dica: Acesse o Painel Streamlit para conferir o Raio-X completo de Player Props e Criar Aposta!</i>"""
        else:
            msg_telegram = f"""🚨 <b>RAIO-X DO PLANTEL - PRO</b> 🚨

⚽ <b>Time: {time_principal}</b>
🏆 Competição: {opcao_liga}

📊 <b>MÉDIAS NA TEMPORADA:</b>
• Jogos Disputados: {stats_t1['jogos']}
• Média Escanteios Pró: {corners_t1['corners_for_geral']:.2f}/j
• Média Gols Feitos: {stats_t1['gols_feitos_media']:.2f}/j
• Média Gols Sofridos: {stats_t1['gols_sofridos_media']:.2f}/j

📈 <i>Dica: Acesse o Painel Streamlit para conferir o scout completo do elenco!</i>"""
        
        with st.sidebar.spinner("Enviando..."):
            sucesso = enviar_alerta_telegram(msg_telegram)
            if sucesso:
                st.sidebar.success("🎉 Alerta enviado com sucesso para o Telegram!")
