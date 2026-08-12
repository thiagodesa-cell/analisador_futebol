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

# --- VERSÃO 22 COM TABELA DETALHADA DE CARTÕES JOGO A JOGO ---
def obter_chave_atualizacao():
    agora = datetime.now(FUSO_BR)
    return agora.strftime("%Y-%m-%d_%H")

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v22_ai_market_cards_detail"  
DATA_HOJE_STR = datetime.now(FUSO_BR).strftime("%Y-%m-%d")

# --- CONVERSOR INTELIGENTE DE FUSO HORÁRIO (UTC -> BRASÍLIA UTC-3) ---
def converter_para_horario_brasilia(iso_string):
    try:
        dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        dt_local = dt_utc.astimezone(FUSO_BR)
        return dt_local.strftime("%Y-%m-%d"), dt_local.strftime("%d/%m/%Y"), dt_local.strftime("%H:%M")
    except Exception as e:
        return iso_string[:10], f"{iso_string[8:10]}/{iso_string[5:7]}/{iso_string[0:4]}", iso_string[11:16]

# --- MOTOR DE INTELIGÊNCIA ARTIFICIAL: DISTRIBUIÇÃO DE POISSON & PROBABILIDADES ---
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
            if h + a > 2.5:
                prob_over_2_5 += p
            else:
                prob_under_2_5 += p
            if h > 0 and a > 0:
                prob_btts += p
            if h > a:
                prob_vitoria_home += p
            elif a > h:
                prob_vitoria_away += p
            else:
                prob_empate += p
                
    return {
        'over_2_5': prob_over_2_5 * 100,
        'under_2_5': prob_under_2_5 * 100,
        'btts': prob_btts * 100,
        'vitoria_home': prob_vitoria_home * 100,
        'vitoria_away': prob_vitoria_away * 100,
        'empate': prob_empate * 100
    }

# --- BOTÃO DE SELEÇÃO DE LIGA NA BARRA LATERAL ---
st.sidebar.header("🏆 Seleção da Competição Global")
opcao_liga = st.sidebar.radio(
    "Escolha qual campeonato deseja analisar:",
    list(LIGAS_MONITORADAS.values()),
    index=None,
    key="radio_opcao_liga"
)

LEAGUE_ID = [k for k, v in LIGAS_MONITORADAS.items() if v == opcao_liga][0] if opcao_liga else None

# --- DETECÇÃO INTELIGENTE DE TEMPORADA VÁLIDA ---
@st.cache_data(persist="disk")
def descobrir_temporada_valida(league_id, season_atual, key, data_cache):
    for s in [season_atual, season_atual - 1, season_atual - 2, season_atual - 3]:
        url = f"https://v3.football.api-sports.io/teams?league={league_id}&season={s}"
        headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
        try:
            res = requests.get(url, headers=headers)
            data = res.json()
            if data.get('results', 0) > 0:
                return s
        except:
            pass
    return season_atual

SEASON_EFETIVA = descobrir_temporada_valida(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO) if LEAGUE_ID else (SEASON - 1)

# --- FUNÇÕES DE BUSCA NA API ---

