import streamlit as st
import pandas as pd
import requests
import time
import math
from datetime import datetime, timedelta, timezone
import os
from openai import OpenAI  # Importação oficial da OpenAI

st.set_page_config(page_title="Painel Pro - Global Trading & IA Preditiva v22.1", layout="wide")

# --- CONFIGURAÇÃO DA API E TELEGRAM ---
API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"
OPENAI_API_KEY_USER = "SUA_CHAVE_OPENAI_AQUI"  # Substitua pela sua chave da OpenAI
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

def obter_chave_atualizacao():
    agora = datetime.now()
    if agora.hour < 8:
        return (agora - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        return agora.strftime("%Y-%m-%d")

CHAVE_ATUALIZACAO = obter_chave_atualizacao() + "_v22_1_ai_market_u6"  
DATA_HOJE_STR = datetime.now().strftime("%Y-%m-%d")

if "historico_bilhetes" not in st.session_state:
    st.session_state.historico_bilhetes = []

def converter_para_horario_brasilia(iso_string):
    try:
        dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        fuso_br = timezone(timedelta(hours=-3))
        dt_local = dt_utc.astimezone(fuso_br)
        return dt_local.strftime("%Y-%m-%d"), dt_local.strftime("%d/%m/%Y"), dt_local.strftime("%H:%M")
    except:
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

st.sidebar.header("🏆 Seleção da Competição Global")
opcao_liga = st.sidebar.radio(
    "Escolha qual campeonato deseja analisar:",
    list(LIGAS_MONITORADAS.values()),
    index=None,
    key="radio_opcao_liga"
)

LEAGUE_ID = [k for k, v in LIGAS_MONITORADAS.items() if v == opcao_liga][0] if opcao_liga else None

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

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Configurações de Análise IA")

if clube_global_selecionado:
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
    st.sidebar.info("📌 Selecione uma competição ou pesquise um clube acima.")

st.sidebar.info(f"🔄 Motor IA v22.1 U6 Dinâmico Ativo • Base: {CHAVE_ATUALIZACAO}")
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
    except:
        return False

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
                _, match_date_fmt, match_time = converter_para_horario_brasilia(date_str)
                status = f['fixture']['status']['short']
                home_name = f['teams']['home']['name']
                away_name = f['teams']['away']['name']
                goals_home = f['goals']['home']
                goals_away = f['goals']['away']
                placar_str = f"{goals_home} x {goals_away}" if goals_home is not None else "vs"
                round_name = f['league'].get('round', 'Rodada')
                jogos_lista.append({
                    'Data': match_date_fmt, 'Horário': match_time, 'Rodada': round_name,
                    'Mandante': home_name, 'Placar': placar_str, 'Visitante': away_name, 'Status': status
                })
            return pd.DataFrame(jogos_lista)
    except:
        pass
    return pd.DataFrame()

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
def buscar_scout_elenco_u6(team_id, league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&team={team_id}&last=6"
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
            'Jogador': k, 'Posição': v['Pos'], 'Jogos (U6)': f"{v['J']}/6", 'Gols (Total U6)': v['G'],
            'Finalizações Média': round(v['Fin']/v['J'], 2), 'Chutes no Alvo Média': round(v['Alvo']/v['J'], 2),
            'Faltas Cometidas Média': round(v['FC']/v['J'], 2), 'Faltas Sofridas Média': round(v['FS']/v['J'], 2),
            'Desarmes Média': round(v['Des']/v['J'], 2), 'Amarelos (Total U6)': v['A'], 'Vermelhos (Total U6)': v['V']
        } for k, v in player_data.items() if v['J'] > 0]
        return pd.DataFrame(rows).sort_values(by=['Gols (Total U6)', 'Finalizações Média'], ascending=[False,False]) if rows else pd.DataFrame(), " ".join(forma)
    except:
        return pd.DataFrame(), "Erro"

def gerar_tendencia_dinamica(time_nome, df_hist):
    if df_hist is None or df_hist.empty:
        return f"Sem dados suficientes nas últimas partidas para gerar tendência de {time_nome}."
    ultimos_6 = df_hist.head(6)
    gols_pro_total = ultimos_6['Gols Pró'].sum()
    gols_contra_total = ultimos_6['Gols Contra'].sum()
    media_cantos = ultimos_6['Total Cantos'].mean() if 'Total Cantos' in ultimos_6.columns else 9.0
    media_cartoes = ultimos_6['Total Cartões'].mean() if 'Total Cartões' in ultimos_6.columns else 4.0
    
    texto = f"📈 **Tendência Dinâmica U6 ({time_nome}):** Nos últimos 6 confrontos analisados, a equipe marcou **{gols_pro_total} gols** e sofreu **{gols_contra_total} gols**. "
    return texto

