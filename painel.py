import streamlit as st
import pandas as pd
import requests
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
        return None, "Nenhum confronto recente retornado entre estas equipes."
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

# 1ª Caixinha: Time Principal
time_principal = st.sidebar.selectbox("⭐ Escolha o Time Principal", times_disponiveis)

# 2ª Caixinha: Time Adversário (para análise de confronto direto / H2H)
times_adversarios = [t for t in times_disponiveis if t != time_principal]
time_adversario = st.sidebar.selectbox("⚔️ Escolha o Time Adversário", times_adversarios if times_adversarios else times_disponiveis)

st.sidebar.markdown("---")

# --- BOTÃO DE DISPARO PARA O TELEGRAM NA BARRA LATERAL ---
if st.sidebar.button("📤 Enviar Análise para o Telegram"):
    mensagem_telegram = (
        f"⚽ <b>Painel Pro - {opcao_liga}</b>\n\n"
        f"⭐ <b>Time Principal:</b> {time_principal}\n"
        f"⚔️ <b>Adversário:</b> {time_adversario}\n"
        f"📈 <b>Média Gols Feitos:</b> {buscar_estatisticas_time(TEAM_IDS[time_principal], LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)['gols_feitos_media']:.2f}\n"
        f"🛡️ <b>Média Gols Sofridos:</b> {buscar_estatisticas_time(TEAM_IDS[time_principal], LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)['gols_sofridos_media']:.2f}\n\n"
        f"🤖 <i>Relatório gerado automaticamente pelo Painel Pro.</i>"
    )
    if enviar_alerta_telegram(mensagem_telegram):
        st.sidebar.success("✅ Análise enviada com sucesso para o Telegram!")
    else:
        st.sidebar.error("❌ Falha ao enviar para o Telegram.")

with st.spinner(f"Extraindo dados reais de {opcao_liga}..."):
    id_time1 = TEAM_IDS[time_principal]
    id_time2 = TEAM_IDS[time_adversario]
    
    stats_t1 = buscar_estatisticas_time(id_time1, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    corners_t1 = buscar_medias_escanteios(id_time1, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_elenco_u5, string_forma_t1 = buscar_scout_elenco_u5(id_time1, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_tabela = buscar_tabela_classificacao(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_arbitros = buscar_dados_arbitros(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_jogos_liga = buscar_jogos_liga(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)


# --- ABAS DE NAVEGAÇÃO SUPERIOR ---
aba_painel, aba_confronto, aba_jogos_dia, aba_arbitros, aba_tabela = st.tabs([
    "📊 Painel de Análise & Elenco", 
    "⚔️ Confronto Direto (H2H)", 
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

with aba_confronto:
    st.subheader(f"⚔️ Histórico de Confronto Direto (H2H)")
    st.markdown(f"Comparativo entre **{time_principal}** e **{time_adversario}** nas últimas temporadas:")
    
    df_h2h, erro_h2h = buscar_h2h_api(id_time1, id_time2, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    if erro_h2h:
        st.info(erro_h2h)
    elif df_h2h is not None and not df_h2h.empty:
        st.dataframe(
            df_h2h,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Nenhum histórico recente de confronto direto encontrado entre estas duas equipes.")

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
    # --- SEÇÃO 1: DESEMPENHO COLETIVO ---
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

    # --- SEÇÃO 1.1: MÉDIAS E HISTÓRICO DE ESCANTEIOS ---
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

    # --- SEÇÃO 1.2: MINUTAGEM DE GOLS & CARTÕES ---
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

    # --- SEÇÃO 2: SCOUT DO PLANTEL ---
    st.subheader(f"👤 Scout do Plantel (Média Móvel U5): {time_principal}")

    if df_elenco_u5 is not None and not df_elenco_u5.empty:
        st.dataframe(
            df_elenco_u5, 
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Dados do scout do elenco indisponíveis no momento.")
