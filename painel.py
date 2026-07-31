import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="Smart Tipster Pro - Global Trading & Futebol", layout="wide")

# --- CONFIGURAÇÃO DA API E TELEGRAM ---
API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"
SEASON = datetime.now().year 

TELEGRAM_TOKEN = "8281259090:AAEggXJKpCMxRbhhrcCZymcmNUKWNoOPFfY"
TELEGRAM_CHAT_ID = "-1004464226419"

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        return response.json().get("ok", False)
    except:
        return False

# --- LÓGICA DE ATUALIZAÇÃO ÀS 8H DA MANHÃ ---
def obter_chave_atualizacao():
    agora = datetime.now()
    if agora.hour < 8:
        return (agora - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        return agora.strftime("%Y-%m-%d")

CHAVE_ATUALIZACAO = obter_chave_atualizacao()

# --- BARRA LATERAL: CONFIGURAÇÕES E TELEGRAM ---
st.sidebar.header("⚙️ Configurações & Competição")
opcao_liga = st.sidebar.selectbox(
    "Escolha o campeonato:",
    [
        "Brasileirão Série A", 
        "Brasileirão Série B", 
        "Campeonato Argentino",
        "Premier League (Inglaterra)",
        "La Liga (Espanha)",
        "Bundesliga (Alemanha)",
        "UEFA Champions League",
        "UEFA Liga Europa",
        "UEFA Conference League",
        "Copa Libertadores",
        "Copa Sudamericana"
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
elif opcao_liga == "Bundesliga (Alemanha)":
    LEAGUE_ID = 78
elif opcao_liga == "UEFA Champions League":
    LEAGUE_ID = 2
elif opcao_liga == "UEFA Liga Europa":
    LEAGUE_ID = 3
elif opcao_liga == "UEFA Conference League":
    LEAGUE_ID = 848
elif opcao_liga == "Copa Libertadores":
    LEAGUE_ID = 13
else:
    LEAGUE_ID = 11

# --- DETECÇÃO INTELIGENTE DE TEMPORADA VÁLIDA ---
@st.cache_data(persist="disk")
def descobrir_temporada_valida(league_id, season_atual, key, data_cache):
    for s in [season_atual, season_atual - 1]:
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

SEASON_EFETIVA = descobrir_temporada_valida(LEAGUE_ID, SEASON, API_KEY_FIXA, CHAVE_ATUALIZACAO)

st.sidebar.success(f"✅ Temporada Ativa: {SEASON_EFETIVA}")

# Seção do Telegram (Smart Tipster) na Barra Lateral
st.sidebar.markdown("---")
st.sidebar.header("📤 Smart Tipster (Telegram)")
msg_personalizada = st.sidebar.text_area("Escreva sua análise/palpite para enviar:", placeholder="Ex: Análise forte para o jogo...")
if st.sidebar.button("🚀 Enviar para o Telegram"):
    if msg_personalizada.strip():
        sucesso = enviar_telegram(msg_personalizada)
        if sucesso:
            st.sidebar.success("Mensagem enviada com sucesso!")
        else:
            st.sidebar.error("Erro ao enviar mensagem.")
    else:
        st.sidebar.warning("Digite uma mensagem antes de enviar.")

# --- FUNÇÕES DE BUSCA NA API (COM CACHE EM DISCO) ---

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
                    'Horário': match_time, 'Rodada': round_name,
                    'Mandante': home_name, 'Placar': placar_str, 'Visitante': away_name, 'Status': status
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
def buscar_estatisticas_jogadores_temporada(team_id, season, key, data_cache):
    url = f"https://v3.football.api-sports.io/players?team={team_id}&season={season}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        jogadores_lista = []
        if data.get('results', 0) > 0:
            for p_item in data['response']:
                p_info = p_item['player']
                p_stats = p_item['statistics'][0] if p_item['statistics'] else {}
                
                games = p_stats.get('games', {})
                goals = p_stats.get('goals', {})
                shots = p_stats.get('shots', {})
                fouls = p_stats.get('fouls', {})
                tackles = p_stats.get('tackles', {})
                cards = p_stats.get('cards', {})
                
                jogadores_lista.append({
                    'Nome': p_info['name'],
                    'Idade': p_info.get('age', '-'),
                    'Nacionalidade': p_info.get('nationality', '-'),
                    'Posição': games.get('position', '-'),
                    'Jogos': games.get('appearences', 0) or 0,
                    'Minutos': games.get('minutes', 0) or 0,
                    'Gols': goals.get('total', 0) or 0,
                    'Assistências': goals.get('assists', 0) or 0,
                    'Finalizações': shots.get('total', 0) or 0,
                    'Chutes no Alvo': shots.get('on', 0) or 0,
                    'Faltas Cometidas': fouls.get('committed', 0) or 0,
                    'Faltas Sofridas': fouls.get('drawn', 0) or 0,
                    'Desarmes': tackles.get('total', 0) or 0,
                    'Cartões Amarelos': cards.get('yellow', 0) or 0,
                    'Cartões Vermelhos': cards.get('red', 0) or 0
                })
            return pd.DataFrame(jogadores_lista)
    except:
        pass
    return pd.DataFrame()

# Carregar lista de times da liga ativa
TEAM_IDS = buscar_times_por_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)

if not TEAM_IDS:
    st.warning(f"⚠️ Não foi possível carregar os times da competição selecionada.")
    st.stop()

# --- TELA PRINCIPAL COM ABAS DE PESQUISA POR DIGITAÇÃO E PAINEL ---
st.title(f"⚽ Smart Tipster Pro - {opcao_liga}")
st.write(f"Painel global integrado em tempo real (Temporada {SEASON_EFETIVA}).")

aba_painel, aba_busca_clube, aba_busca_jogador, aba_jogos_dia, aba_arbitros, aba_tabela = st.tabs([
    "📊 Painel Principal & H2H", 
    "🔍 Pesquisa de Clube", 
    "👤 Pesquisa de Jogador", 
    "📅 Jogos & Rodada", 
    "⚖️ Árbitros", 
    f"🏆 Tabela ({opcao_liga})"
])

# 1. ABA DE PESQUISA DE CLUBE (COM CAIXINHA DE DIGITAÇÃO)
with aba_busca_clube:
    st.subheader("🔍 Consulta Individual de Clube na Temporada")
    st.markdown("Digite abaixo o nome do clube que deseja pesquisar:")
    
    termo_clube = st.text_input("Digite o nome do clube:", placeholder="Ex: Flamengo, Arsenal, Boca Juniors...")
    
    if termo_clube:
        times_encontrados = {k: v for k, v in TEAM_IDS.items() if termo_clube.lower() in k.lower()}
        if times_encontrados:
            clube_escolhido = st.selectbox("Selecione o clube correspondente:", list(times_encontrados.keys()))
            id_clube_pesq = times_encontrados[clube_escolhido]
            
            with st.spinner(f"Carregando dados de {clube_escolhido}..."):
                stats_clube = buscar_estatisticas_time(id_clube_pesq, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                corners_clube = buscar_medias_escanteios(id_clube_pesq, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                df_elenco_temp = buscar_estatisticas_jogadores_temporada(id_clube_pesq, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            
            st.markdown(f"### 📊 Relatório: {clube_escolhido} ({SEASON_EFETIVA})")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Jogos Disputados", stats_clube['jogos'])
            c2.metric("Clean Sheets", stats_clube['clean_sheets'])
            c3.metric("Média Gols Feitos", f"{stats_clube['gols_feitos_media']:.2f}")
            c4.metric("Média Gols Sofridos", f"{stats_clube['gols_sofridos_media']:.2f}")
            
            st.markdown("---")
            st.subheader("👥 Elenco e Estatísticas na Temporada")
            if not df_elenco_temp.empty:
                st.dataframe(df_elenco_temp, use_container_width=True, hide_index=True)
            else:
                st.info("Estatísticas de elenco detalhadas indisponíveis para este clube.")
        else:
            st.warning("Nenhum clube encontrado com esse termo na competição atual.")

# 2. ABA DE PESQUISA DE JOGADOR (COM CAIXINHA DE DIGITAÇÃO)
with aba_busca_jogador:
    st.subheader("👤 Consulta Individual de Jogador na Temporada")
    st.markdown("Digite o nome do jogador para buscar estatísticas de finalizações, cartões, desarmes e faltas:")
    
    termo_jogador = st.text_input("Digite o nome do jogador:", placeholder="Ex: Haaland, Pedro, Messi...")
    
    if termo_jogador:
        with st.spinner("Buscando jogadores na competição..."):
            # Varre os principais times para encontrar o jogador digitado
            resultados_jogadores = []
            for nome_t, id_t in list(TEAM_IDS.items())[:15]: # Busca otimizada nos primeiros times ou geral
                df_j = buscar_estatisticas_jogadores_temporada(id_t, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                if not df_j.empty:
                    match_j = df_j[df_j['Nome'].str.contains(termo_jogador, case=False, na=False)]
                    for _, row in match_j.iterrows():
                        row_dict = row.to_dict()
                        row_dict['Clube'] = nome_t
                        resultados_jogadores.append(row_dict)
            
            df_resultado_busca = pd.DataFrame(resultados_jogadores)
            
        if not df_resultado_busca.empty:
            st.success(f"Encontrado(s) {len(df_resultado_busca)} atleta(s)correspondente(s):")
            for _, atleta in df_resultado_busca.iterrows():
                st.markdown(f"---")
                st.markdown(f"### ⚡ {atleta['Nome']} ({atleta['Clube']})")
                
                inf1, inf2, inf3, inf4 = st.columns(4)
                inf1.metric("Posição", atleta['Posição'])
                inf2.metric("Idade / Nação", f"{atleta['Idade']} | {atleta['Nacionalidade']}")
                inf3.metric("Partidas Jogadas", atleta['Jogos'])
                inf4.metric("Minutos em Campo", atleta['Minutos'])
                
                st.markdown("#### 🎯 Estatísticas Principais na Temporada")
                st1, st2, st3, st4 = st.columns(4)
                st1.metric("Gols / Assistências", f"{atleta['Gols']} / {atleta['Assistências']}")
                st2.metric("Finalizações / Alvo", f"{atleta['Finalizações']} / {atleta['Chutes no Alvo']}")
                st3.metric("Faltas (Cometidas/Sofridas)", f"{atleta['Faltas Cometidas']} / {atleta['Faltas Sofridas']}")
                st4.metric("Desarmes / Cartões (Am/Ver)", f"{atleta['Desarmes']} | {atleta['Cartões Amarelos']}/{atleta['Cartões Vermelhos']}")
        else:
            st.warning("Nenhum jogador encontrado com esse nome.")

# 3. ABA PAINEL PRINCIPAL & H2H
with aba_painel:
    time_principal = st.selectbox("Escolha o Time Principal para Análise:", sorted(list(TEAM_IDS.keys())))

    if time_principal:
        id_time1 = TEAM_IDS[time_principal]
        with st.spinner(f"Extraindo dados de {time_principal}..."):
            stats_t1 = buscar_estatisticas_time(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
            corners_t1 = buscar_medias_escanteios(id_time1, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)

        rg1, rg2, rg3 = st.columns(3)
        rg1.metric("Jogos Disputados", stats_t1['jogos'])
        rg2.metric("Clean Sheets", stats_t1['clean_sheets'])
        rg3.markdown("💡 *Simule abaixo o confronto direto.*")
        
        st.markdown("---")
        col_esquerda_gols, col_direita_cantos = st.columns(2)
        
        with col_esquerda_gols:
            st.markdown("### ⚽ Gols")
            g_col1, g_col2 = st.columns(2)
            g_col1.metric("Média Gols Feitos", f"{stats_t1['gols_feitos_media']:.2f}")
            g_col2.metric("Média Gols Sofridos", f"{stats_t1['gols_sofridos_media']:.2f}")
            
            if not corners_t1['df_historico'].empty:
                st.markdown("**Últimas Partidas (Gols):**")
                st.dataframe(corners_t1['df_historico'][['Data', 'Adversário', 'Mando', 'Placar']], use_container_width=True, hide_index=True)

        with col_direita_cantos:
            st.markdown("### 🚩 Escanteios")
            e_col1, e_col2 = st.columns(2)
            e_col1.metric("Cantos Pró (Média)", f"{corners_t1['corners_for_geral']:.2f}")
            e_col2.metric("Cantos Contra (Média)", f"{corners_t1['corners_ag_geral']:.2f}")
            
            if not corners_t1['df_historico'].empty:
                st.markdown("**Últimas Partidas (Cantos):**")
                st.dataframe(corners_t1['df_historico'][['Data', 'Adversário', 'Cantos Pró', 'Cantos Contra', 'Total Cantos']], use_container_width=True, hide_index=True)
                
        st.markdown("---")
        st.subheader("🤖 Simulador de Confronto Direto & H2H")
        usar_comparacao = st.checkbox("Ativar simulação contra adversário")
        
        if usar_comparacao:
            adversario = st.selectbox("Escolha o Adversário", [t for t in sorted(list(TEAM_IDS.keys())) if t != time_principal])
            if adversario:
                id_time2 = TEAM_IDS[adversario]
                stats_t2 = buscar_estatisticas_time(id_time2, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                corners_t2 = buscar_medias_escanteios(id_time2, LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
                
                gols_t1 = (stats_t1['gf_home'] + stats_t2['ga_away']) / 2
                gols_t2 = (stats_t2['gf_away'] + stats_t1['ga_home']) / 2
                total_gols = gols_t1 + gols_t2
                
                sc1, sc2, sc3 = st.columns(3)
                sc1.metric(f"Exp. Gols ({time_principal})", f"{gols_t1:.2f}")
                sc2.metric(f"Exp. Gols ({adversario})", f"{gols_t2:.2f}")
                sc3.metric("Total Gols Esperados", f"{total_gols:.2f}")

# 4. ABA DE JOGOS DA RODADA
with aba_jogos_dia:
    st.subheader("📅 Calendário de Partidas")
    df_jogos_liga = buscar_jogos_liga(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    rodada_atual_str = buscar_rodada_atual(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    if not df_jogos_liga.empty:
        filtro_opcao = st.radio("Filtrar:", ["Jogos da Rodada Atual", "Todos os Jogos"], horizontal=True)
        df_exibir = df_jogos_liga.copy()
        if filtro_opcao == "Jogos da Rodada Atual" and rodada_atual_str:
            df_exibir = df_exibir[df_exibir['Rodada'] == rodada_atual_str]
        st.dataframe(df_exibir, use_container_width=True, hide_index=True)

# 5. ABA DE ÁRBITROS
with aba_arbitros:
    st.subheader("⚖️ Perfil dos Árbitros")
    df_arbitros = buscar_dados_arbitros(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    if not df_arbitros.empty:
        st.dataframe(df_arbitros, use_container_width=True, hide_index=True)

# 6. ABA DE TABELA
with aba_tabela:
    st.subheader("🏆 Tabela de Classificação")
    df_tabela = buscar_tabela_classificacao(LEAGUE_ID, SEASON_EFETIVA, API_KEY_FIXA, CHAVE_ATUALIZACAO)
    if not df_tabela.empty:
        st.dataframe(df_tabela, use_container_width=True, hide_index=True)