if LEAGUE_ID:
    with st.spinner(f"Extraindo panorama geral de {opcao_liga}..."):
        df_tabela = buscar_tabela_classificacao(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        df_arbitros = buscar_dados_arbitros(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
        df_jogos_liga = buscar_jogos_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
else:
    df_tabela = pd.DataFrame()
    df_arbitros = pd.DataFrame()
    df_jogos_liga = pd.DataFrame()

stats_t1 = {'jogos':0,'gols_feitos_media':0.0,'gols_sofridos_media':0.0,'gf_home':0.0,'ga_home':0.0,'gf_away':0.0,'ga_away':0.0,'clean_sheets':0}
corners_t1 = {'corners_for_geral':0.0,'corners_ag_geral':0.0,'corners_for_home':0.0,'corners_ag_home':0.0,'corners_for_away':0.0,'corners_ag_away':0.0,'media_cartoes_pro':0.0,'media_cartoes_contra':0.0,'df_historico':pd.DataFrame()}
df_elenco_u6 = pd.DataFrame()
string_forma_t1 = "Sem dados"

if id_time1 and LEAGUE_ID:
    stats_t1 = buscar_estatisticas_time(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    corners_t1 = buscar_medias_escanteios(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_elenco_u6, string_forma_t1 = buscar_scout_elenco_u6(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)

if not LEAGUE_ID and not clube_global_selecionado and not id_time1:
    st.title("⚽ Smart Tipster Pro v22.1 - Motor de IA Preditiva & U6 Dinâmico")
    st.markdown("---")
    st.info("👈 **Para começar, selecione uma competição** na barra lateral ou utilize a **Busca Global de Clubes**.")
else:
    st.title(f"⚽ Painel Preditivo Pro v22.1 - {opcao_liga}")
    
    aba_painel, aba_chat = st.tabs(["📊 Painel IA & U6", "🤖 Chat com o ChatGPT"])

    with aba_painel:
        st.subheader(f"📊 Raio-X Preditivo (Base U6): {time_permanent if 'time_permanent' in locals() else time_principal}")
        st.markdown(f"**Forma Recente:** {string_forma_t1}")
        texto_tendencia = gerar_tendencia_dinamica(time_principal, corners_t1['df_historico'])
        st.info(texto_tendencia)

    with aba_chat:
        st.subheader("🤖 Chat com o ChatGPT (OpenAI)")
        st.markdown("Faça perguntas livres para o modelo **ChatGPT (GPT-4o / GPT-4o-mini)** sobre as estatísticas dos últimos 6 jogos e tendências de mercado.")
        
        if "messages_openai" not in st.session_state:
            st.session_state.messages_openai = [
                {"role": "assistant", "content": f"Olá! Sou o assistente de IA baseado no ChatGPT integrado ao painel. O time em foco atual é **{time_principal or 'Nenhum'}**. Como posso ajudar?"}
            ]
            
        for message in st.session_state.messages_openai:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
        if prompt_usuario := st.chat_input("Digite sua dúvida para o ChatGPT...", key="chat_input_openai_user"):
            st.session_state.messages_openai.append({"role": "user", "content": prompt_usuario})
            with st.chat_message("user"):
                st.markdown(prompt_usuario)
                
            with st.chat_message("assistant"):
                with st.spinner("O ChatGPT está analisando os dados..."):
                    contexto_prompt = f"""
                    Você é um analista especialista em apostas esportivas e trading quantitativo integrando o painel Smart Tipster Pro v22.1.
                    Contexto atual:
                    - Competição: {opcao_liga}
                    - Time em foco: {time_principal}
                    - Média de gols feitos: {stats_t1.get('gols_feitos_media', 0):.2f}
                    - Média de gols sofridos: {stats_t1.get('gols_sofridos_media', 0):.2f}
                    
                    Pergunta do usuário: {prompt_usuario}
                    """
                    
                    try:
                        client = OpenAI(api_key=OPENAI_API_KEY_USER)
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",  # Ou "gpt-4o"
                            messages=[
                                {"role": "system", "content": "Você é um assistente especialista em trading esportivo."},
                                {"role": "user", "content": contexto_prompt}
                            ]
                        )
                        resposta_ia = response.choices[0].message.content
                    except Exception as e:
                        resposta_ia = f"⚠️ Erro ao consultar a API da OpenAI: {str(e)}"
                    
                    st.markdown(resposta_ia)
                    st.session_state.messages_openai.append({"role": "assistant", "content": resposta_ia})
