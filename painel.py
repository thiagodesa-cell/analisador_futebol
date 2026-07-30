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
TELEGRAM_CHAT_ID = "-1004464226419"

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
    LEAGUE_ID = 78

st.sidebar.success(f"✅ Ativo: {opcao_liga} (Temporada {SEASON})!")
st.sidebar.info(f"🔄 Última atualização base: {CHAVE_ATUALIZACAO} às 08:00")
st.sidebar.markdown("---")
st.sidebar.markdown("### 👨‍💻 Painel Desenvolvido por:")
st.sidebar.markdown("**Thiago Oliveira De sá**")
st.sidebar.markdown("📧 `thiago.desa@yahoo.com.br`")
st.sidebar.markdown("📞 `(21) 96485-9482`")
st.sidebar.markdown("---")

st.title(f"⚽ Painel Analisador Esportivo Pro - {opcao_liga}")
st.write(f"Dados integrados em tempo real via API-Football para a competição {opcao_liga}.")


# --- FUNÇÃO DE ENVIO PARA O TELEGRAM ---
def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload)
        return res.status_code == 200
    except:
        return False


# --- FUNÇÕES DE BUSCA NA API (COM CACHE EM DISCO PERSISTENTE) ---

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
                match_date = date_str[:10]
                match_time = date_str[11:16]
                status = f['fixture']['status']['short']
                home_name = f['teams']['home']['name']
                away_name = f['teams']['away']['name']
                goals_home = f['goals']['home']
                goals_away = f['goals']['away']
                
                placar_str = f"{goals_home} x {goals_away}" if goals_home is not None else "vs"
                round_name = f['league'].get('round', 'Rodada')
                
                jogos_lista.append({
                    'Data': f"{match_date[8:10]}/{match_date[5:7]}/{match_date[0:4]}",
                    'Horário': match_time,
                    'Rodada': round_name,
                    'Mandante': home_name,
                    'Placar': placar_str,
                    'Visitante': away_name,
                    'Status': status
                })
            return pd.DataFrame(jogos_lista)
    except:
        pass
    return pd.DataFrame()

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
    detalhes = []
    try:
        res = requests.get(url_fixtures, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            for f in data['response']:
                f_id = f['fixture']['id']
                is_home = (f['teams']['home']['id'] == team_id)
                adv = f['teams']['away']['name'] if is_home else f['teams']['home']['name']
                dt = f['fixture']['date'][:10]
                
                g_home = f['goals']['home'] if f['goals']['home'] is not None else 0
                g_away = f['goals']['away'] if f['goals']['away'] is not None else 0
                g_pro = g_home if is_home else g_away
                g_contra = g_away if is_home else g_home
                placar_real = f"{g_home} x {g_away}"
                
                time.sleep(0.15)
                res_s = requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={f_id}", headers=headers)
                data_s = res_s.json()
                
                if data_s.get('results', 0) > 0:
                    t_corners, o_corners = 0, 0
                    for item in data_s['response']:
                        c_val = next((int(s['value']) for s in item['statistics'] if s['type'] == 'Corner Kicks' and s['value'] is not None), 0)
                        if item['team']['id'] == team_id: t_corners = c_val
                        else: o_corners = c_val
                    
                    if is_home:
                        cantos_pro_casa.append(t_corners)
                        cantos_contra_casa.append(o_corners)
                    else:
                        cantos_pro_fora.append(t_corners)
                        cantos_contra_fora.append(o_corners)
                    
                    detalhes.append({
                        'Data': f"{dt[8:10]}/{dt[5:7]}/{dt[0:4]}", 'Adversário': adv,
                        'Mando': 'Casa' if is_home else 'Fora', 'Placar': placar_real,
                        'Gols Marcados': g_pro, 'Gols Sofridos': g_contra,
                        'Cantos Pró': t_corners, 'Cantos Contra': o_corners, 'Total Cantos': t_corners + o_corners
                    })
        return {
            'corners_for_geral': (sum(cantos_pro_casa+cantos_pro_fora)/max(len(cantos_pro_casa+cantos_pro_fora),1)),
            'corners_ag_geral': (sum(cantos_contra_casa+cantos_contra_fora)/max(len(cantos_contra_casa+cantos_contra_fora),1)),
            'corners_for_home': sum(cantos_pro_casa)/max(len(cantos_pro_casa),1), 'corners_ag_home': sum(cantos_contra_casa)/max(len(cantos_contra_casa),1),
            'corners_for_away': sum(cantos_pro_fora)/max(len(cantos_pro_fora),1), 'corners_ag_away': sum(cantos_contra_fora)/max(len(cantos_contra_fora),1),
            'df_historico': pd.DataFrame(detalhes)
        }
    except:
        return {'corners_for_geral':0.0,'corners_ag_geral':0.0,'corners_for_home':0.0,'corners_ag_home':0.0,'corners_for_away':0.0,'corners_ag_away':0.0,'df_historico':pd.DataFrame()}

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
def buscar_minutagem_u4(team_id, league_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&team={team_id}&last=4"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    
    intervalos = ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90"]
    gols_dict = {i: {"Gols Feitos": 0, "Gols Sofridos": 0} for i in intervalos}
    cartoes_dict = {i: {"Cartões Amarelos": 0} for i in intervalos}
    
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get('results', 0) > 0:
            for f in data['response']:
                f_id = f['fixture']['id']
                time.sleep(0.15)
                res_e = requests.get(f"https://v3.football.api-sports.io/fixtures/events?fixture={f_id}", headers=headers)
                data_e = res_e.json()
                
                if data_e.get('results', 0) > 0:
                    for ev in data_e['response']:
                        minuto = ev.get('time', {}).get('elapsed')
                        if minuto is None:
                            continue
                        
                        if 0 <= minuto <= 15: inter = "0-15"
                        elif 16 <= minuto <= 30: inter = "16-30"
                        elif 31 <= minuto <= 45: inter = "31-45"
                        elif 46 <= minuto <= 60: inter = "46-60"
                        elif 61 <= minuto <= 75: inter = "61-75"
                        else: inter = "76-90"
                        
                        ev_type = ev.get('type')
                        ev_team_id = ev.get('team', {}).get('id')
                        
                        if ev_type == 'Goal':
                            if ev_team_id == team_id:
                                gols_dict[inter]["Gols Feitos"] += 1
                            else:
                                gols_dict[inter]["Gols Sofridos"] += 1
                        elif ev_type == 'Card' and 'Yellow' in str(ev.get('detail', '')):
                            if ev_team_id == team_id:
                                cartoes_dict[inter]["Cartões Amarelos"] += 1
                                
        df_gols = pd.DataFrame([{"Intervalo": f"{k} min", "Gols Feitos": v["Gols Feitos"], "Gols Sofridos": v["Gols Sofridos"]} for k, v in gols_dict.items()])
        df_cartoes = pd.DataFrame([{"Intervalo": f"{k} min", "Cartões Amarelos": v["Cartões Amarelos"]} for k, v in cartoes_dict.items()])
        return df_gols, df_cartoes
    except:
        df_gols = pd.DataFrame([{"Intervalo": f"{k} min", "Gols Feitos": 0, "Gols Sofridos": 0} for k in intervalos])
        df_cartoes = pd.DataFrame([{"Intervalo": f"{k} min", "Cartões Amarelos": 0} for k in intervalos])
        return df_gols, df_cartoes

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
            rows = [{
                'Data': f"{m['fixture']['date'][8:10]}/{m['fixture']['date'][5:7]}/{m['fixture']['date'][0:4]}",
                'Competição': m['league']['name'], 'Mandante': m['teams']['home']['name'],
                'Placar': f"{m['goals']['home']} x {m['goals']['away']}", 'Visitante': m['teams']['away']['name']
            } for m in sorted(data['response'], key=lambda x: x['fixture']['date'], reverse=True)[:6]]
            return pd.DataFrame(rows), None
    except:
        pass
    return None, "Sem confrontos recentes."

# --- CARREGAMENTO INICIAL DINÂMICO ---
TEAM_IDS = buscar_times_por_liga(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)

if not TEAM_IDS:
    st.warning(f"⚠️ Não foi possível carregar os times da competição selecionada.")
    st.stop()

st.sidebar.header("⚙️ Configurações de Análise")
times_disponiveis = sorted(list(TEAM_IDS.keys()))
time_principal = st.sidebar.selectbox("Escolha o Time", times_disponiveis)

with st.spinner(f"Extraindo dados reais de {opcao_liga}..."):
    id_time1 = TEAM_IDS[time_principal]
    stats_t1 = buscar_estatisticas_time(id_time1, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    corners_t1 = buscar_medias_escanteios(id_time1, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_elenco_u5, string_forma_t1 = buscar_scout_elenco_u5(id_time1, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_tabela = buscar_tabela_classificacao(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_arbitros = buscar_dados_arbitros(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    df_jogos_liga = buscar_jogos_liga(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    rodada_atual_str = buscar_rodada_atual(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    
    # Executa a busca cirúrgica de minutagem baseada nos últimos 4 confrontos
    df_min_gols_u4, df_cartoes_u4 = buscar_minutagem_u4(id_time1, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)

# --- ABAS DE NAVEGAÇÃO SUPERIOR ---
aba_painel, aba_jogos_dia, aba_arbitros, aba_tabela = st.tabs([
    "📊 Painel de Análise & Elenco", "📅 Jogos & Rodada", "⚖️ Árbitros", f"🏆 Tabela ({opcao_liga})"
])

with aba_tabela:
    st.subheader(f"🏆 Classificação Atual - {opcao_liga} ({SEASON})")
    if not df_tabela.empty:
        st.dataframe(df_tabela, use_container_width=True, hide_index=True)

with aba_jogos_dia:
    st.subheader(f"📅 Calendário e Partidas da Rodada - {opcao_liga}")
    if not df_jogos_liga.empty:
        filtro_opcao = st.radio("Filtrar visualização:", ["Ver Jogos da Rodada Atual", "Ver Todos os Jogos da Temporada"], horizontal=True)
        df_exibir = df_jogos_liga.copy()
        if filtro_opcao == "Ver Jogos da Rodada Atual":
            if rodada_atual_str:
                df_exibir = df_exibir[df_exibir['Rodada'] == rodada_atual_str]
                st.success(f"📌 Exibindo jogos da **{rodada_atual_str}**")
        if not df_exibir.empty:
            st.dataframe(df_exibir[['Data', 'Horário', 'Rodada', 'Mandante', 'Placar', 'Visitante', 'Status']], use_container_width=True, hide_index=True)

with aba_arbitros:
    st.subheader(f"⚖️ Perfil dos Árbitros - {opcao_liga}")
    if not df_arbitros.empty:
        st.dataframe(df_arbitros, use_container_width=True, hide_index=True)

with aba_painel:
    st.subheader(f"📊 Análise Estruturada de Rendimento: {time_principal}")
    st.markdown(f"**Forma Recente (Últimas 5 partidas):** {string_forma_t1}")
    
    rg1, rg2, rg3 = st.columns(3)
    rg1.metric("Jogos Disputados na Temporada", stats_t1['jogos'])
    rg2.metric("Jogos sem Sofrer Gols (Clean Sheets)", stats_t1['clean_sheets'])
    rg3.markdown("💡 *As tabelas abaixo mostram os mesmos últimos 10 confrontos cruzando dados sob duas perspectivas.*")
    
    st.markdown("---")
    
    col_esquerda_gols, col_direita_cantos = st.columns(2)
    
    with col_esquerda_gols:
        st.markdown("### ⚽ Estatísticas e Histórico de Gols")
        g_col1, g_col2 = st.columns(2)
        g_col1.metric("Média Gols Feitos (Geral)", f"{stats_t1['gols_feitos_media']:.2f}")
        g_col2.metric("Média Gols Sofridos (Geral)", f"{stats_t1['gols_sofridos_media']:.2f}")
        g_col3, g_col4 = st.columns(2)
        g_col3.metric("Mando Casa (Pró / Contra)", f"{stats_t1['gf_home']:.2f} / {stats_t1['ga_home']:.2f}")
        g_col4.metric("Mando Fora (Pró / Contra)", f"{stats_t1['gf_away']:.2f} / {stats_t1['ga_away']:.2f}")
        
        if not corners_t1['df_historico'].empty:
            st.markdown("**Últimas 10 Partidas (Histórico de Placares & Gols):**")
            st.dataframe(corners_t1['df_historico'][['Data', 'Adversário', 'Mando', 'Placar', 'Gols Marcados', 'Gols Sofridos']], use_container_width=True, hide_index=True)

    with col_direita_cantos:
        st.markdown("### 🚩 Estatísticas e Histórico de Escanteios")
        e_col1, e_col2 = st.columns(2)
        e_col1.metric("Cantos Pró (Média Geral)", f"{corners_t1['corners_for_geral']:.2f}")
        e_col2.metric("Cantos Contra (Média Geral)", f"{corners_t1['corners_ag_geral']:.2f}")
        e_col3, e_col4 = st.columns(2)
        e_col3.metric("Mando Casa (Pró / Contra)", f"{corners_t1['corners_for_home']:.2f} / {corners_t1['corners_ag_home']:.2f}")
        e_col4.metric("Mando Fora (Pró / Contra)", f"{corners_t1['corners_for_away']:.2f} / {corners_t1['corners_ag_away']:.2f}")
        
        if not corners_t1['df_historico'].empty:
            st.markdown("**Últimas 10 Partidas (Histórico de Tiros de Canto):**")
            st.dataframe(corners_t1['df_historico'][['Data', 'Adversário', 'Mando', 'Cantos Pró', 'Cantos Contra', 'Total Cantos']], use_container_width=True, hide_index=True)
            
    st.markdown("---")
    
    # --- EXIBIÇÃO DA MINUTAGEM DINÂMICA DOS ÚLTIMOS 4 JOGOS ---
    col_min1, col_min2 = st.columns(2)
    with col_min1:
        st.subheader("⏱️ Minutagem de Gols (Últimos 4 Jogos)")
        st.caption("Contagem real de gols feitos e sofridos por faixa de tempo nos 4 jogos mais recentes.")
        if not df_min_gols_u4.empty:
            st.dataframe(df_min_gols_u4, use_container_width=True, hide_index=True)
            
    with col_min2:
        st.subheader("🟨 Minutagem de Cartões (Últimos 4 Jogos)")
        st.caption("Volume real de cartões amarelos recebidos pelo time por faixa de tempo nos 4 jogos mais recentes.")
        if not df_cartoes_u4.empty:
            st.dataframe(df_cartoes_u4, use_container_width=True, hide_index=True)
            
    st.markdown("---")
    st.subheader(f"👤 Scout do Plantel (Média Móvel U5): {time_principal}")
    if not df_elenco_u5.empty:
        st.dataframe(df_elenco_u5, use_container_width=True, hide_index=True)
        
    st.markdown("---")
    st.subheader("🤖 Simulador de Confronto Direto & H2H")
    usar_comparacao = st.checkbox("Ativar comparação e simulação contra um adversário")
    
    if usar_comparacao:
        adversario = st.selectbox("Escolha o Time Adversário", [t for t in times_disponiveis if t != time_principal])
        if adversario:
            id_time2 = TEAM_IDS[adversario]
            stats_t2 = buscar_estatisticas_time(id_time2, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            corners_t2 = buscar_medias_escanteios(id_time2, LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            
            gols_t1 = (stats_t1['gf_home'] + stats_t2['ga_away']) / 2
            gols_t2 = (stats_t2['gf_away'] + stats_t1['ga_home']) / 2
            total_gols = gols_t1 + gols_t2
            
            c_proj_t1 = (corners_t1['corners_for_home'] + corners_t2['corners_ag_away']) / 2
            c_proj_t2 = (corners_t2['corners_for_away'] + corners_t1['corners_ag_home']) / 2
            escanteios_jogo = c_proj_t1 + c_proj_t2
            
            total_cartoes = 4.0 
            
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric(f"Expec. Gols ({time_principal})", f"{gols_t1:.2f}")
            sc2.metric(f"Expec. Gols ({adversario})", f"{gols_t2:.2f}")
            sc3.metric("Total de Gols Esperados", f"{total_gols:.2f}")
            sc4.metric("Média Estimada de Cantos", f"{escanteios_jogo:.1f}")
            
            st.markdown("---")
            st.markdown("### 💡 Smart Tipster: Sugestões de Apostas Automatizadas")
            tip_c1, tip_c2 = st.columns(2)
            
            with tip_c1:
                with st.container(border=True):
                    st.markdown("#### ⚽ Mercado de Gols & Projeções")
                    st.markdown(f"- **Projeção Total:** `{total_gols:.2f}` gols")
                    st.markdown(f"- **Sugestão Principal:** `Mais de 2.5 Gols` 🔥" if total_gols >= 2.5 else "`Mais de 1.5 Gols` ⚡" if total_gols >= 1.5 else "`Menos de 2.5 Gols` 🛡️")
                    st.markdown(f"- **Ambas Marcam (BTTS):** `Sim` ✅" if gols_t1 >= 0.95 and gols_t2 >= 0.95 else "`Não` ❌")
                with st.container(border=True):
                    st.markdown("#### 🚩 Projeção Fina de Escanteios")
                    st.markdown(f"- **Total Estimado da Partida:** `{escanteios_jogo:.1f}` cantos")
                    st.markdown(f"- **Sugestão:** `Mais de 9.5 Escanteios` 🔥" if escanteios_jogo >= 9.8 else "`Mais de 8.5 Escanteios` ⚡" if escanteios_jogo >= 8.8 else "`Menos de 10.5 Escanteios` 🛡️")
            
            with tip_c2:
                with st.container(border=True):
                    st.markdown("#### 🟨 Mercado de Cartões Real")
                    st.markdown(f"- **Projeção Total da Partida:** `{total_cartoes:.2f}` cartões")
                    st.markdown(f"- **Sugestão de Entrada:** `Mais de 4.5 Cartões Amarelos` 🟨" if total_cartoes >= 4.5 else "`Mais de 3.5 Cartões Amarelos` 🟨" if total_cartoes >= 3.5 else "`Menos de 4.5 Cartões Amarelos` 🛡️")
                with st.container(border=True):
                    st.markdown("#### 🔥 Bilhete Estruturado (Base Matemática)")
                    opcoes_combo = ["Mais de 1.5 Gols" if total_gols >= 1.6 else "Menos de 3.5 Gols", "Mais de 8.5 Escanteios" if escanteios_jogo >= 9.0 else f"Mais de 3.5 Cantos para o {time_principal if c_proj_t1>c_proj_t2 else adversario}"]
                    for idx, opt in enumerate(opcoes_combo, 1): st.markdown(f"{idx}. `{opt}`")
            
            st.markdown("---")
            st.markdown(f"### 📜 Histórico Real de Confronto H2H")
            df_h2h, _ = buscar_h2h_api(id_time1, id_time2, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            if df_h2h is not None: st.dataframe(df_h2h, use_container_width=True, hide_index=True)

# --- DISPARADOR DO TELEGRAM ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 📢 Enviar Análise para o Telegram")
if st.sidebar.button("🚀 Disparar Alerta Pré-Live"):
    if usar_comparacao and adversario:
        g_t1 = (stats_t1['gf_home'] + stats_t2['ga_away']) / 2
        g_t2 = (stats_t2['gf_away'] + stats_t1['ga_home']) / 2
        c_proj_t1 = (corners_t1['corners_for_home'] + corners_t2['corners_ag_away']) / 2
        c_proj_t2 = (corners_t2['corners_for_away'] + corners_t1['corners_ag_home']) / 2
        
        msg = f"""🚨 <b>RAIO-X PRÉ-LIVE PRO</b> 🚨\n\n⚽ <b>{time_principal} x {adversario}</b>\n🏆 Competição: {opcao_liga}\n\n📊 <b>PROJEÇÃO DE GOLS:</b>\n• Total Estimado: {g_t1+g_t2:.2f} gols\n• Ambas Marcam: {"Sim ✅" if g_t1>=0.95 and g_t2>=0.95 else "Não ❌"}\n\n🚩 <b>ESCANTEIOS:</b>\n• Total Estimado: {c_proj_t1+c_proj_t2:.1f} cantos"""
    else:
        msg = f"""🚨 <b>RAIO-X INDIVIDUAL</b> 🚨\n\n⚽ <b>Time: {time_principal}</b>\n🏆 Competição: {opcao_liga}"""
    
    if enviar_alerta_telegram(msg): st.sidebar.success("🎉 Alerta enviado para o Telegram!")
    else: st.sidebar.error("❌ Falha ao disparar.")
