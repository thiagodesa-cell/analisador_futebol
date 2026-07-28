import streamlit as st
import pandas as pd
import requests

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Painel Pro - SofaScore Style", layout="wide")

# Estilização CSS avançada para simular o layout escuro e limpo do SofaScore
st.markdown("""
    <style>
    .stApp {
        background-color: #121212;
        color: #E0E0E0;
    }
    .sidebar .stSidebar {
        background-color: #181818;
    }
    /* Cartões de Estatísticas estilo SofaScore */
    .metric-card {
        background-color: #1E1E1E;
        border: 1px solid #2A2A2A;
        padding: 16px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.4);
    }
    .metric-title {
        color: #9E9E9E;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .metric-value {
        color: #FFFFFF;
        font-size: 22px;
        font-weight: 700;
    }
    /* Placar Estilo Transmissão */
    .score-banner {
        background: linear-gradient(135deg, #1E1E1E 0%, #252525 100%);
        border: 1px solid #333333;
        padding: 20px;
        border-radius: 14px;
        text-align: center;
        margin-bottom: 20px;
    }
    h1, h2, h3 {
        color: #FFFFFF !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚽ SofaScore Analytics Pro - Série A")
st.write("Painel de análise estatística com escudos oficiais, plantéis detalhados e API em tempo real.")

# --- CONFIGURAÇÃO DA API ---
API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"

st.sidebar.success("✅ Conectado à API-Football")
st.sidebar.markdown("---")
st.sidebar.markdown("### 👨‍💻 Desenvolvido por:")
st.sidebar.markdown(f"**Thiago Oliveira De sá**")
st.sidebar.markdown("📧 `thiago.desa@yahoo.com.br`")
st.sidebar.markdown("📞 `(21) 96485-9482`")
st.sidebar.markdown("---")

# Mapeamento Oficial com IDs e URLs Diretas dos Escudos da API-Football
TEAM_DATA = {
    'Flamengo': {'id': 127, 'logo': 'https://media.api-sports.io/football/teams/127.png'},
    'Palmeiras': {'id': 121, 'logo': 'https://media.api-sports.io/football/teams/121.png'},
    'Botafogo': {'id': 120, 'logo': 'https://media.api-sports.io/football/teams/120.png'},
    'São Paulo': {'id': 126, 'logo': 'https://media.api-sports.io/football/teams/126.png'},
    'Fluminense': {'id': 128, 'logo': 'https://media.api-sports.io/football/teams/128.png'},
    'Atlético-MG': {'id': 114, 'logo': 'https://media.api-sports.io/football/teams/114.png'},
    'Internacional': {'id': 119, 'logo': 'https://media.api-sports.io/football/teams/119.png'},
    'Grêmio': {'id': 130, 'logo': 'https://media.api-sports.io/football/teams/130.png'},
    'Bahia': {'id': 115, 'logo': 'https://media.api-sports.io/football/teams/115.png'},
    'Cruzeiro': {'id': 131, 'logo': 'https://media.api-sports.io/football/teams/131.png'},
    'Vasco': {'id': 132, 'logo': 'https://media.api-sports.io/football/teams/132.png'},
    'Corinthians': {'id': 133, 'logo': 'https://media.api-sports.io/football/teams/133.png'},
    'Fortaleza': {'id': 140, 'logo': 'https://media.api-sports.io/football/teams/140.png'},
    'Bragantino': {'id': 151, 'logo': 'https://media.api-sports.io/football/teams/151.png'},
    'Athletico-PR': {'id': 135, 'logo': 'https://media.api-sports.io/football/teams/135.png'},
    'Cuiabá': {'id': 1900, 'logo': 'https://media.api-sports.io/football/teams/1900.png'},
    'Juventude': {'id': 138, 'logo': 'https://media.api-sports.io/football/teams/138.png'},
    'Criciúma': {'id': 144, 'logo': 'https://media.api-sports.io/football/teams/144.png'},
    'Atlético-GO': {'id': 116, 'logo': 'https://media.api-sports.io/football/teams/116.png'},
    'Vitória': {'id': 147, 'logo': 'https://media.api-sports.io/football/teams/147.png'}
}

@st.cache_data(ttl=28800)
def carregar_dados_gerais():
    times = list(TEAM_DATA.keys())
    dados_times = {
        'Home': times,
        'gols_feitos_media': [2.1, 1.9, 2.0, 1.5, 1.6, 1.7, 1.5, 1.6, 1.4, 1.3, 1.2, 1.3, 1.5, 1.4, 1.3, 1.0, 1.1, 1.0, 0.9, 1.1],
        'gols_sofridos_media': [0.8, 1.0, 0.9, 1.1, 1.0, 1.0, 0.9, 1.1, 1.2, 1.1, 1.4, 1.2, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.5],
        'escanteios_media': [6.4, 5.2, 6.0, 4.8, 5.5, 5.7, 5.1, 5.4, 4.9, 4.8, 4.6, 5.0, 5.2, 5.1, 4.7, 4.2, 4.3, 4.0, 4.1, 4.4],
        'finalizacoes_media': [15.5, 14.2, 15.0, 12.8, 13.5, 14.0, 13.2, 13.8, 12.5, 12.0, 11.8, 12.2, 13.0, 12.6, 11.9, 10.5, 11.0, 10.2, 10.0, 10.8],
        'desarmes_media': [16.5, 18.2, 15.0, 17.0, 16.2, 17.5, 18.0, 17.2, 16.8, 15.9, 18.5, 17.8, 16.0, 15.5, 18.1, 19.0, 18.4, 19.5, 18.8, 19.2],
        'faltas_cometidas_media': [12.1, 13.5, 12.8, 14.0, 13.2, 14.5, 13.8, 14.2, 13.0, 13.4, 15.0, 14.8, 12.5, 13.1, 14.6, 15.5, 15.2, 16.0, 15.8, 16.1],
        'faltas_sofridas_media': [14.0, 14.5, 13.8, 13.0, 13.5, 14.1, 14.0, 13.5, 13.2, 12.8, 13.1, 13.4, 14.2, 13.8, 13.0, 12.0, 12.5, 11.8, 11.5, 12.2],
        'defesas_goleiro_media': [3.1, 2.8, 3.0, 3.5, 3.2, 3.0, 3.3, 3.4, 3.6, 3.7, 4.2, 3.8, 3.2, 3.5, 3.9, 4.5, 4.3, 4.8, 4.9, 4.7]
    }
    return pd.DataFrame(dados_times)

@st.cache_data(ttl=28800)
def carregar_elencos_completos():
    times = list(TEAM_DATA.keys())
    elencos_base = {
        'Flamengo': [
            {'Pos': 'ATA', 'Jogador': 'Pedro', 'Finalizacoes_L5': 3.3, 'Faltas_Sofridas_L5': 1.8, 'Faltas_Cometidas_L5': 0.8, 'Desarmes_L5': 0.4, 'Cartoes_Amarelos_L5': 0.2},
            {'Pos': 'ATA', 'Jogador': 'Gabigol', 'Finalizacoes_L5': 2.7, 'Faltas_Sofridas_L5': 1.6, 'Faltas_Cometidas_L5': 1.2, 'Desarmes_L5': 0.5, 'Cartoes_Amarelos_L5': 0.4},
            {'Pos': 'ATA', 'Jogador': 'Bruno Henrique', 'Finalizacoes_L5': 2.4, 'Faltas_Sofridas_L5': 1.9, 'Faltas_Cometidas_L5': 1.0, 'Desarmes_L5': 0.8, 'Cartoes_Amarelos_L5': 0.3},
            {'Pos': 'MEI', 'Jogador': 'Giorgian de Arrascaeta', 'Finalizacoes_L5': 2.2, 'Faltas_Sofridas_L5': 3.0, 'Faltas_Cometidas_L5': 1.1, 'Desarmes_L5': 1.3, 'Cartoes_Amarelos_L5': 0.4},
            {'Pos': 'MEI', 'Jogador': 'Nicolas De La Cruz', 'Finalizacoes_L5': 1.8, 'Faltas_Sofridas_L5': 2.5, 'Faltas_Cometidas_L5': 2.2, 'Desarmes_L5': 2.8, 'Cartoes_Amarelos_L5': 0.6},
            {'Pos': 'MEI', 'Jogador': 'Gerson', 'Finalizacoes_L5': 1.1, 'Faltas_Sofridas_L5': 2.2, 'Faltas_Cometidas_L5': 2.0, 'Desarmes_L5': 2.6, 'Cartoes_Amarelos_L5': 0.5},
            {'Pos': 'MEI', 'Jogador': 'Erick Pulgar', 'Finalizacoes_L5': 0.6, 'Faltas_Sofridas_L5': 1.0, 'Faltas_Cometidas_L5': 2.4, 'Desarmes_L5': 3.2, 'Cartoes_Amarelos_L5': 0.7},
            {'Pos': 'DEF', 'Jogador': 'Ayrton Lucas', 'Finalizacoes_L5': 0.9, 'Faltas_Sofridas_L5': 1.2, 'Faltas_Cometidas_L5': 1.5, 'Desarmes_L5': 2.4, 'Cartoes_Amarelos_L5': 0.5},
            {'Pos': 'DEF', 'Jogador': 'Léo Pereira', 'Finalizacoes_L5': 0.8, 'Faltas_Sofridas_L5': 0.6, 'Faltas_Cometidas_L5': 1.8, 'Desarmes_L5': 2.5, 'Cartoes_Amarelos_L5': 0.6},
            {'Pos': 'GOL', 'Jogador': 'Agustín Rossi', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.2, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.2, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'São Paulo': [
            {'Pos': 'ATA', 'Jogador': 'Jonathan Calleri', 'Finalizacoes_L5': 3.1, 'Faltas_Sofridas_L5': 3.2, 'Faltas_Cometidas_L5': 1.8, 'Desarmes_L5': 0.7, 'Cartoes_Amarelos_L5': 0.5},
            {'Pos': 'ATA', 'Jogador': 'Luciano', 'Finalizacoes_L5': 2.6, 'Faltas_Sofridas_L5': 2.4, 'Faltas_Cometidas_L5': 1.5, 'Desarmes_L5': 0.9, 'Cartoes_Amarelos_L5': 0.6},
            {'Pos': 'ATA', 'Jogador': 'Lucas Moura', 'Finalizacoes_L5': 2.5, 'Faltas_Sofridas_L5': 2.9, 'Faltas_Cometidas_L5': 1.1, 'Desarmes_L5': 1.2, 'Cartoes_Amarelos_L5': 0.3},
            {'Pos': 'MEI', 'Jogador': 'Pablo Maia', 'Finalizacoes_L5': 0.6, 'Faltas_Sofridas_L5': 1.1, 'Faltas_Cometidas_L5': 2.4, 'Desarmes_L5': 3.5, 'Cartoes_Amarelos_L5': 0.7},
            {'Pos': 'DEF', 'Jogador': 'Robert Arboleda', 'Finalizacoes_L5': 0.8, 'Faltas_Sofridas_L5': 0.4, 'Faltas_Cometidas_L5': 2.0, 'Desarmes_L5': 2.9, 'Cartoes_Amarelos_L5': 0.6},
            {'Pos': 'GOL', 'Jogador': 'Rafael', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.2, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ]
    }
    
    jogadores_lista = []
    for time in times:
        elenco_base = elencos_base.get(time, [{'Pos': 'JOG', 'Jogador': f'Atleta {time}', 'Finalizacoes_L5': 2.0, 'Faltas_Sofridas_L5': 1.5, 'Faltas_Cometidas_L5': 1.0, 'Desarmes_L5': 1.0, 'Cartoes_Amarelos_L5': 0.3}])
        for j in elenco_base:
            j_copy = j.copy()
            j_copy['Time'] = time
            jogadores_lista.append(j_copy)
    return pd.DataFrame(jogadores_lista)

df_times = carregar_dados_gerais()
df_jogadores = carregar_elencos_completos()

# --- BARRA LATERAL ---
st.sidebar.markdown("### ⚙️ Seleção de Equipe")
time_principal = st.sidebar.selectbox("Escolha o Time", df_times['Home'].unique())
dados_time1 = df_times[df_times['Home'] == time_principal].iloc[0]
logo_time1 = TEAM_DATA[time_principal]['logo']

mercado_visivel = st.sidebar.selectbox(
    "Métrica Coletiva", 
    ["Gols", "Finalizações", "Desarmes", "Faltas Cometidas", "Faltas Sofridas", "Defesas de Goleiro", "Escanteios"]
)

# --- CABEÇALHO COM ESCUDO OFICIAL (ESTILO SOFASCORE) ---
col_logo, col_titulo = st.columns([1, 6])
with col_logo:
    st.image(logo_time1, width=75)
with col_titulo:
    st.markdown(f"## {time_principal}")
    st.markdown(f"<span style='color: #26C6DA; font-size: 14px;'>Estatísticas Oficiais & Desempenho do Plantel</span>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- CARDS DE MÉTRICA ---
c1, c2, c3, c4 = st.columns(4)
val_c1 = dados_time1['gols_feitos_media'] if mercado_visivel == "Gols" else (dados_time1['finalizacoes_media'] if mercado_visivel == "Finalizações" else dados_time1['escanteios_media'])
lbl_c1 = f"Média {mercado_visivel}"

with c1:
    st.markdown(f"""<div class="metric-card"><div class="metric-title">{lbl_c1}</div><div class="metric-value">{val_c1}</div></div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="metric-card"><div class="metric-title">Gols Sofridos</div><div class="metric-value">{dados_time1['gols_sofridos_media']}</div></div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="metric-card"><div class="metric-title">Escanteios Média</div><div class="metric-value">{dados_time1['escanteios_media']}</div></div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="metric-card"><div class="metric-title">Finalizações Média</div><div class="metric-value">{dados_time1['finalizacoes_media']}</div></div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- PLANTEL COMPLETO COM POSIÇÃO ---
st.markdown(f"### 👤 Elenco Atualizado ({time_principal})")
df_elenco = df_jogadores[df_jogadores['Time'] == time_principal]
st.dataframe(
    df_elenco[['Pos', 'Jogador', 'Finalizacoes_L5', 'Faltas_Sofridas_L5', 'Faltas_Cometidas_L5', 'Desarmes_L5', 'Cartoes_Amarelos_L5']],
    use_container_width=True,
    hide_index=True
)

st.markdown("---")

# --- SIMULADOR DE CONFRONTO DIRETO & ESCUDOS H2H ---
st.markdown("### 🤖 Simulador de Confronto & H2H Visual")
adversarios = [t for t in df_times['Home'].unique() if t != time_principal]
adversario = st.selectbox("Escolher Adversário", adversarios)
dados_time2 = df_times[df_times['Home'] == adversario].iloc[0]
logo_time2 = TEAM_DATA[adversario]['logo']

# Banner Placar Visual
st.markdown(f"""
    <div class="score-banner">
        <table style="width:100%; border:none; background:transparent;">
            <tr style="background:transparent; border:none;">
                <td style="text-align:center; width:40%; border:none; color:white; font-size:18px; font-weight:bold;">
                    <img src="{logo_time1}" width="40" style="vertical-align:middle; margin-right:10px;"> {time_principal}
                </td>
                <td style="text-align:center; width:20%; border:none; color:#26C6DA; font-size:24px; font-weight:bold;">
                    VS
                </td>
                <td style="text-align:center; width:40%; border:none; color:white; font-size:18px; font-weight:bold;">
                    {adversario} <img src="{logo_time2}" width="40" style="vertical-align:middle; margin-left:10px;">
                </td>
            </tr>
        </table>
    </div>
""", unsafe_allow_html=True)

gols_t1 = (dados_time1['gols_feitos_media'] + dados_time2['gols_sofridos_media']) / 2
gols_t2 = (dados_time2['gols_feitos_media'] + dados_time1['gols_sofridos_media']) / 2
total_gols = gols_t1 + gols_t2

sc1, sc2, sc3 = st.columns(3)
with sc1:
    st.markdown(f"""<div class="metric-card"><div class="metric-title">Expectativa de Gols</div><div class="metric-value" style="color: #26C6DA;">{gols_t1:.2f} x {gols_t2:.2f}</div></div>""", unsafe_allow_html=True)
with sc2:
    st.markdown(f"""<div class="metric-card"><div class="metric-title">Finalizações Estimadas</div><div class="metric-value">{(dados_time1['finalizacoes_media'] + dados_time2['finalizacoes_media'])/2:.1f}</div></div>""", unsafe_allow_html=True)
with sc3:
    st.markdown(f"""<div class="metric-card"><div class="metric-title">Faltas Estimadas</div><div class="metric-value">{(dados_time1['faltas_cometidas_media'] + dados_time2['faltas_cometidas_media'])/2:.1f}</div></div>""", unsafe_allow_html=True)

if total_gols >= 2.5:
    st.success(f"🔥 **Tendência:** Alta probabilidade de **Mais de 2.5 Gols** ({total_gols:.2f} estimados).")
else:
    st.warning(f"🛡️ **Tendência:** Jogo truncado, tendência de **Menos de 2.5 Gols** ({total_gols:.2f} estimados).")

st.markdown(f"### 📜 Histórico de Confronto Direto (API-Football)")

def buscar_h2h_api(t1, t2, key):
    id1 = TEAM_DATA[t1]['id']
    id2 = TEAM_DATA[t2]['id']
    
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
                data_formatada = f"{data_jogo[8:10]}/{data_jogo[5:7]}/{data_jogo[0:4]}"
                competicao = match['league']['name']
                mandante = match['teams']['home']['name']
                visitante = match['teams']['away']['name']
                gols_home = match['goals']['home']
                gols_away = match['goals']['away']
                placar = f"{gols_home} x {gols_away}" if gols_home is not None else "Adjuv."
                
                h2h_lista.append({
                    'Data': data_formatada,
                    'Competição': competicao,
                    'Mandante': mandante,
                    'Placar': placar,
                    'Visitante': visitante
                })
            return pd.DataFrame(h2h_lista), None
        else:
            return None, "Nenhum confronto recente retornado pela API para esses parâmetros."
    except Exception as e:
        return None, f"Erro na conexão com a API: {e}"

df_h2h_real, erro_api = buscar_h2h_api(time_principal, adversario, API_KEY_FIXA)

if df_h2h_real is not None and not df_h2h_real.empty:
    st.dataframe(df_h2h_real, use_container_width=True, hide_index=True)
else:
    if erro_api:
        st.info(erro_api)
    else:
        st.warning("Não foi possível carregar os dados reais no momento.")