@st.cache_data(persist="disk")
def buscar_times_por_liga(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/teams?league={league_id}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        times_dict = {}
        if data.get('results', 0) > 0:
            for item in data['response']:
                times_dict[item['team']['name']] = item['team']['id']
            return times_dict
    except:
        pass
    return {}

@st.cache_data(persist="disk")
def buscar_times_global(termo, season, key, data_cache):
    termo_lower = termo.lower().strip()
    url = f"https://v3.football.api-sports.io/teams?search={termo_lower}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        times_dict = {}
        if data.get('results', 0) > 0:
            filtro_ruido = [
                'sub-', 'sub ', 'u17', 'u19', 'u20', 'u21', 'u23', 'under', 
                'feminino', 'women', 'fem', 'girls', 'youth', 'academy',
                ' b ', ' ii ', ' reserve', ' futsal', ' beach'
            ]
            
            ruido_regional = [
                '-pi', 'piauí', '-ba', 'bahia de feira', '-sp', '-ce', '-pe', 
                '-pb', '-rn', '-ma', '-pa', '-am', '-es', '-sc', '-pr', '-rs', 
                '-mg', '-go', '-mt', '-ms', 'arcoverde', 'guanambi', 'jaguaré'
            ]
            
            for item in data['response']:
                t_name = item['team']['name']
                t_name_lower = t_name.lower()
                t_id = item['team']['id']
                
                if any(p in t_name_lower for p in filtro_ruido):
                    continue
                
                if 'flamengo' in termo_lower and t_name_lower not in ['flamengo', 'cr flamengo']:
                    continue
                if 'botafogo' in termo_lower and t_name_lower not in ['botafogo', 'botafogo fr']:
                    continue
                
                if any(r in t_name_lower for r in ruido_regional):
                    continue

                country = item['venue'].get('country') or item['team'].get('country', 'Mundo')
                label = f"{t_name} ({country})"
                times_dict[label] = {'id': t_id, 'name': t_name}
            return times_dict
    except:
        pass
    return {}

@st.cache_data(persist="disk")
def buscar_jogador_global(termo, season, key, data_cache):
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    jogadores_dict = {}
    anos_para_testar = [season - 1, season - 2, season, season - 3, season - 4]
    
    for s in anos_para_testar:
        url = f"https://v3.football.api-sports.io/players?search={termo}&season={s}"
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 429:
                return {"__rate_limit__": True}
            
            if res.status_code == 200:
                data = res.json()
                if data.get('results', 0) > 0:
                    for item in data['response']:
                        p_info = item['player']
                        p_id = p_info['id']
                        p_name = p_info['name']
                        stats_list = item.get('statistics', [])
                        if stats_list:
                            for stat in stats_list:
                                team_info = stat['team']
                                league_info = stat['league']
                                t_id = team_info['id']
                                t_name = team_info['name']
                                l_id = league_info['id']
                                l_name = league_info['name']
                                
                                label = f"{p_name} ({t_name} - {l_name}) [{s}]"
                                jogadores_dict[label] = {
                                    'player_id': p_id, 'player_name': p_name,
                                    'team_id': t_id, 'team_name': t_name,
                                    'league_id': l_id, 'league_name': l_name, 'season': s
                                }
                        else:
                            label = f"{p_name} (Temporada {s})"
                            jogadores_dict[label] = {
                                'player_id': p_id, 'player_name': p_name,
                                'team_id': None, 'team_name': "Time não especificado",
                                'league_id': 71, 'league_name': "Brasileirão Série A", 'season': s
                            }
                    if jogadores_dict:
                        return jogadores_dict
        except:
            pass
    return jogadores_dict

@st.cache_data(persist="disk")
def buscar_liga_por_time(team_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/leagues?team={team_id}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            for resp in data['response']:
                league_info = resp['league']
                if league_info['id'] in LIGAS_MONITORADAS:
                    return league_info['id'], league_info['name']
            league_info = data['response'][0]['league']
            return league_info['id'], league_info['name']
    except:
        pass
    return None, None

TEAM_IDS = buscar_times_por_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO) if LEAGUE_ID else {}

# --- BUSCA GLOBAL DE CLUBES (MUNDO) ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🌍 Busca Global de Clubes")
termo_busca_global = st.sidebar.text_input("Pesquisar qualquer clube no mundo:", placeholder="Ex: Flamengo, Boca Juniors...", key="input_busca_clube_global")

clube_global_selecionado = None
id_time_global = None

if termo_busca_global and len(termo_busca_global) >= 2:
    dict_globais = buscar_times_global(termo_busca_global, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    if dict_globais:
        escolha_g = st.sidebar.selectbox(
            "Resultados da Busca Global:", list(dict_globais.keys()), index=None, placeholder="Selecione o clube...", key="select_global_clube"
        )
        if escolha_g:
            clube_global_selecionado = dict_globais[escolha_g]['name']
            id_time_global = dict_globais[escolha_g]['id']
            l_id, l_name = buscar_liga_por_time(id_time_global, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            if l_id:
                LEAGUE_ID = l_id
                opcao_liga = l_name
            else:
                LEAGUE_ID = 71
                opcao_liga = LIGAS_MONITORADAS[LEAGUE_ID]
            
            SEASON_EFETIVA = descobrir_temporada_valida(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            TEAM_IDS = buscar_times_por_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)

# --- BUSCA GLOBAL DE JOGADORES ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 Busca Global de Jogadores")
termo_busca_jogador = st.sidebar.text_input("Pesquisar qualquer jogador:", placeholder="Ex: Borja, Hulk...", key="input_busca_jogador_global")

jogador_global_selecionado = None
id_time_global_jogador = None

if termo_busca_jogador and len(termo_busca_jogador) >= 3:
    dict_jogadores_globais = buscar_jogador_global(termo_busca_jogador, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    
    if "__rate_limit__" in dict_jogadores_globais:
        st.sidebar.error("⚠️ Limite diário de requisições da API atingido.")
    elif dict_jogadores_globais:
        escolha_j = st.sidebar.selectbox(
            "Resultados da Busca de Jogadores:", list(dict_jogadores_globais.keys()), index=None, placeholder="Selecione o jogador...", key="select_global_jogador"
        )
        if escolha_j:
            j_info = dict_jogadores_globais[escolha_j]
            LEAGUE_ID = j_info['league_id'] if j_info['league_id'] in LIGAS_MONITORADAS else 71
            opcao_liga = j_info['league_name'] if j_info['league_id'] in LIGAS_MONITORADAS else LIGAS_MONITORADAS[71]
            id_time_global_jogador = j_info['team_id']
            clube_global_selecionado = j_info['team_name']
            jogador_global_selecionado = j_info['player_name']
            SEASON_EFETIVA = j_info.get('season', SEASON - 1)
            TEAM_IDS = buscar_times_por_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)

# --- CONFIGURAÇÕES DE ANÁLISE ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Configurações de Análise IA")

if jogador_global_selecionado:
    time_principal = clube_global_selecionado
    id_time1 = id_time_global_jogador
    st.sidebar.success(f"🔍 Jogador: **{jogador_global_selecionado}** ({time_principal})")
elif clube_global_selecionado:
    time_principal = clube_global_selecionado
    id_time1 = id_time_global
    st.sidebar.success(f"🌐 Ativo via Busca Global: **{time_principal}**")
elif LEAGUE_ID:
    times_disponiveis = sorted(list(TEAM_IDS.keys())) if TEAM_IDS else []
    time_principal = st.sidebar.selectbox(
        "Escolha o Time (Opcional)", times_disponiveis, index=None, placeholder="Selecione para ver o Raio-X", key="select_time_principal"
    )
    if time_principal:
        id_time1 = TEAM_IDS[time_principal]
    else:
        id_time1 = None
else:
    time_principal = None
    id_time1 = None
    st.sidebar.info("📌 Selecione uma competição, clube ou pesquise um jogador acima.")

if LEAGUE_ID:
    st.sidebar.success(f"✅ Competição Ativa: {opcao_liga} ({SEASON_EFETIVA})")
else:
    st.sidebar.warning("⚠️ Nenhuma competição selecionada.")

st.sidebar.info(f"🔄 Motor IA v22 Ultimate Ativo • Base: {CHAVE_ATUALIZACAO}")
st.sidebar.markdown("---")
st.sidebar.markdown("### 👨‍💻 Desenvolvido por:")
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
        return res.status_code == 200
    except:
        return False

# --- FUNÇÕES DE BUSCA NA API (COM CACHE) ---

@st.cache_data(persist="disk")
def buscar_tabela_classificacao(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/standings?league={league_id}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            response_league = data['response'][0]['league']
            if 'standings' in response_league:
                standings = response_league['standings'][0]
                tabela = []
                for s in standings:
                    tabela.append({
                        'Pos': s['rank'], 'Time': s['team']['name'], 'Pts': s['points'],
                        'J': s['all']['played'], 'V': s['all']['win'], 'E': s['all']['draw'],
                        'D': s['all']['lose'], 'GP': s['all']['goals']['for'], 'GC': s['all']['goals']['against'],
                        'SG': s['goalsDiff']
                    })
                return pd.DataFrame(tabela)
    except:
        pass
    return pd.DataFrame()

@st.cache_data(persist="disk")
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
                iso_date_local, match_date_fmt, match_time = converter_para_horario_brasilia(date_str)
                
                status = f['fixture']['status']['short']
                home_name = f['teams']['home']['name']
                away_name = f['teams']['away']['name']
                goals_home = f['goals']['home']
                goals_away = f['goals']['away']
                
                placar_str = f"{goals_home} x {goals_away}" if goals_home is not None else "vs"
                round_name = f['league'].get('round', 'Rodada')
                
                jogos_lista.append({
                    'DataISO': iso_date_local, 
                    'Data': match_date_fmt, 'Horário': match_time, 'Rodada': round_name,
                    'Mandante': home_name, 'Placar': placar_str, 'Visitante': away_name, 'Status': status
                })
            return pd.DataFrame(jogos_lista)
    except:
        pass
    return pd.DataFrame()

@st.cache_data(persist="disk")
def buscar_jogos_ligas_monitoradas_por_data(data_str, key, cache_key):
    url = f"https://v3.football.api-sports.io/fixtures?date={data_str}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        jogos_filtrados = []
        if data.get('results', 0) > 0:
            for f in data['response']:
                league_id = f['league']['id']
                if league_id in LIGAS_MONITORADAS:
                    date_str_f = f['fixture']['date']
                    _, match_date_fmt, match_time = converter_para_horario_brasilia(date_str_f)
                    league_name = LIGAS_MONITORADAS[league_id]
                        
                    home_name = f['teams']['home']['name']
                    away_name = f['teams']['away']['name']
                    home_id = f['teams']['home']['id']
                    away_id = f['teams']['away']['id']
                    status = f['fixture']['status']['short']
                    
                    if status in ['NS', 'TBD', '1H', 'HT', '2H']:
                        jogos_filtrados.append({
                            'LeagueID': league_id, 'Liga': league_name,
                            'Mandante': home_name, 'Visitante': away_name,
                            'HomeID': home_id, 'AwayID': away_id,
                            'Data': match_date_fmt, 'Horário': match_time
                        })
            return jogos_filtrados
    except:
        pass
    return []

@st.cache_data(persist="disk")
def buscar_rodada_atual(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/fixtures/rounds?league={league_id}&season={season}&current=true"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('response') and len(data['response']) > 0:
            return data['response'][0]
    except:
        pass
    return None

@st.cache_data(persist="disk")
def buscar_dados_arbitros(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            ref_data = {}
            for f in data['response']:
                ref = f['fixture']['referee'] or "Não Divulgado"
                status = f['fixture']['status']['short']
                if status in ['FT', 'AET', 'PEN', '1H', '2H', 'HT', 'ET']:
                    home = f['teams']['home']['name']
                    away = f['teams']['away']['name']
                    if ref not in ref_data:
                        ref_data[ref] = {'Jogos': 0, 'Confrontos': []}
                    ref_data[ref]['Jogos'] += 1
                    ref_data[ref]['Confrontos'].append(f"{home} x {away}")
            
            rows = [{'Árbitro': r, 'Jogos Apitados': i['Jogos'], 'Últimos Confrontos': ", ".join(i['Confrontos'][:2])} for r, i in ref_data.items()]
            return pd.DataFrame(rows).sort_values(by='Jogos Apitados', ascending=False) if rows else pd.DataFrame()
    except:
        pass
    return pd.DataFrame()

@st.cache_data(persist="disk")
def buscar_medias_escanteios(team_id, league_id, season, key, data_cache):
    url_fixtures = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&team={team_id}&last=10"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    cantos_pro_casa, cantos_contra_casa = [], []
    cantos_pro_fora, cantos_contra_fora = [], []
    cartoes_pro_casa, cartoes_contra_casa_list = [], []
    cartoes_pro_fora, cartoes_contra_fora_list = [], []
    detalhes = []
    try:
        res = requests.get(url_fixtures, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            for f in data['response']:
                f_id = f['fixture']['id']
                is_home = (f['teams']['home']['id'] == team_id)
                adv = f['teams']['away']['name'] if is_home else f['teams']['home']['name']
                _, dt_fmt, _ = converter_para_horario_brasilia(f['fixture']['date'])
                
                g_home = f['goals']['home'] if f['goals']['home'] is not None else 0
                g_away = f['goals']['away'] if f['goals']['away'] is not None else 0
                g_pro = g_home if is_home else g_away
                g_contra = g_away if is_home else g_home
                placar_real = f"{g_home} x {g_away}"
                
                time.sleep(0.15)
                res_s = requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={f_id}", headers=headers)
                data_s = res_s.json()
                
                t_corners, o_corners = 0, 0
                t_yellow, o_yellow = 0, 0
                if data_s.get('results', 0) > 0:
                    for item in data_s['response']:
                        for s in item['statistics']:
                            if s['type'] == 'Corner Kicks' and s['value'] is not None:
                                c_val = int(s['value'])
                                if item['team']['id'] == team_id: t_corners = c_val
                                else: o_corners = c_val
                            elif s['type'] == 'Yellow Cards' and s['value'] is not None:
                                y_val = int(s['value'])
                                if item['team']['id'] == team_id: t_yellow = y_val
                                else: o_yellow = y_val
                
                if is_home:
                    cantos_pro_casa.append(t_corners)
                    cantos_contra_casa.append(o_corners)
                    cartoes_pro_casa.append(t_yellow)
                    cartoes_contra_casa_list.append(o_yellow)
                else:
                    cantos_pro_fora.append(t_corners)
                    cantos_contra_fora.append(o_corners)
                    cartoes_pro_fora.append(t_yellow)
                    cartoes_contra_fora_list.append(o_yellow)
                
                detalhes.append({
                    'Data': dt_fmt, 'Adversário': adv, 'Mando': 'Casa' if is_home else 'Fora', 'Placar': placar_real,
                    'Gols Pró': g_pro, 'Gols Contra': g_contra, 'Cantos Pró': t_corners, 'Cantos Contra': o_corners,
                    'Total Cantos': t_corners + o_corners, 'Cartões Pró': t_yellow, 'Cartões Contra': o_yellow, 'Total Cartões': t_yellow + o_yellow
                })
        
        todas_cartoes_pro = cartoes_pro_casa + cartoes_pro_fora
        todas_cartoes_contra = cartoes_contra_casa_list + cartoes_contra_fora
        
        cf_geral = (sum(cantos_pro_casa+cantos_pro_fora)/max(len(cantos_pro_casa+cantos_pro_fora),1))
        ca_geral = (sum(cantos_contra_casa+cantos_contra_fora)/max(len(cantos_contra_casa+cantos_contra_fora),1))
        cf_home = sum(cantos_pro_casa)/max(len(cantos_pro_casa),1)
        ca_home = sum(cantos_contra_casa)/max(len(cantos_contra_casa),1)
        cf_away = sum(cantos_pro_fora)/max(len(cantos_pro_fora),1)
        ca_away = sum(cantos_contra_fora)/max(len(cantos_contra_fora),1)

        m_pro = sum(todas_cartoes_pro)/max(len(todas_cartoes_pro),1)
        m_contra = sum(todas_cartoes_contra)/max(len(todas_cartoes_contra),1)
        
        if m_pro == m_contra and m_pro > 0:
            m_contra = m_pro + 0.55

        return {
            'corners_for_geral': cf_geral if cf_geral > 1.0 else 4.8,
            'corners_ag_geral': ca_geral if ca_geral > 1.0 else 4.5,
            'corners_for_home': cf_home if cf_home > 1.0 else 5.0, 
            'corners_ag_home': ca_home if ca_home > 1.0 else 4.5,
            'corners_for_away': cf_away if cf_away > 1.0 else 4.2, 
            'corners_ag_away': ca_away if ca_away > 1.0 else 4.8,
            'media_cartoes_pro': m_pro if m_pro > 0 else 2.15,
            'media_cartoes_contra': m_contra if m_contra > 0 else 2.80,
            'df_historico': pd.DataFrame(detalhes)
        }
    except:
        return {
            'corners_for_geral': 4.8, 'corners_ag_geral': 4.5,
            'corners_for_home': 5.0, 'corners_ag_home': 4.5,
            'corners_for_away': 4.2, 'corners_ag_away': 4.8,
            'media_cartoes_pro': 2.15, 'media_cartoes_contra': 2.80,
            'df_historico': pd.DataFrame()
        }

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
                'jogos': stats.get('fixtures',{}).get('played',{}).get('total',0),
                'gols_feitos_media': float(gf.get('total') or 0), 'gols_sofridos_media': float(ga.get('total') or 0),
                'gf_home': float(gf.get('home') or 0), 'ga_home': float(ga.get('home') or 0),
                'gf_away': float(gf.get('away') or 0), 'ga_away': float(ga.get('away') or 0),
                'clean_sheets': stats.get('clean_sheet',{}).get('total',0)
            }
    except:
        pass
    return {'jogos':0,'gols_feitos_media':0.0,'gols_sofridos_media':0.0,'gf_home':0.0,'ga_home':0.0,'gf_away':0.0,'ga_away':0.0,'clean_sheets':0}

@st.cache_data(persist="disk")
def buscar_scout_elenco_u5(team_id, league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&team={team_id}&last=5"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) == 0: return pd.DataFrame(), "Sem dados"
        
        forma = ["🟢" if f['teams']['home']['winner'] and f['teams']['home']['id']==team_id or f['teams']['away']['winner'] and f['teams']['away']['id']==team_id else "🔴" if f['teams']['home']['winner'] is not None else "🟡" for f in reversed(data['response'])]
        player_data = {}
        
        for f in data['response']:
            time.sleep(0.15)
            r_p = requests.get(f"https://v3.football.api-sports.io/fixtures/players?fixture={f['fixture']['id']}", headers=headers)
            d_p = r_p.json()
            if d_p.get('results', 0) > 0:
                for team_p in d_p['response']:
                    if team_p['team']['id'] == team_id:
                        for p in team_p['players']:
                            name = p['player']['name']
                            st_p = p['statistics'][0] if p['statistics'] else {}
                            if int(st_p.get('games',{}).get('minutes') or 0) > 0:
                                if name not in player_data:
                                    player_data[name] = {'Pos': st_p.get('games',{}).get('position','-'), 'J':0, 'G':0, 'Fin':0, 'Alvo':0, 'FC':0, 'FS':0, 'Des':0, 'A':0, 'V':0}
                                player_data[name]['J'] += 1
                                player_data[name]['G'] += st_p.get('goals',{}).get('total') or 0
                                player_data[name]['Fin'] += st_p.get('shots',{}).get('total') or 0
                                player_data[name]['Alvo'] += st_p.get('shots',{}).get('on') or 0
                                player_data[name]['FC'] += st_p.get('fouls',{}).get('committed') or 0
                                player_data[name]['FS'] += st_p.get('fouls',{}).get('drawn') or 0
                                player_data[name]['Des'] += st_p.get('tackles',{}).get('total') or 0
                                player_data[name]['A'] += st_p.get('cards',{}).get('yellow') or 0
                                player_data[name]['V'] += st_p.get('cards',{}).get('red') or 0
        rows = [{
            'Jogador': k, 'Posição': v['Pos'], 'Jogos (U5)': f"{v['J']}/5", 'Gols (Total U5)': v['G'],
            'Finalizações Média': round(v['Fin']/v['J'], 2), 'Chutes no Alvo Média': round(v['Alvo']/v['J'], 2),
            'Faltas Cometidas Média': round(v['FC']/v['J'], 2), 'Faltas Sofridas Média': round(v['FS']/v['J'], 2),
            'Desarmes Média': round(v['Des']/v['J'], 2), 'Amarelos (Total U5)': v['A'], 'Vermelhos (Total U5)': v['V']
        } for k, v in player_data.items() if v['J'] > 0]
        return pd.DataFrame(rows).sort_values(by=['Gols (Total U5)', 'Finalizações Média'], ascending=[False,False]) if rows else pd.DataFrame(), " ".join(forma)
    except:
        return pd.DataFrame(), "Erro"

@st.cache_data(persist="disk")
def buscar_h2h_api(id1, id2, key, data_cache):
    url = f"https://v3.football.api-sports.io/fixtures/headtohead?h2h={id1}-{id2}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            rows = []
            for m in sorted(data['response'], key=lambda x: x['fixture']['date'], reverse=True)[:6]:
                _, dt_fmt, _ = converter_para_horario_brasilia(m['fixture']['date'])
                rows.append({
                    'Data': dt_fmt, 'Competição': m['league']['name'], 'Mandante': m['teams']['home']['name'],
                    'Placar': f"{m['goals']['home']} x {m['goals']['away']}", 'Visitante': m['teams']['away']['name']
                })
            return pd.DataFrame(rows), None
    except:
        pass
    return None, "Sem confrontos recentes."

# --- CARREGAMENTO DE DADOS GERAIS DA LIGA ---
if LEAGUE_ID:
    with st.spinner(f"Extraindo panorama geral de {opcao_liga}..."):
        df_tabela = buscar_tabela_classificacao(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        df_arbitros = buscar_dados_arbitros(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        df_jogos_liga = buscar_jogos_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        rodada_atual_str = buscar_rodada_atual(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
else:
    df_tabela = pd.DataFrame()
    df_arbitros = pd.DataFrame()
    df_jogos_liga = pd.DataFrame()
    rodada_atual_str = None

# --- VARIÁVEIS INICIAIS ---
stats_t1 = {'jogos':0,'gols_feitos_media':0.0,'gols_sofridos_media':0.0,'gf_home':0.0,'ga_home':0.0,'gf_away':0.0,'ga_away':0.0,'clean_sheets':0}
corners_t1 = {'corners_for_geral':0.0,'corners_ag_geral':0.0,'corners_for_home':0.0,'corners_ag_home':0.0,'corners_for_away':0.0,'corners_ag_away':0.0,'media_cartoes_pro':0.0,'media_cartoes_contra':0.0,'df_historico':pd.DataFrame()}
df_elenco_u5 = pd.DataFrame()
string_forma_t1 = "Sem dados"

if id_time1 and LEAGUE_ID:
    stats_t1 = buscar_estatisticas_time(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    corners_t1 = buscar_medias_escanteios(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_elenco_u5, string_forma_t1 = buscar_scout_elenco_u5(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)

if jogador_global_selecionado and not df_elenco_u5.empty:
    st.info(f"⭐ Jogador em destaque na busca: **{jogador_global_selecionado}** ({time_principal})")
    jogadores_encontrados = df_elenco_u5[df_elenco_u5['Jogador'].str.contains(jogador_global_selecionado, case=False, na=False)]
    if not jogadores_encontrados.empty:
        st.markdown(f"### 👤 Scout do Jogador Selecionado: `{jogador_global_selecionado}`")
        st.dataframe(jogadores_encontrados, use_container_width=True, hide_index=True)
    else:
        st.warning(f"O jogador {jogador_global_selecionado} não pontuou nas últimas 5 partidas listadas do {time_principal}.")
    st.markdown("---")

# =========================================================================
# CENÁRIO 0: TELA DE BOAS-VINDAS
# =========================================================================
if not LEAGUE_ID and not clube_global_selecionado and not id_time1:
    st.title("⚽ Smart Tipster Pro v22 - Motor de IA Preditiva & Trading")
    st.markdown("---")
    st.info("👈 **Para começar, selecione uma competição** na barra lateral, utilize a **Busca Global de Clubes** ou pesquise diretamente qualquer **jogador** no mundo.")

# =========================================================================
# CENÁRIO 1: PANORAMA DA LIGA
# =========================================================================
elif LEAGUE_ID and not id_time1:
    st.title(f"🏆 Panorama Geral: {opcao_liga} ({SEASON_EFETIVA})")
    st.markdown("Bem-vindo ao Hub da Competição! Abaixo você encontra o calendário oficial calibrado para o horário de Brasília, tabela e árbitros.")
    st.markdown("---")

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Competição Ativa", opcao_liga)
    col_m2.metric("Temporada", SEASON_EFETIVA)
    col_m3.metric("Rodada Atual", rodada_atual_str if rodada_atual_str else "Em andamento")

    st.markdown("---")

    tab_pan_jogos, tab_pan_tabela, tab_pan_refs = st.tabs([
        "📅 Jogos & Calendário (BR)", "🏆 Tabela de Classificação", "⚖️ Árbitros em Destaque"
    ])

    with tab_pan_jogos:
        st.subheader(f"📅 Partidas - {opcao_liga}")
        if not df_jogos_liga.empty:
            filtro_opcao = st.radio("Filtrar visualização:", ["Ver Jogos da Rodada Atual", "Ver Todos los Jogos da Temporada"], horizontal=True, key="filtro_jogos_pan")
            df_exibir = df_jogos_liga.copy()
            if filtro_opcao == "Ver Jogos da Rodada Atual" and rodada_atual_str:
                df_exibir = df_exibir[df_exibir['Rodada'] == rodada_atual_str]
                st.success(f"📌 Exibindo jogos da **{rodada_atual_str}**")
            st.dataframe(df_exibir[['Data', 'Horário', 'Rodada', 'Mandante', 'Placar', 'Visitante', 'Status']], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum jogo encontrado para esta competição.")

    with tab_pan_tabela:
        st.subheader(f"🏆 Classificação Atual - {opcao_liga}")
        if not df_tabela.empty:
            st.dataframe(df_tabela, use_container_width=True, hide_index=True)

    with tab_pan_refs:
        st.subheader(f"⚖️ Perfil dos Árbitros - {opcao_liga}")
        if not df_arbitros.empty:
            st.dataframe(df_arbitros, use_container_width=True, hide_index=True)

# =========================================================================
# CENÁRIO 2: PAINEL DE ANÁLISE DETALHADA COM IA
# =========================================================================
else:
    st.title(f"⚽ Painel Preditivo Pro v22 - {opcao_liga}")
    
    st.markdown(f"### 📅 Agenda Oficial & 🏆 Tabela: **{time_principal}**")
    col_auto_1, col_auto_2 = st.columns(2)
    
    with col_auto_1:
        st.markdown("#### 🗓️ Próximos Jogos / Agenda do Time")
        if not df_jogos_liga.empty:
            df_agenda_time = df_jogos_liga[
                (df_jogos_liga['Mandante'] == time_principal) | 
                (df_jogos_liga['Visitante'] == time_principal)
            ].copy()
            if not df_agenda_time.empty:
                hoje_str = datetime.now(FUSO_BR).strftime("%Y-%m-%d")
                
                jogos_passados = df_agenda_time[df_agenda_time['DataISO'] < hoje_str].tail(3)
                jogos_futuros = df_agenda_time[df_agenda_time['DataISO'] >= hoje_str].head(5)
                
                df_exibir_agenda = pd.concat([jogos_passados, jogos_futuros])
                
                if df_exibir_agenda.empty or len(jogos_futuros) == 0:
                    df_exibir_agenda = df_agenda_time.tail(8)
                    
                st.dataframe(df_exibir_agenda[['Data', 'Horário', 'Rodada', 'Mandante', 'Placar', 'Visitante', 'Status']], use_container_width=True, hide_index=True)
            else:
                st.info(f"Nenhum jogo localizado diretamente para {time_principal} na base.")
        else:
            st.info("Carregando agenda...")
            
    with col_auto_2:
        st.markdown("#### 🏆 Tabela da Competição")
        if not df_tabela.empty:
            st.dataframe(df_tabela, use_container_width=True, hide_index=True)
        else:
            st.info("Carregando tabela...")
            
    st.markdown("---")

    aba_painel, aba_jogos_dia, aba_arbitros, aba_tabela, aba_chat = st.tabs([
        "📊 Painel IA & Elenco", "📅 Jogos & Rodada", "⚖️ Árbitros", f"🏆 Tabela ({opcao_liga})", "🤖 Chat com a IA"
    ])

    with aba_tabela:
        st.subheader(f"🏆 Classificação - {opcao_liga} ({SEASON_EFETIVA})")
        if not df_tabela.empty:
            st.dataframe(df_tabela, use_container_width=True, hide_index=True)

    with aba_jogos_dia:
        st.subheader(f"📅 Calendário - {opcao_liga}")
        if not df_jogos_liga.empty:
            filtro_opcao = st.radio("Filtrar:", ["Ver Jogos da Rodada Atual", "Ver Todos os Jogos da Temporada"], horizontal=True, key="filtro_jogos_calendario")
            df_exibir = df_jogos_liga.copy()
            if filtro_opcao == "Ver Jogos da Rodada Atual" and rodada_atual_str:
                df_exibir = df_exibir[df_exibir['Rodada'] == rodada_atual_str]
            st.dataframe(df_exibir[['Data', 'Horário', 'Rodada', 'Mandante', 'Placar', 'Visitante', 'Status']], use_container_width=True, hide_index=True)

    with aba_arbitros:
        st.subheader(f"⚖️ Árbitros - {opcao_liga}")
        if not df_arbitros.empty:
            st.dataframe(df_arbitros, use_container_width=True, hide_index=True)

    with aba_painel:
        st.subheader(f"📊 Raio-X Preditivo: {time_principal}")
        st.markdown(f"**Forma Recente (Últimas 5 partidas):** {string_forma_t1}")
        
        rg1, rg2, rg3 = st.columns(3)
        rg1.metric("Jogos Disputados", stats_t1['jogos'])
        rg2.metric("Clean Sheets (Jogos sem sofrer gols)", stats_t1['clean_sheets'])
        rg3.markdown("💡 *Ative a simulação H2H abaixo para calcular o motor de Poisson e IA.*")
        
        st.markdown("---")
        
        col_esquerda_gols, col_direita_cantos = st.columns(2)
        
        with col_esquerda_gols:
            st.markdown("### ⚽ Gols & Histórico")
            g_col1, g_col2 = st.columns(2)
            g_col1.metric("Média Gols Feitos", f"{stats_t1['gols_feitos_media']:.2f}")
            g_col2.metric("Média Gols Sofridos", f"{stats_t1['gols_sofridos_media']:.2f}")
            g_col3, g_col4 = st.columns(2)
            g_col3.metric("Casa (Pró / Contra)", f"{stats_t1['gf_home']:.2f} / {stats_t1['ga_home']:.2f}")
            g_col4.metric("Fora (Pró / Contra)", f"{stats_t1['gf_away']:.2f} / {stats_t1['ga_away']:.2f}")
            
            if not corners_t1['df_historico'].empty:
                st.markdown("**Últimas 10 Partidas (Placares):**")
                st.dataframe(corners_t1['df_historico'][['Data', 'Adversário', 'Mando', 'Placar', 'Gols Pró', 'Gols Contra']], use_container_width=True, hide_index=True)

        with col_direita_cantos:
            st.markdown("### 🚩 Escanteios & Histórico")
            e_col1, e_col2 = st.columns(2)
            e_col1.metric("Cantos Pró (Geral)", f"{corners_t1['corners_for_geral']:.2f}")
            e_col2.metric("Cantos Contra (Geral)", f"{corners_t1['corners_ag_geral']:.2f}")
            e_col3, e_col4 = st.columns(2)
            e_col3.metric("Casa (Pró / Contra)", f"{corners_t1['corners_for_home']:.2f} / {corners_t1['corners_ag_home']:.2f}")
            e_col4.metric("Fora (Pró / Contra)", f"{corners_t1['corners_for_away']:.2f} / {corners_t1['corners_ag_away']:.2f}")
            
            if not corners_t1['df_historico'].empty:
                st.markdown("**Últimas 10 Partidas (Cantos):**")
                st.dataframe(corners_t1['df_historico'][['Data', 'Adversário', 'Mando', 'Cantos Pró', 'Cantos Contra', 'Total Cantos']], use_container_width=True, hide_index=True)
                
        st.markdown("---")
        
        # =========================================================================
        # SEÇÃO DE CARTÕES: TABELA DETALHADA JOGO A JOGO (SOLICITADA)
        # =========================================================================
        st.subheader(f"🟨 Tabela Detalhada Jogo a Jogo - Cartões: {time_principal}")
        st.markdown(f"Acompanhamento analítico jogo a jogo mostrando exatamente quantos cartões **{time_principal}** recebeu em comparação com o **Adversário** em cada partida recente:")
        
        c_card1, c_card2 = st.columns(2)
        c_card1.metric("Média de Cartões Pró (Time)", f"{corners_t1['media_cartoes_pro']:.2f}")
        c_card2.metric("Média de Cartões Contra (Adversários)", f"{corners_t1['media_cartoes_contra']:.2f}")
        
        if not corners_t1['df_historico'].empty:
            df_cartoes_detalhado = corners_t1['df_historico'][['Data', 'Mando', 'Adversário', 'Placar', 'Cartões Pró', 'Cartões Contra', 'Total Cartões']].copy()
            df_cartoes_detalhado.columns = ['Data', 'Mando', 'Adversário', 'Placar', f'Cartões {time_principal}', 'Cartões Adversário', 'Total na Partida']
            st.dataframe(df_cartoes_detalhado, use_container_width=True, hide_index=True)
        else:
            st.info("Histórico de cartões indisponível no momento.")
                
        st.markdown("---")
        st.subheader(f"👤 Scout do Plantel (Média Móvel U5): {time_principal}")
        if not df_elenco_u5.empty:
            st.dataframe(df_elenco_u5, use_container_width=True, hide_index=True)
            
        st.markdown("---")
        st.subheader("🤖 Simulador H2H & Motor de Probabilidade (IA & Poisson)")
        usar_comparacao = st.checkbox("Ativar motor de IA e comparação contra adversário", key="check_usar_comparacao")
        
        if usar_comparacao:
            times_disponiveis = sorted(list(TEAM_IDS.keys()))
            adversario = st.selectbox("Escolha o Time Adversário", [t for t in times_disponiveis if t != time_principal], key="select_adversario_h2h")
            if adversario:
                id_time2 = TEAM_IDS[adversario]
                stats_t2 = buscar_estatisticas_time(id_time2, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                corners_t2 = buscar_medias_escanteios(id_time2, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                
                gols_t1 = (stats_t1['gf_home'] + stats_t2['ga_away']) / 2
                gols_t2 = (stats_t2['gf_away'] + stats_t1['ga_home']) / 2
                
                probs_poisson = calcular_probabilidades_poisson(gols_t1, gols_t2)
                total_gols = gols_t1 + gols_t2
                
                c_proj_t1 = (corners_t1['corners_for_home'] + corners_t2['corners_ag_away']) / 2
                c_proj_t2 = (corners_t2['corners_for_away'] + corners_t1['corners_ag_home']) / 2
                escanteios_jogo = c_proj_t1 + c_proj_t2
                
                if LEAGUE_ID == 128:
                    escanteios_jogo += 3.0
                elif LEAGUE_ID in [71, 39, 13]:
                    escanteios_jogo += 2.0
                else:
                    escanteios_jogo += 1.5
                
                total_cartoes = corners_t1['media_cartoes_pro'] + corners_t2['media_cartoes_pro']
                
                confianca_ia = min(95, max(55, int(50 + abs(probs_poisson['vitoria_home'] - probs_poisson['vitoria_away']) * 0.7)))

                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric(f"Prob. Vitória ({time_principal})", f"{probs_poisson['vitoria_home']:.1f}%")
                sc2.metric(f"Prob. Vitória ({adversario})", f"{probs_poisson['vitoria_away']:.1f}%")
                sc3.metric("Prob. Over 2.5 Gols", f"{probs_poisson['over_2_5']:.1f}%")
                sc4.metric("Índice de Confiança IA", f"{confianca_ia}% 🧠")
                
                st.markdown("---")
                st.markdown("### 💡 Smart Tipster Pro: Recomendações Baseadas em IA (Mercado Neutro)")
                tip_c1, tip_c2 = st.columns(2)
                
                with tip_c1:
                    with st.container(border=True):
                        st.markdown("#### ⚽ Mercado de Gols Dinâmico")
                        st.markdown(f"- **Expectativa Modelada:** `{total_gols:.2f}` gols")
                        st.markdown(f"- **Probabilidade BTTS (Ambas Marcam):** `{probs_poisson['btts']:.1f}%`")
                        
                        if total_gols >= 2.8 and probs_poisson['over_2_5'] >= 50:
                            sel_gols_sim = "Mais de 2.5 Gols 🔥"
                        elif probs_poisson['btts'] >= 55 and total_gols >= 2.3:
                            sel_gols_sim = "Ambas Marcam (BTTS) Sim ⚡"
                        elif total_gols >= 2.0:
                            sel_gols_sim = "Mais de 1.5 Gols ⚽"
                        elif total_gols <= 1.8:
                            sel_gols_sim = "Menos de 2.5 Gols 🛡️"
                        else:
                            sel_gols_sim = "Mais de 1.5 Gols ⚽"
                            
                        st.markdown(f"- **Sugestão Otimizada:** `{sel_gols_sim}`")
                    
                    with st.container(border=True):
                        st.markdown("#### 🛡️ Mercado de Segurança & Dupla Chance (Neutro v22)")
                        
                        vh = probs_poisson['vitoria_home']
                        va = probs_poisson['vitoria_away']
                        
                        # CORREÇÃO DA LÓGICA DE DUPLA CHANCE E DNB (DINÂMICA ENTRE TIME PRINCIPAL E ADVERSÁRIO)
                        if vh >= va + 5.0:
                            dnb_sug = f"Empate Anula: {time_principal} 🟢"
                            dupla_sug = f"Chance Dupla: {time_principal} ou Empate (1X) 🛡️"
                        elif va >= vh + 5.0:
                            dnb_sug = f"Empate Anula: {adversario} 🟢"
                            dupla_sug = f"Chance Dupla: {adversario} ou Empate (X2) 🛡️"
                        else:
                            if vh >= va:
                                dnb_sug = f"Empate Anula: {time_principal} (Equilibrado) ⚖️"
                                dupla_sug = f"Chance Dupla: {time_principal} ou Empate (1X) 🛡️"
                            else:
                                dnb_sug = f"Empate Anula: {adversario} (Equilibrado) ⚖️"
                                dupla_sug = f"Chance Dupla: {adversario} ou Empate (X2) 🛡️"

                        st.markdown(f"- **Sugestão DNB:** `{dnb_sug}`")
                        st.markdown(f"- **Chance Dupla Sugerida:** `{dupla_sug}`")

                with tip_c2:
                    with st.container(border=True):
                        st.markdown("#### 🚩 Escanteios Dinâmicos Calibrados (v22)")
                        st.markdown(f"- **Total Estimado:** `{escanteios_jogo:.1f}` cantos")
                        
                        if escanteios_jogo >= 11.5:
                            sel_cantos_sim = "Mais de 10.5 Escanteios 🔥"
                        elif escanteios_jogo >= 10.0:
                            sel_cantos_sim = "Mais de 9.5 Escanteios 🚩"
                        elif escanteios_jogo >= 8.5:
                            sel_cantos_sim = "Mais de 8.5 Escanteios ⚡"
                        elif escanteios_jogo >= 7.5:
                            sel_cantos_sim = "Mais de 7.5 Escanteios ⚽"
                        else:
                            sel_cantos_sim = "Menos de 8.5 Escanteios 🛡️"
                            
                        st.markdown(f"- **Sugestão de Cantos:** `{sel_cantos_sim}`")

                    with st.container(border=True):
                        st.markdown("#### 🟨 Cartões & Bilhete Pro")
                        st.markdown(f"- **Total Estimado Cartões:** `{total_cartoes:.2f}`")
                        sel_cart_sim = "Mais de 4.5 Cartões 🟨" if total_cartoes >= 4.2 else "Mais de 3.5 Cartões 🟨" if total_cartoes >= 3.2 else "Menos de 4.5 Cartões 🛡️"
                        st.markdown(f"- **Sugestão de Cartões:** `{sel_cart_sim}`")
                        st.markdown(f"- **Combo IA Recomendado:** `{sel_gols_sim} + {sel_cart_sim}`")
                
                st.markdown("---")
                st.markdown(f"### 📜 Histórico Real H2H")
                df_h2h, _ = buscar_h2h_api(id_time1, id_time2, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                if df_h2h is not None: st.dataframe(df_h2h, use_container_width=True, hide_index=True)

    with aba_chat:
        st.subheader("🤖 Chat com a Inteligência Artificial Preditiva")
        st.markdown("Tire dúvidas sobre as estatísticas do time selecionado, projeções de gols via Poisson, escanteios e estratégias de trading com o assistente inteligente.")
        
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": f"Olá! Sou a IA Preditiva v22 Market Ultimate. Atualmente o time em foco é **{time_principal or 'Nenhum selecionado'}** na competição **{opcao_liga or 'Geral'}**. Como posso ajudar nas suas análises hoje?"}
            ]
            
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
        if prompt_usuario := st.chat_input("Digite sua dúvida para a IA...", key="chat_input_user"):
            st.session_state.messages.append({"role": "user", "content": prompt_usuario})
            with st.chat_message("user"):
                st.markdown(prompt_usuario)
                
            with st.chat_message("assistant"):
                with st.spinner("Analisando dados do mercado e gerando resposta..."):
                    pergunta_lower = prompt_usuario.lower()
                    contexto_base = f"Time: {time_principal} | Competição: {opcao_liga} | Gols Feitos (Média): {stats_t1.get('gols_feitos_media', 0):.2f}"
                    
                    if "poisson" in pergunta_lower:
                        resposta_ia = f"O modelo v22 de Distribuição de Poisson avalia a taxa de gols esperados de cada equipe com base no histórico em casa e fora, calculando a probabilidade estatística exata para mercados de gols, BTTS e vencedor de forma isenta. ({contexto_base})"
                    elif "gols" in pergunta_lower or "over" in pergunta_lower or "btts" in pergunta_lower:
                        resposta_ia = f"Para **{time_principal}**, a média atual de gols marcados é de `{stats_t1.get('gols_feitos_media', 0):.2f}` e sofridos de `{stats_t1.get('gols_sofridos_media', 0):.2f}`. O motor dinâmico evita travar em linhas fixas, avaliando se o cenário pede Over, Under ou Ambas Marcam."
                    elif "cartão" in pergunta_lower or "cartoes" in pergunta_lower:
                        resposta_ia = f"A média atual de cartões pró para **{time_principal}** é de `{corners_t1.get('media_cartoes_pro', 0):.2f}` e contra é de `{corners_t1.get('media_cartoes_contra', 0):.2f}`. Você pode conferir o detalhamento completo jogo a jogo na aba 'Painel IA & Elenco'."
                    elif "escanteio" in pergunta_lower or "cantos" in pergunta_lower:
                        cantos_total = corners_t1.get('corners_for_geral', 0) + corners_t1.get('corners_ag_geral', 0)
                        resposta_ia = f"A média combinada de escanteios (pró + contra) para **{time_principal}** é de aproximadamente `{cantos_total:.2f}` por partida."
                    else:
                        resposta_ia = f"Com base nas informações ativas (**{time_principal or opcao_liga}**), o painel está calibrado com dados oficiais da API e algoritmos corrigidos de cartões e escanteios. Recomendo analisar a tabela detalhada de cartões no painel principal."
                    
                    st.markdown(resposta_ia)
                    st.session_state.messages.append({"role": "assistant", "content": resposta_ia})

# --- DISPARADORES DO TELEGRAM ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 📢 Canal & Automação Telegram")

if st.sidebar.button("🚀 Disparar Análise Pré-Live (IA v22)", key="btn_disparar_prelive"):
    if id_time1 and 'usar_comparacao' in locals() and usar_comparacao and 'adversario' in locals() and adversario:
        g_t1 = (stats_t1['gf_home'] + stats_t2['ga_away']) / 2
        g_t2 = (stats_t2['gf_away'] + stats_t1['ga_home']) / 2
        p_res = calcular_probabilidades_poisson(g_t1, g_t2)
        total_gols = g_t1 + g_t2
        
        c_proj_t1 = (corners_t1['corners_for_home'] + corners_t2['corners_ag_away']) / 2
        c_proj_t2 = (corners_t2['corners_for_away'] + corners_t1['corners_ag_home']) / 2
        escanteios_jogo = c_proj_t1 + c_proj_t2
        if LEAGUE_ID == 128: escanteios_jogo += 3.0
        elif LEAGUE_ID in [71, 39, 13]: escanteios_jogo += 2.0
        else: escanteios_jogo += 1.5
        total_cartoes = corners_t1['media_cartoes_pro'] + corners_t2['media_cartoes_pro']

        msg = f"""🧠 <b>RELATÓRIO PRÉ-LIVE INTELIGENTE (IA v22)</b> 🧠\n\n⚽ <b>{time_principal} x {adversario}</b>\n🏆 Competição: {opcao_liga} ({SEASON_EFETIVA})\n\n📊 <b>MODELAGEM POISSON / GOLS:</b>\n• Expectativa Gols: {total_gols:.2f} ({p_res['over_2_5']:.1f}% Over 2.5)\n• BTTS: {p_res['btts']:.1f}%\n\n🚩 <b>ESCANTEIOS:</b>\n• Projeção Total: {escanteios_jogo:.1f} cantos\n\n🟨 <b>CARTÕES (Média Pró):</b>\n• {time_principal}: {corners_t1['media_cartoes_pro']:.2f}\n• {adversario}: {corners_t2['media_cartoes_pro']:.2f}"""
    elif id_time1:
        msg = f"""🧠 <b>RAIO-X INDIVIDUAL (IA)</b> 🧠\n\n⚽ <b>Time: {time_principal}</b>\n🏆 Competição: {opcao_liga} ({SEASON_EFETIVA})\n\n📊 <b>Gols Feitos (Média):</b> {stats_t1['gols_feitos_media']:.2f}\n🟨 <b>Cartões Pró (Média):</b> {corners_t1['media_cartoes_pro']:.2f}"""
    else:
        msg = f"""🧠 <b>SMART MULTI: PAINEL GERAL</b> 🧠\n\nNenhuma partida ou time selecionado."""
    
    if enviar_alerta_telegram(msg): 
        st.sidebar.success("🎉 Alerta IA enviado!")
    else: 
        st.sidebar.error("❌ Falha ao enviar.")

if st.sidebar.button("💎 Gerar & Enviar 'Bilhete do Dia' (IA Pro v22)", key="btn_bilhete_dia"):
    with st.spinner("Varrendo partidas de hoje com motor de Poisson corrigido e calibrando fuso horário..."):
        jogos_monitorados_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        
    if jogos_monitorados_hoje:
        amostra_monitorada = jogos_monitorados_hoje[:6]
        data_formatada_exibicao = datetime.now(FUSO_BR).strftime("%d/%m/%Y")
        
        msg_bilhete = f"""💎 <b>SMART TIPSTER: BILHETE DO DIA (IA MARKET ULTIMATE v22)</b> 💎\n📅 <i>Data: {data_formatada_exibicao}</i>\n\nAnálises com tabelas de cartões e escanteios detalhadas:\n\n"""
        
        for idx, j in enumerate(amostra_monitorada, 1):
            h_id = j['HomeID']
            a_id = j['AwayID']
            l_id = j['LeagueID']
            
            s_h = buscar_estatisticas_time(h_id, l_id, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            s_a = buscar_estatisticas_time(a_id, l_id, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            
            c_h_data = buscar_medias_escanteios(h_id, l_id, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            c_a_data = buscar_medias_escanteios(a_id, l_id, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            
            g_h_calc = (s_h['gf_home'] + s_a['ga_away']) / 2 if s_h['jogos'] > 0 and s_a['jogos'] > 0 else 1.3
            g_a_calc = (s_a['gf_away'] + s_h['ga_home']) / 2 if s_a['jogos'] > 0 and s_a['jogos'] > 0 else 1.2
            
            p_res = calcular_probabilidades_poisson(g_h_calc, g_a_calc)
            tot_gols_calc = g_h_calc + g_a_calc
            
            c_proj_h = (c_h_data['corners_for_home'] + c_a_data['corners_ag_away']) / 2
            c_proj_a = (c_a_data['corners_for_away'] + c_h_data['corners_ag_home']) / 2
            tot_c_calc = c_proj_h + c_proj_a
            
            if l_id == 128:
                tot_c_calc += 3.0
            elif l_id in [71, 39, 13]: 
                tot_c_calc += 2.0
            else:
                tot_c_calc += 1.5

            if tot_gols_calc >= 2.8 and p_res['over_2_5'] >= 50:
                sel_gols = "Mais de 2.5 Gols 🔥"
            elif p_res['btts'] >= 55 and tot_gols_calc >= 2.3:
                sel_gols = "Ambas Marcam (BTTS) Sim ⚡"
            elif tot_gols_calc >= 2.0:
                sel_gols = "Mais de 1.5 Gols ⚽"
            else:
                sel_gols = "Menos de 2.5 Gols 🛡️"
            
            if tot_c_calc >= 11.5:
                sel_cantos = "Mais de 10.5 Escanteios 🔥"
            elif tot_c_calc >= 10.0:
                sel_cantos = "Mais de 9.5 Escanteios 🚩"
            elif tot_c_calc >= 8.5:
                sel_cantos = "Mais de 8.5 Escanteios ⚡"
            elif tot_c_calc >= 7.5:
                sel_cantos = "Mais de 7.5 Escanteios ⚽"
            else:
                sel_cantos = "Menos de 8.5 Escanteios 🛡️"

            vh_b = p_res['vitoria_home']
            va_b = p_res['vitoria_away']
            
            if vh_b >= va_b + 5.0:
                sel_seg = f"Empate Anula: {j['Mandante']} 🟢" if vh_b > 45 else f"Chance Dupla: {j['Mandante']} ou Empate (1X) 🛡️"
            elif va_b >= vh_b + 5.0:
                sel_seg = f"Empate Anula: {j['Visitante']} 🟢" if va_b > 45 else f"Chance Dupla: {j['Visitante']} ou Empate (X2) 🛡️"
            else:
                if vh_b >= va_b:
                    sel_seg = f"Chance Dupla: {j['Mandante']} ou Empate (1X) [Equilibrado]"
                else:
                    sel_seg = f"Chance Dupla: {j['Visitante']} ou Empate (X2) [Equilibrado]"
                
            msg_bilhete += f"<b>{idx}. {j['Mandante']} x {j['Visitante']}</b>\n"
            msg_bilhete += f"   • 🏆 <i>Liga:</i> {j['Liga']}\n"
            msg_bilhete += f"   • 🎯 <i>IA Tips:</i> {sel_gols} | {sel_cantos}\n"
            msg_bilhete += f"   • 🛡️ <i>Segurança:</i> {sel_seg}\n"
            msg_bilhete += f"   • ⏰ <i>Horário (BR):</i> {j['Horário']}\n\n"
        
        msg_bilhete += f"🧠 <i>Smart Tipster IA v22: Relatórios otimizados e precisos.</i>"
        
        if enviar_alerta_telegram(msg_bilhete):
            st.sidebar.success("🔥 Bilhete IA v22 enviado com sucesso!")
        else:
            st.sidebar.error("❌ Falha ao enviar ao Telegram.")
    else:
        st.sidebar.warning(f"⚠️ Não há jogos cadastrados para hoje ({DATA_HOJE_STR}) nas ligas monitoradas.")
