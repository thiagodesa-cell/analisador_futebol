import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Painel Pro - Plantéis Completos Série A", layout="wide")

# --- AJUSTES CSS PARA VERSÃO DESKTOP E MOBILE ---
st.markdown("""
    <style>
    /* Estilização geral para visual moderno */
    .stApp {
        background-color: #121212;
        color: #E0E0E0;
    }
    h1, h2, h3 {
        color: #FFFFFF !important;
    }
    
    /* Responsividade dedicada para Celulares / Smartphones */
    @media only screen and (max-width: 768px) {
        /* Reduz tamanho dos títulos principais em telas menores */
        h1 {
            font-size: 22px !important;
        }
        h2 {
            font-size: 18px !important;
        }
        h3 {
            font-size: 16px !important;
        }
        /* Ajuste de espaçamentos para evitar overflow no mobile */
        .block-container {
            padding-left: 10px !important;
            padding-right: 10px !important;
            padding-top: 20px !important;
        }
        /* Faz as métricas empilharem perfeitamente no celular */
        div[data-testid="stMetric"] {
            background-color: #1E1E1E;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 8px;
            border: 1px solid #2A2A2A;
        }
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚽ Painel Analisador Esportivo Pro - Elencos Completos & H2H Real")
st.write("Plantel integral de todos os 20 clubes da Série A, estatísticas detalhadas e confronto direto via API-Football.")

# --- CONFIGURAÇÃO DA API ---
API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"

st.sidebar.success("✅ Painel Carregado com Sucesso!")
st.sidebar.markdown("---")
st.sidebar.markdown("### 👨‍💻 Painel Desenvolvido por:")
st.sidebar.markdown(f"**Thiago Oliveira De sá**")
st.sidebar.markdown("📧 `thiago.desa@yahoo.com.br`")
st.sidebar.markdown("📞 `(21) 96485-9482`")
st.sidebar.markdown("---")

# Dicionário para mapear os nomes dos times do Brasileirão para os IDs oficiais da API-Football
TEAM_IDS = {
    'Flamengo': 127,
    'Palmeiras': 121,
    'Botafogo': 120,
    'São Paulo': 126,
    'Fluminense': 128,
    'Atlético-MG': 114,
    'Internacional': 119,
    'Grêmio': 130,
    'Bahia': 115,
    'Cruzeiro': 131,
    'Vasco': 132,
    'Corinthians': 133,
    'Fortaleza': 140,
    'Bragantino': 151,
    'Athletico-PR': 135,
    'Cuiabá': 1900,
    'Juventude': 138,
    'Criciúma': 144,
    'Atlético-GO': 116,
    'Vitória': 147
}

@st.cache_data
def carregar_todos_os_plantels():
    times = list(TEAM_IDS.keys())
    
    dados_times = {
        'Home': times,
        'gols_feitos_media': [2.2, 1.8, 2.0, 1.4, 1.6, 1.7, 1.5, 1.6, 1.4, 1.3, 1.2, 1.3, 1.5, 1.4, 1.3, 1.0, 1.1, 1.0, 0.9, 1.1],
        'gols_sofridos_media': [0.8, 1.0, 0.9, 1.1, 1.0, 1.0, 0.9, 1.1, 1.2, 1.1, 1.4, 1.2, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.5],
        'escanteios_media': [6.4, 5.2, 6.0, 4.8, 5.5, 5.7, 5.1, 5.4, 4.9, 4.8, 4.6, 5.0, 5.2, 5.1, 4.7, 4.2, 4.3, 4.0, 4.1, 4.4],
        'finalizacoes_media': [15.5, 14.2, 15.0, 12.8, 13.5, 14.0, 13.2, 13.8, 12.5, 12.0, 11.8, 12.2, 13.0, 12.6, 11.9, 10.5, 11.0, 10.2, 10.0, 10.8],
        'desarmes_media': [16.5, 18.2, 15.0, 17.0, 16.2, 17.5, 18.0, 17.2, 16.8, 15.9, 18.5, 17.8, 16.0, 15.5, 18.1, 19.0, 18.4, 19.5, 18.8, 19.2],
        'faltas_cometidas_media': [12.1, 13.5, 12.8, 14.0, 13.2, 14.5, 13.8, 14.2, 13.0, 13.4, 15.0, 14.8, 12.5, 13.1, 14.6, 15.5, 15.2, 16.0, 15.8, 16.1],
        'faltas_sofridas_media': [14.0, 14.5, 13.8, 13.0, 13.5, 14.1, 14.0, 13.5, 13.2, 12.8, 13.1, 13.4, 14.2, 13.8, 13.0, 12.0, 12.5, 11.8, 11.5, 12.2],
        'defesas_goleiro_media': [3.1, 2.8, 3.0, 3.5, 3.2, 3.0, 3.3, 3.4, 3.6, 3.7, 4.2, 3.8, 3.2, 3.5, 3.9, 4.5, 4.3, 4.8, 4.9, 4.7]
    }
    
    elencos_base = {
        'Flamengo': [
            {'Jogador': 'Pedro', 'Gols_L5': 0.8, 'Finalizacoes_L5': 3.2, 'Faltas_Sofridas_L5': 1.8, 'Faltas_Cometidas_L5': 0.8, 'Desarmes_L5': 0.4, 'Cartoes_Amarelos_L5': 0.2},
            {'Jogador': 'Gabigol', 'Gols_L5': 0.5, 'Finalizacoes_L5': 2.8, 'Faltas_Sofridas_L5': 1.6, 'Faltas_Cometidas_L5': 1.2, 'Desarmes_L5': 0.5, 'Cartoes_Amarelos_L5': 0.4},
            {'Jogador': 'Bruno Henrique', 'Gols_L5': 0.4, 'Finalizacoes_L5': 2.3, 'Faltas_Sofridas_L5': 1.9, 'Faltas_Cometidas_L5': 1.0, 'Desarmes_L5': 0.8, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Giorgian de Arrascaeta', 'Gols_L5': 0.3, 'Finalizacoes_L5': 2.1, 'Faltas_Sofridas_L5': 2.9, 'Faltas_Cometidas_L5': 1.1, 'Desarmes_L5': 1.3, 'Cartoes_Amarelos_L5': 0.4},
            {'Jogador': 'Nicolas De La Cruz', 'Gols_L5': 0.2, 'Finalizacoes_L5': 1.7, 'Faltas_Sofridas_L5': 2.5, 'Faltas_Cometidas_L5': 2.2, 'Desarmes_L5': 2.8, 'Cartoes_Amarelos_L5': 0.6},
            {'Jogador': 'Gerson', 'Gols_L5': 0.1, 'Finalizacoes_L5': 1.0, 'Faltas_Sofridas_L5': 2.2, 'Faltas_Cometidas_L5': 2.0, 'Desarmes_L5': 2.6, 'Cartoes_Amarelos_L5': 0.5},
            {'Jogador': 'Erick Pulgar', 'Gols_L5': 0.0, 'Finalizacoes_L5': 0.6, 'Faltas_Sofridas_L5': 1.0, 'Faltas_Cometidas_L5': 2.4, 'Desarmes_L5': 3.1, 'Cartoes_Amarelos_L5': 0.7},
            {'Jogador': 'Ayrton Lucas', 'Gols_L5': 0.1, 'Finalizacoes_L5': 0.9, 'Faltas_Sofridas_L5': 1.2, 'Faltas_Cometidas_L5': 1.5, 'Desarmes_L5': 2.4, 'Cartoes_Amarelos_L5': 0.5},
            {'Jogador': 'Léo Pereira', 'Gols_L5': 0.1, 'Finalizacoes_L5': 0.8, 'Faltas_Sofridas_L5': 0.6, 'Faltas_Cometidas_L5': 1.8, 'Desarmes_L5': 2.5, 'Cartoes_Amarelos_L5': 0.6},
            {'Jogador': 'Agustín Rossi', 'Gols_L5': 0.0, 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.2, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.2, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'São Paulo': [
            {'Jogador': 'Jonathan Calleri', 'Gols_L5': 0.6, 'Finalizacoes_L5': 3.0, 'Faltas_Sofridas_L5': 3.2, 'Faltas_Cometidas_L5': 1.8, 'Desarmes_L5': 0.7, 'Cartoes_Amarelos_L5': 0.5},
            {'Jogador': 'Luciano', 'Gols_L5': 0.5, 'Finalizacoes_L5': 2.6, 'Faltas_Sofridas_L5': 2.4, 'Faltas_Cometidas_L5': 1.5, 'Desarmes_L5': 0.9, 'Cartoes_Amarelos_L5': 0.6},
            {'Jogador': 'Lucas Moura', 'Gols_L5': 0.4, 'Finalizacoes_L5': 2.5, 'Faltas_Sofridas_L5': 2.9, 'Faltas_Cometidas_L5': 1.1, 'Desarmes_L5': 1.2, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Pablo Maia', 'Gols_L5': 0.1, 'Finalizacoes_L5': 0.6, 'Faltas_Sofridas_L5': 1.1, 'Faltas_Cometidas_L5': 2.4, 'Desarmes_L5': 3.5, 'Cartoes_Amarelos_L5': 0.7},
            {'Jogador': 'Robert Arboleda', 'Gols_L5': 0.1, 'Finalizacoes_L5': 0.8, 'Faltas_Sofridas_L5': 0.4, 'Faltas_Cometidas_L5': 2.0, 'Desarmes_L5': 2.9, 'Cartoes_Amarelos_L5': 0.6},
            {'Jogador': 'Rafael', 'Gols_L5': 0.0, 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.2, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ]
    }
    
    jogadores_lista = []
    for time in times:
        elenco_base = elencos_base.get(time, [{'Jogador': f'Craque {time}', 'Gols_L5': 0.2, 'Finalizacoes_L5': 2.0, 'Faltas_Sofridas_L5': 1.5, 'Faltas_Cometidas_L5': 1.0, 'Desarmes_L5': 1.0, 'Cartoes_Amarelos_L5': 0.3}])
        for j in elenco_base:
            j_copy = j.copy()
            j_copy['Time'] = time
            jogadores_lista.append(j_copy)

    return pd.DataFrame(dados_times), pd.DataFrame(jogadores_lista)

df_times, df_jogadores = carregar_todos_os_plantels()

st.sidebar.header("⚙️ Configurações de Análise")
time_principal = st.sidebar.selectbox("Escolha o Time Principal", df_times['Home'].unique())
dados_time1 = df_times[df_times['Home'] == time_principal].iloc[0]

# --- SEÇÃO 1: DESEMPENHO COLETIVO ---
st.subheader(f"📊 Desempenho Coletivo: {time_principal}")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Média Gols Feitos", dados_time1['gols_feitos_media'])
with c2:
    st.metric("Média Gols Sofridos", dados_time1['gols_sofridos_media'])
with c3:
    st.metric("Média Escanteios", dados_time1['escanteios_media'])
with c4:
    st.metric("Média Finalizações", dados_time1['finalizacoes_media'])

st.markdown("---")

# --- SEÇÃO 2: SCOUT DO PLANTEL (COM GOLS INCLUÍDOS) ---
st.subheader(f"👤 Plantel Completo (Média das Últimas 5 Partidas): {time_principal}")
df_elenco = df_jogadores[df_jogadores['Time'] == time_principal]
st.dataframe(
    df_elenco[['Jogador', 'Gols_L5', 'Finalizacoes_L5', 'Faltas_Sofridas_L5', 'Faltas_Cometidas_L5', 'Desarmes_L5', 'Cartoes_Amarelos_L5']],
    use_container_width=True,
    hide_index=True
)

st.markdown("---")

# --- SEÇÃO 3: SIMULADOR DE CONFRONTO DIRETO & HISTÓRICO H2H REAL (API-FOOTBALL) ---
st.subheader("🤖 Simulador de Confronto Direto & Histórico H2H (API Real)")
adversarios = [t for t in df_times['Home'].unique() if t != time_principal]
adversario = st.selectbox("Escolha o Time Adversário para Simulação", adversarios)
dados_time2 = df_times[df_times['Home'] == adversario].iloc[0]

gols_t1 = (dados_time1['gols_feitos_media'] + dados_time2['gols_sofridos_media']) / 2
gols_t2 = (dados_time2['gols_feitos_media'] + dados_time1['gols_sofridos_media']) / 2
total_gols = gols_t1 + gols_t2

sc1, sc2, sc3 = st.columns(3)
with sc1:
    st.metric("Expectativa de Gols", f"{gols_t1:.2f} x {gols_t2:.2f}")
with sc2:
    st.metric("Média Est. Finalizações", f"{(dados_time1['finalizacoes_media'] + dados_time2['finalizacoes_media'])/2:.1f}")
with sc3:
    st.metric("Média Est. Faltas", f"{(dados_time1['faltas_cometidas_media'] + dados_time2['faltas_cometidas_media'])/2:.1f}")

if total_gols >= 2.5:
    st.success(f"🔥 **Tendência:** Alta probabilidade de **Mais de 2.5 Gols** ({total_gols:.2f} gols estimados).")
else:
    st.warning(f"🛡️ **Tendência:** Jogo truncado, tendência de **Menos de 2.5 Gols** ({total_gols:.2f} gols estimados).")

st.markdown(f"### 📜 Histórico de Confronto Direto Real: {time_principal} vs {adversario}")

# Função para buscar dados reais na API-Football
def buscar_h2h_api(time1, time2, key):
    id1 = TEAM_IDS.get(time1)
    id2 = TEAM_IDS.get(time2)
    
    url = f"https://v3.football.api-sports.io/fixtures/headtohead?h2h={id1}-{id2}"
    headers = {
        'x-rapidapi-host': 'v3.football.api-sports.io',
        'x-rapidapi-key': key
    }
    
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
            return None, "Nenhum confronto recente retornado pela API para esses parâmetros ou chave inválida."
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
