import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Painel Pro - Plantéis Completos Série A", layout="wide")

st.title("⚽ Painel Analisador Esportivo Pro - Elencos & H2H Real")
st.write("Dados 100% extraídos da API-Football (Elencos atualizados, estatísticas de jogadores e H2H).")

# --- CONFIGURAÇÃO DA API ---
API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"
LEAGUE_ID = 71  # ID Oficial do Brasileirão Série A na API
SEASON = 2024   # Mude para 2025 ou 2026 conforme a virada do calendário da API

st.sidebar.success("✅ Painel Integrado via API!")
st.sidebar.markdown("---")
st.sidebar.markdown("### 👨‍💻 Painel Desenvolvido por:")
st.sidebar.markdown("**Thiago Oliveira De sá**")
st.sidebar.markdown("📧 `thiago.desa@yahoo.com.br`")
st.sidebar.markdown("📞 `(21) 96485-9482`")
st.sidebar.markdown("---")

# IDs oficiais da API-Football
TEAM_IDS = {
    'Flamengo': 127, 'Palmeiras': 121, 'Botafogo': 120, 'São Paulo': 126,
    'Fluminense': 128, 'Atlético-MG': 114, 'Internacional': 119, 'Grêmio': 130,
    'Bahia': 115, 'Cruzeiro': 131, 'Vasco': 132, 'Corinthians': 133,
    'Fortaleza': 140, 'Bragantino': 151, 'Athletico-PR': 135, 'Cuiabá': 1900,
    'Juventude': 138, 'Criciúma': 144, 'Atlético-GO': 116, 'Vitória': 147
}

# --- FUNÇÕES DE BUSCA NA API (COM CACHE DE 1 HORA PARA ECONOMIZAR REQUISIÇÕES) ---

@st.cache_data(ttl=3600)
def buscar_estatisticas_time(team_id, season, key):
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
        
    # Retorno padrão caso falhe
    return {'jogos': 0, 'gols_feitos_media': 0.0, 'gols_sofridos_media': 0.0, 'clean_sheets': 0}


@st.cache_data(ttl=3600)
def buscar_elenco_api(team_id, season, key):
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    jogadores = []
    
    # A API divide os jogadores em páginas (normalmente 2 páginas cobrem o elenco todo)
    for page in [1, 2]:
        url = f"https://v3.football.api-sports.io/players?league={LEAGUE_ID}&season={season}&team={team_id}&page={page}"
        try:
            res = requests.get(url, headers=headers)
            data = res.json()
            if data.get('results', 0) > 0:
                for item in data['response']:
                    p = item['player']
                    # Estatísticas específicas desta liga/temporada
                    s = item['statistics'][0] if len(item['statistics']) > 0 else {}
                    
                    jogadores.append({
                        'Jogador': p.get('name', 'N/A'),
                        'Idade': p.get('age', '-'),
                        'Posição': s.get('games', {}).get('position', '-'),
                        'Jogos': s.get('games', {}).get('appearences', 0) or 0,
                        'Minutos': s.get('games', {}).get('minutes', 0) or 0,
                        'Gols': s.get('goals', {}).get('total', 0) or 0,
                        'Assist': s.get('goals', {}).get('assists', 0) or 0,
                        'Finalizações': s.get('shots', {}).get('total', 0) or 0,
                        'Desarmes': s.get('tackles', {}).get('total', 0) or 0,
                        'Amarelos': s.get('cards', {}).get('yellow', 0) or 0,
                        'Vermelhos': s.get('cards', {}).get('red', 0) or 0
                    })
            else:
                break # Fim das páginas
        except Exception as e:
            st.error(f"Erro API (Jogadores): {e}")
            break
            
    df = pd.DataFrame(jogadores)
    if not df.empty:
        df = df.drop_duplicates(subset=['Jogador'])
        # Filtrar apenas quem jogou para não mostrar atletas que não entraram em campo e ordernar por minutos jogados
        df = df[df['Jogos'] > 0].sort_values(by='Minutos', ascending=False)
    return df


@st.cache_data(ttl=3600)
def buscar_h2h_api(time1, time2, key):
    id1, id2 = TEAM_IDS.get(time1), TEAM_IDS.get(time2)
    url = f"https://v3.football.api-sports.io/fixtures/headtohead?h2h={id1}-{id2}"
    headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': key}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if response.status_code == 200 and data.get('results', 0) > 0:
            fixtures = data['response']
            # Pega os 6 últimos confrontos
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


# --- INTERFACE E PROCESSAMENTO DO DASHBOARD ---

st.sidebar.header("⚙️ Configurações de Análise")
times_disponiveis = list(TEAM_IDS.keys())

time_principal = st.sidebar.selectbox("Escolha o Time Principal", times_disponiveis)
adversario = st.sidebar.selectbox("Escolha o Time Adversário", [t for t in times_disponiveis if t != time_principal])

# Buscando dados ao vivo apenas dos dois times selecionados!
with st.spinner("Extraindo dados da API..."):
    id_time1 = TEAM_IDS[time_principal]
    id_time2 = TEAM_IDS[adversario]
    
    stats_t1 = buscar_estatisticas_time(id_time1, SEASON, API_KEY_FIXA)
    stats_t2 = buscar_estatisticas_time(id_time2, SEASON, API_KEY_FIXA)
    df_elenco = buscar_elenco_api(id_time1, SEASON, API_KEY_FIXA)

# --- SEÇÃO 1: DESEMPENHO COLETIVO ---
st.subheader(f"📊 Desempenho Coletivo (Temporada {SEASON}): {time_principal}")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Jogos Disputados", stats_t1['jogos'])
with c2:
    st.metric("Média Gols Feitos", f"{stats_t1['gols_feitos_media']:.2f}")
with c3:
    st.metric("Média Gols Sofridos", f"{stats_t1['gols_sofridos_media']:.2f}")
with c4:
    st.metric("Clean Sheets (Jogos sem sofrer gol)", stats_t1['clean_sheets'])

st.markdown("---")

# --- SEÇÃO 2: SCOUT DO PLANTEL (API REAL) ---
st.subheader(f"👤 Plantel Atualizado via API: {time_principal}")
st.caption("A tabela exibe apenas jogadores que entraram em campo nesta temporada, ordenados pelos minutos jogados.")
if not df_elenco.empty:
    st.dataframe(df_elenco, use_container_width=True, hide_index=True)
else:
    st.warning("Não foi possível carregar os jogadores. Verifique se a temporada já iniciou ou se a chave da API está correta.")

st.markdown("---")

# --- SEÇÃO 3: SIMULADOR DE CONFRONTO DIRETO & HISTÓRICO ---
st.subheader("🤖 Simulador de Confronto Direto Estimado")

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

if total_gols >= 2.5:
    st.success(f"🔥 **Tendência:** Alta probabilidade de **Mais de 2.5 Gols** (Média somada de ataques/defesas indica jogo aberto).")
else:
    st.warning(f"🛡️ **Tendência:** Jogo truncado, tendência de **Menos de 2.5 Gols** (Defesas fortes ou ataques ineficientes).")

st.markdown(f"### 📜 Histórico Real de Confronto (Últimos Jogos): {time_principal} vs {adversario}")

df_h2h_real, erro_api = buscar_h2h_api(time_principal, adversario, API_KEY_FIXA)

if df_h2h_real is not None and not df_h2h_real.empty:
    st.dataframe(df_h2h_real, use_container_width=True, hide_index=True)
else:
    st.info(erro_api if erro_api else "Sem dados recentes de H2H na API.")
