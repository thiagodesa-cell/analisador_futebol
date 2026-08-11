import streamlit as st
import pandas as pd
import requests
import time
import math
from datetime import datetime, timedelta, timezone

# Tenta importar o SDK moderno do Google GenAI
try:
    from google import genai
    from google.genai import types
    GEANAI_SDK_DISPONIVEL = True
except ImportError:
    GEANAI_SDK_DISPONIVEL = False

st.set_page_config(page_title="Painel Pro - Global Trading & IA Preditiva v22.2", layout="wide")

# --- CONFIGURAÇÃO DA API E TELEGRAM ---
# Compatível com chaves antigas (AIza) ou novas (HAQ)
API_KEY_FIXA = "AQ.Ab8RN6L-h6_cjeQe4v9pSwQq8tzG-N407YZY4ixRGurNuX6yJA" 
SEASON = datetime.now().year 

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

# --- VERSÃO 22.2 COM CHAT INTEGRADO AO GEMINI RECURSIVO ---
def obter_chave_atualizacao():
    agora = datetime.now()
    if agora.hour < 8:
        return (agora - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        return agora.strftime("%Y-%m-%d")

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v22_2_ai_market_u6"  
DATA_HOJE_STR = datetime.now().strftime("%Y-%m-%d")

if "historico_bilhetes" not in st.session_state:
    st.session_state.historico_bilhetes = []

# --- CONVERSOR INTELIGENTE DE FUSO HORÁRIO (UTC -> BRASÍLIA UTC-3) ---
def converter_para_horario_brasilia(iso_string):
    try:
        dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        fuso_br = timezone(timedelta(hours=-3))
        dt_local = dt_utc.astimezone(fuso_br)
        return dt_local.strftime("%Y-%m-%d"), dt_local.strftime("%d/%m/%Y"), dt_local.strftime("%H:%M")
    except:
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
                
                if any(p in t_name_lower for p in filtro_ruido): continue
                if any(r in t_name_lower for r in ruido_regional): continue

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
    anos_para_testar = [season - 1, season - 2, season, season - 3]
    
    for s in anos_para_testar:
        url = f"https://v3.football.api-sports.io/players?search={termo}&season={s}"
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 429: return {"__rate_limit__": True}
            if res.status_code == 200:
                data = res.json()
                if data.get('results', 0) > 0:
                    for item in data['response']:
                        p_info = item['player']
                        stats_list = item.get('statistics', [])
                        if stats_list:
                            for stat in stats_list:
                                t_id = stat['team']['id']
                                t_name = stat['team']['name']
                                l_id = stat['league']['id']
                                l_name = stat['league']['name']
                                label = f"{p_info['name']} ({t_name} - {l_name}) [{s}]"
                                jogadores_dict[label] = {
                                    'player_id': p_info['id'], 'player_name': p_info['name'],
                                    'team_id': t_id, 'team_name': t_name,
                                    'league_id': l_id, 'league_name': l_name, 'season': s
                                }
                    if jogadores_dict: return jogadores_dict
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

# --- BUSCA GLOBAL DE CLUBES ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🌍 Busca Global de Clubes")
termo_busca_global = st.sidebar.text_input("Pesquisar qualquer clube no mundo:", placeholder="Ex: Flamengo, Boca...", key="input_busca_clube_global")

clube_global_selecionado = None
id_time_global = None

if termo_busca_global and len(termo_busca_global) >= 2:
    dict_globais = buscar_times_global(termo_busca_global, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    if dict_globais:
        escolha_g = st.sidebar.selectbox("Resultados da Busca Global:", list(dict_globais.keys()), index=None, placeholder="Selecione o clube...", key="select_global_clube")
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
        st.sidebar.error("⚠️ Limite diário da API de jogadores atingido.")
    elif dict_jogadores_globais:
        escolha_j = st.sidebar.selectbox("Resultados de Jogadores:", list(dict_jogadores_globais.keys()), index=None, placeholder="Selecione o jogador...", key="select_global_jogador")
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
    st.sidebar.success(f"🔍 Jogador: **{jogador_global_selecionado}**")
elif clube_global_selecionado:
    time_principal = clube_global_selecionado
    id_time1 = id_time_global
    st.sidebar.success(f"🌐 Ativo: **{time_principal}**")
elif LEAGUE_ID:
    times_disponiveis = sorted(list(TEAM_IDS.keys())) if TEAM_IDS else []
    time_principal = st.sidebar.selectbox("Escolha o Time", times_disponiveis, index=None, placeholder="Selecione...", key="select_time_principal")
    id_time1 = TEAM_IDS[time_principal] if time_principal else None
else:
    time_principal, id_time1 = None, None

st.sidebar.info(f"🔄 Motor IA v22.2 U6 • Base: {CHAVE_ATUALIZACAO}")
st.sidebar.markdown("---")
st.sidebar.markdown("**Desenvolvido por:** Thiago Oliveira De sá")

def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload)
        return res.status_code == 200
    except:
        return False

# --- FUNÇÕES DE DADOS (CACHE) ---

@st.cache_data(persist="disk")
def buscar_tabela_classificacao(league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/standings?league={league_id}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            standings = data['response'][0]['league']['standings'][0]
            tabela = [{
                'Pos': s['rank'], 'Time': s['team']['name'], 'Pts': s['points'],
                'J': s['all']['played'], 'V': s['all']['win'], 'E': s['all']['draw'],
                'D': s['all']['lose'], 'GP': s['all']['goals']['for'], 'GC': s['all']['goals']['against'],
                'SG': s['goalsDiff']
            } for s in standings]
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
            jogos_lista = []
            for f in data['response']:
                _, match_date_fmt, match_time = converter_para_horario_brasilia(f['fixture']['date'])
                status = f['fixture']['status']['short']
                g_home = f['goals']['home']
                g_away = f['goals']['away']
                placar_str = f"{g_home} x {g_away}" if g_home is not None else "vs"
                jogos_lista.append({
                    'Data': match_date_fmt, 'Horário': match_time, 'Rodada': f['league'].get('round', 'Rodada'),
                    'Mandante': f['teams']['home']['name'], 'Placar': placar_str, 'Visitante': f['teams']['away']['name'], 'Status': status
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
                if f['league']['id'] in LIGAS_MONITORADAS:
                    _, match_date_fmt, match_time = converter_para_horario_brasilia(f['fixture']['date'])
                    if f['fixture']['status']['short'] in ['NS', 'TBD', '1H', 'HT', '2H']:
                        jogos_filtrados.append({
                            'LeagueID': f['league']['id'], 'Liga': LIGAS_MONITORADAS[f['league']['id']],
                            'Mandante': f['teams']['home']['name'], 'Visitante': f['teams']['away']['name'],
                            'HomeID': f['teams']['home']['id'], 'AwayID': f['teams']['away']['id'],
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
                if f['fixture']['status']['short'] in ['FT', 'AET', 'PEN', '1H', '2H', 'HT', 'ET']:
                    if ref not in ref_data: ref_data[ref] = {'Jogos': 0, 'Confrontos': []}
                    ref_data[ref]['Jogos'] += 1
                    ref_data[ref]['Confrontos'].append(f"{f['teams']['home']['name']} x {f['teams']['away']['name']}")
            rows = [{'Árbitro': r, 'Jogos Apitados': i['Jogos'], 'Últimos Confrontos': ", ".join(i['Confrontos'][:2])} for r, i in ref_data.items()]
            return pd.DataFrame(rows).sort_values(by='Jogos Apitados', ascending=False) if rows else pd.DataFrame()
    except:
        pass
    return pd.DataFrame()

@st.cache_data(persist="disk")
def buscar_medias_escanteios(team_id, league_id, season, key, data_cache):
    url_fixtures = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&team={team_id}&last=10"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    cantos_pro_casa, cantos_contra_casa, cantos_pro_fora, cantos_contra_fora = [], [], [], []
    cartoes_pro, cartoes_contra = [], []
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
                
                g_home, g_away = f['goals']['home'] or 0, f['goals']['away'] or 0
                g_pro, g_contra = (g_home, g_away) if is_home else (g_away, g_home)
                
                time.sleep(0.15)
                res_s = requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={f_id}", headers=headers)
                data_s = res_s.json()
                t_corners, o_corners, t_yellow, o_yellow = 0, 0, 0, 0
                if data_s.get('results', 0) > 0:
                    for item in data_s['response']:
                        for s in item['statistics']:
                            if s['type'] == 'Corner Kicks' and s['value'] is not None:
                                c = int(s['value'])
                                if item['team']['id'] == team_id: t_corners = c
                                else: o_corners = c
                            elif s['type'] == 'Yellow Cards' and s['value'] is not None:
                                y = int(s['value'])
                                if item['team']['id'] == team_id: t_yellow = y
                                else: o_yellow = y
                
                if is_home:
                    cantos_pro_casa.append(t_corners)
                    cantos_contra_casa.append(o_corners)
                    cartoes_pro.append(t_yellow)
                    cartoes_contra.append(o_yellow)
                else:
                    cantos_pro_fora.append(t_corners)
                    cantos_contra_fora.append(o_corners)
                    cartoes_pro.append(t_yellow)
                    cartoes_contra.append(o_yellow)
                
                detalhes.append({
                    'Data': dt_fmt, 'Adversário': adv, 'Mando': 'Casa' if is_home else 'Fora', 'Placar': f"{g_home} x {g_away}",
                    'Gols Pró': g_pro, 'Gols Contra': g_contra, 'Cantos Pró': t_corners, 'Cantos Contra': o_corners,
                    'Total Cantos': t_corners + o_corners, 'Cartões Pró': t_yellow, 'Cartões Contra': o_yellow, 'Total Cartões': t_yellow + o_yellow
                })
        
        cf_geral = sum(cantos_pro_casa + cantos_pro_fora) / max(len(cantos_pro_casa + cantos_pro_fora), 1)
        ca_geral = sum(cantos_contra_casa + cantos_contra_fora) / max(len(cantos_contra_casa + cantos_contra_fora), 1)
        m_pro = sum(cartoes_pro) / max(len(cartoes_pro), 1)
        m_contra = sum(cartoes_contra) / max(len(cartoes_contra), 1)

        return {
            'corners_for_geral': cf_geral if cf_geral > 1.0 else 4.8,
            'corners_ag_geral': ca_geral if ca_geral > 1.0 else 4.5,
            'corners_for_home': sum(cantos_pro_casa)/max(len(cantos_pro_casa),1) if cantos_pro_casa else 5.0,
            'corners_ag_home': sum(cantos_contra_casa)/max(len(cantos_contra_casa),1) if cantos_contra_casa else 4.5,
            'corners_for_away': sum(cantos_pro_fora)/max(len(cantos_pro_fora),1) if cantos_pro_fora else 4.2,
            'corners_ag_away': sum(cantos_contra_fora)/max(len(cantos_contra_fora),1) if cantos_contra_fora else 4.8,
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
def buscar_scout_elenco_u6(team_id, league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&team={team_id}&last=6"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) == 0: return pd.DataFrame(), "Sem dados"
        
        forma = ["🟢" if (f['teams']['home']['winner'] and f['teams']['home']['id']==team_id) or (f['teams']['away']['winner'] and f['teams']['away']['id']==team_id) else "🔴" if f['teams']['home']['winner'] is not None else "🟡" for f in reversed(data['response'])]
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
                                    player_data[name] = {'Pos': st_p.get('games',{}).get('position','-'), 'J':0, 'G':0, 'Fin':0, 'Alvo':0, 'A':0}
                                player_data[name]['J'] += 1
                                player_data[name]['G'] += st_p.get('goals',{}).get('total') or 0
                                player_data[name]['Fin'] += st_p.get('shots',{}).get('total') or 0
                                player_data[name]['Alvo'] += st_p.get('shots',{}).get('on') or 0
                                player_data[name]['A'] += st_p.get('cards',{}).get('yellow') or 0
        rows = [{
            'Jogador': k, 'Posição': v['Pos'], 'Jogos (U6)': f"{v['J']}/6", 'Gols (U6)': v['G'],
            'Finalizações Média': round(v['Fin']/v['J'], 2), 'Chutes no Alvo Média': round(v['Alvo']/v['J'], 2), 'Amarelos': v['A']
        } for k, v in player_data.items() if v['J'] > 0]
        return pd.DataFrame(rows).sort_values(by=['Gols (U6)', 'Finalizações Média'], ascending=[False,False]) if rows else pd.DataFrame(), " ".join(forma)
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
            rows = [{
                'Data': converter_para_horario_brasilia(m['fixture']['date'])[1], 'Competição': m['league']['name'],
                'Mandante': m['teams']['home']['name'], 'Placar': f"{m['goals']['home']} x {m['goals']['away']}", 'Visitante': m['teams']['away']['name']
            } for m in sorted(data['response'], key=lambda x: x['fixture']['date'], reverse=True)[:6]]
            return pd.DataFrame(rows), None
    except:
        pass
    return None, "Sem confrontos recentes."

def gerar_tendencia_dinamica(time_nome, df_hist):
    if df_hist is None or df_hist.empty:
        return f"Sem dados suficientes nas últimas partidas para gerar tendência de {time_nome}."
    ultimos_6 = df_hist.head(6)
    g_pro, g_contra = ultimos_6['Gols Pró'].sum(), ultimos_6['Gols Contra'].sum()
    media_c = ultimos_6['Total Cantos'].mean() if 'Total Cantos' in ultimos_6.columns else 9.0
    texto = f"📈 **Tendência Dinâmica U6 ({time_nome}):** Nos últimos 6 confrontos, marcou **{g_pro} gols** e sofreu **{g_contra}**. "
    if (g_pro + g_contra) / 6 >= 2.8:
        texto += "Apresenta padrão altamente ofensivo (Over 2.5 e BTTS). "
    else:
        texto += "Equipe equilibrada e defensiva. "
    texto += f"Média de cantos: `{media_c:.1f}`."
    return texto

# --- CARREGAMENTO DE DADOS GERAIS ---
if LEAGUE_ID:
    df_tabela = buscar_tabela_classificacao(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_arbitros = buscar_dados_arbitros(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_jogos_liga = buscar_jogos_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    rodada_atual_str = buscar_rodada_atual(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
else:
    df_tabela, df_arbitros, df_jogos_liga, rodada_atual_str = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None

stats_t1 = {'jogos':0,'gols_feitos_media':0.0,'gols_sofridos_media':0.0,'gf_home':0.0,'ga_home':0.0,'gf_away':0.0,'ga_away':0.0,'clean_sheets':0}
corners_t1 = {'corners_for_geral':0.0,'corners_ag_geral':0.0,'corners_for_home':0.0,'corners_ag_home':0.0,'corners_for_away':0.0,'corners_ag_away':0.0,'media_cartoes_pro':0.0,'media_cartoes_contra':0.0,'df_historico':pd.DataFrame()}
df_elenco_u6, string_forma_t1 = pd.DataFrame(), "Sem dados"

if id_time1 and LEAGUE_ID:
    stats_t1 = buscar_estatisticas_time(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    corners_t1 = buscar_medias_escanteios(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_elenco_u6, string_forma_t1 = buscar_scout_elenco_u6(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)

# =========================================================================
# INTERFACE PRINCIPAL DO STREAMLIT
# =========================================================================
if not LEAGUE_ID and not clube_global_selecionado and not id_time1:
    st.title("⚽ Smart Tipster Pro v22.2 - Motor de IA Preditiva & U6 Dinâmico")
    st.markdown("---")
    st.info("👈 **Para começar, selecione uma competição** na barra lateral, utilize a **Busca Global de Clubes** ou pesquise qualquer **jogador**.")
elif LEAGUE_ID and not id_time1:
    st.title(f"🏆 Panorama Geral: {opcao_liga} ({SEASON_EFETIVA})")
    tab_pan_jogos, tab_pan_tabela, tab_pan_refs, tab_pan_bilhetes = st.tabs(["📅 Jogos", "🏆 Tabela", "⚖️ Árbitros", "📜 Bilhetes"])
    with tab_pan_jogos: st.dataframe(df_jogos_liga, use_container_width=True, hide_index=True)
    with tab_pan_tabela: st.dataframe(df_tabela, use_container_width=True, hide_index=True)
    with tab_pan_refs: st.dataframe(df_arbitros, use_container_width=True, hide_index=True)
    with tab_pan_bilhetes:
        for idx, b in enumerate(reversed(st.session_state.historico_bilhetes), 1):
            with st.container(border=True): st.markdown(b['conteudo'], unsafe_allow_html=True)
else:
    st.title(f"⚽ Painel Preditivo Pro v22.2 - {opcao_liga}")
    aba_painel, aba_jogos_dia, aba_arbitros, aba_tabela, aba_historico_bilhetes, aba_chat = st.tabs([
        "📊 Painel IA & U6", "📅 Jogos & Rodada", "⚖️ Árbitros", f"🏆 Tabela", "📜 Bilhetes Salvos", "🤖 Chat Real com Gemini"
    ])

    with aba_tabela: st.dataframe(df_tabela, use_container_width=True, hide_index=True)
    with aba_jogos_dia: st.dataframe(df_jogos_liga, use_container_width=True, hide_index=True)
    with aba_arbitros: st.dataframe(df_arbitros, use_container_width=True, hide_index=True)
    with aba_historico_bilhetes:
        for idx, b in enumerate(reversed(st.session_state.historico_bilhetes), 1):
            with st.container(border=True): st.markdown(b['conteudo'], unsafe_allow_html=True)

    with aba_painel:
        st.subheader(f"📊 Raio-X Preditivo (Base U6): {time_principal}")
        st.markdown(f"**Forma Recente (U6):** {string_forma_t1}")
        st.info(gerar_tendencia_dinamica(time_principal, corners_t1['df_historico']))
        
        rg1, rg2, rg3 = st.columns(3)
        rg1.metric("Jogos Disputados", stats_t1['jogos'])
        rg2.metric("Clean Sheets", stats_t1['clean_sheets'])
        
        st.markdown("---")
        col_esq, col_dir = st.columns(2)
        with col_esq:
            st.markdown("### ⚽ Gols & Histórico (U6)")
            st.metric("Média Gols Feitos", f"{stats_t1['gols_feitos_media']:.2f}")
            st.metric("Média Gols Sofridos", f"{stats_t1['gols_sofridos_media']:.2f}")
            if not corners_t1['df_historico'].empty:
                st.dataframe(corners_t1['df_historico'][['Data', 'Adversário', 'Mando', 'Placar']].head(6), use_container_width=True, hide_index=True)
        with col_dir:
            st.markdown("### 🚩 Escanteios & Cartões (U6)")
            st.metric("Cantos Pró (Geral)", f"{corners_t1['corners_for_geral']:.2f}")
            st.metric("Média Cartões Pró", f"{corners_t1['media_cartoes_pro']:.2f}")
            if not corners_t1['df_historico'].empty:
                st.dataframe(corners_t1['df_historico'][['Data', 'Adversário', 'Total Cantos', 'Total Cartões']].head(6), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("🤖 Simulador H2H & Motor de Probabilidade (Poisson)")
        usar_comparacao = st.checkbox("Ativar motor de IA e H2H contra adversário", key="check_usar_comp")
        if usar_comparacao:
            advs = sorted([t for t in TEAM_IDS.keys() if t != time_principal])
            adversario = st.selectbox("Escolha o Adversário", advs, key="sel_adv_h2h")
            if adversario:
                id_t2 = TEAM_IDS[adversario]
                s_t2 = buscar_estatisticas_time(id_t2, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                c_t2 = buscar_medias_escanteios(id_t2, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                
                g_t1 = (stats_t1['gf_home'] + s_t2['ga_away']) / 2
                g_t2 = (s_t2['gf_away'] + stats_t1['ga_home']) / 2
                p_pois = calcular_probabilidades_poisson(g_t1, g_t2)
                
                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric(f"Vitória ({time_principal})", f"{p_pois['vitoria_home']:.1f}%")
                sc2.metric(f"Vitória ({adversario})", f"{p_pois['vitoria_away']:.1f}%")
                sc3.metric("Over 2.5 Gols", f"{p_pois['over_2_5']:.1f}%")
                sc4.metric("BTTS", f"{p_pois['btts']:.1f}%")

    # =========================================================================
    # ABA 6: CHAT REAL COM O GEMINI INTEGRADO (FLUIDO E INTELIGENTE)
    # =========================================================================
    with aba_chat:
        st.subheader("🤖 Chat Inteligente Real com o Gemini (v22.2)")
        st.markdown("Faça qualquer pergunta analítica. O assistente possui contexto completo dos dados U6 da API, médias de escanteios, cartões e confrontos.")
        
        if "messages_gemini" not in st.session_state:
            st.session_state.messages_gemini = [
                {"role": "assistant", "content": f"Olá! Sou a IA Preditiva do painel. O time em foco atual é **{time_principal or 'Nenhum'}** na competição **{opcao_liga or 'Geral'}**. Como posso ajudar na sua análise ou projeção para o próximo jogo?"}
            ]
            
        for msg in st.session_state.messages_gemini:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
        if prompt_usuario := st.chat_input("Digite sua dúvida (ex: 'Como o Flamengo vem nos escanteios?', 'Vai ter gols contra o Cruzeiro?')..."):
            st.session_state.messages_gemini.append({"role": "user", "content": prompt_usuario})
            with st.chat_message("user"):
                st.markdown(prompt_usuario)
                
            with st.chat_message("assistant"):
                with st.spinner("O Gemini está processando os dados U6 e gerando a análise..."):
                    resposta_ia = ""
                    
                    if GEANAI_SDK_DISPONIVEL:
                        try:
                            # Inicializa o cliente GenAI oficial aceitando chaves AIza ou HAQ
                            client = genai.Client(api_key=API_KEY_FIXA)
                            
                            # Constrói o contexto estatístico atual para alimentar a IA
                            contexto_estatistico = f"""
                            Contexto do Usuário no Painel:
                            - Time Principal Ativo: {time_principal or 'Nenhum'}
                            - Competição: {opcao_liga or 'Geral'}
                            - Média Gols Feitos: {stats_t1.get('gols_feitos_media', 0):.2f}
                            - Média Gols Sofridos: {stats_t1.get('gols_sofridos_media', 0):.2f}
                            - Média Escanteios Pró (Geral): {corners_t1.get('corners_for_geral', 0):.2f}
                            - Média Escanteios Contra (Geral): {corners_t1.get('corners_ag_geral', 0):.2f}
                            - Média Cartões Pró: {corners_t1.get('media_cartoes_pro', 0):.2f}
                            - Forma Recente (U6): {string_forma_t1}
                            """
                            
                            prompt_sistema = f"""Você é um analista especialista em apostas esportivas, trading e estatísticas de futebol de alta performance. 
                            Responda de forma fluida, intuitiva, detalhada e profissional para o usuário com base nos seguintes dados reais recentes (U6):
                            {contexto_estatistico}
                            """
                            
                            response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=[prompt_sistema, prompt_usuario]
                            )
                            resposta_ia = response.text
                        except Exception as e:
                            resposta_ia = f"⚠️ Erro ao consultar a API do Gemini: {e}. Verifique se a sua chave está ativa."
                    else:
                        # Fallback inteligente se a biblioteca moderna não estiver instalada
                        resposta_ia = f"O SDK do Gemini não foi detectado no ambiente Python. Com base nos dados U6 do **{time_principal}**, a média de gols é `{stats_t1.get('gols_feitos_media', 0):.2f}` e de cantos é `{corners_t1.get('corners_for_geral', 0):.2f}`."
                    
                    st.markdown(resposta_ia)
                    st.session_state.messages_gemini.append({"role": "assistant", "content": resposta_ia})

# --- BOTÕES DA BARRA LATERAL (TELEGRAM / BILHETE DO DIA) ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 📢 Canal & Automação Telegram")

if st.sidebar.button("🚀 Disparar Análise Pré-Live (IA v22.2)", key="btn_dispr_pre"):
    msg = f"🧠 <b>RELATÓRIO PRÉ-LIVE (IA v22.2 U6)</b>\n⚽ <b>Time:</b> {time_principal or 'Geral'}\n🏆 <b>Liga:</b> {opcao_liga or 'N/A'}\n📊 <b>Média Gols:</b> {stats_t1.get('gols_feitos_media', 0):.2f}"
    if enviar_alerta_telegram(msg): st.sidebar.success("🎉 Enviado!")
    else: st.sidebar.error("❌ Falha ao enviar.")

if st.sidebar.button("💎 Gerar & Enviar 'Bilhete do Dia'", key="btn_bilhete_dia"):
    with st.spinner("Varrendo partidas de hoje..."):
        jogos_hoje = buscar_jogos_ligas_monitoradas_por_data(DATA_HOJE_STR, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    if jogos_hoje:
        msg_b = f"💎 <b>SMART TIPSTER: BILHETE DO DIA (IA v22.2)</b> 💎\n📅 <i>Data: {DATA_HOJE_STR}</i>\n\n"
        for j in jogos_hoje[:5]:
            msg_b += f"• <b>{j['Mandante']} x {j['Visitante']}</b> ({j['Liga']}) - ⏰ {j['Horário']}\n"
        st.session_state.historico_bilhetes.append({'data': DATA_HOJE_STR, 'conteudo': msg_b})
        if enviar_alerta_telegram(msg_b): st.sidebar.success("🔥 Bilhete enviado e salvo!")
    else:
        st.sidebar.warning("⚠️ Sem jogos hoje nas ligas monitoradas.")
