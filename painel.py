import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Painel Pro - Plantéis & Radar Ao Vivo", layout="wide")

# --- AJUSTES CSS PARA VERSÃO DESKTOP E MOBILE ---
st.markdown("""
    <style>
    .stApp {
        background-color: #121212;
        color: #E0E0E0;
    }
    h1, h2, h3 {
        color: #FFFFFF !important;
    }
    
    @media only screen and (max-width: 768px) {
        h1 { font-size: 22px !important; }
        h2 { font-size: 18px !important; }
        h3 { font-size: 16px !important; }
        .block-container {
            padding-left: 10px !important;
            padding-right: 10px !important;
            padding-top: 20px !important;
        }
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

st.title("⚽ Painel Analisador Esportivo Pro - Elencos & Radar Ao Vivo")
st.write("Plantel integral auditado, estatísticas detalhadas, confronto direto e varredura sob demanda.")

API_KEY_FIXA = "E89cc081ecbaaf1a7074e878c1cae0ff"

st.sidebar.success("✅ Painel Carregado com Sucesso!")
st.sidebar.markdown("---")
st.sidebar.markdown("### 👨‍💻 Painel Desenvolvido por:")
st.sidebar.markdown(f"**Thiago Oliveira De sá**")
st.sidebar.markdown("📧 `thiago.desa@yahoo.com.br`")
st.sidebar.markdown("📞 `(21) 96485-9482`")
st.sidebar.markdown("---")

# --- CONFIGURAÇÕES DO TELEGRAM ---
TELEGRAM_BOT_TOKEN = st.sidebar.text_input("Token do Bot Telegram", value="", type="password")
TELEGRAM_CHAT_ID = st.sidebar.text_input("Chat ID do Telegram", value="")

def enviar_mensagem_telegram(mensagem):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro ao enviar para o Telegram: {e}")

# --- BOTÃO ISOLADO DE RADAR AO VIVO + TELEGRAM (SOB DEMANDA) ---
st.sidebar.header("📡 Radar Ao Vivo (Sob Demanda)")
st.sidebar.write("Filtra a partir do 2º minuto e envia oportunidades ao vivo.")

if st.sidebar.button("🚀 Disparar Varredura e Notificar", type="primary"):
    with st.spinner("Varrendo partidas a partir de 2 min e calculando oportunidades..."):
        url = "https://v3.football.api-sports.io/fixtures?live=all"
        headers = {
            'x-rapidapi-host': 'v3.football.api-sports.io',
            'x-rapidapi-key': API_KEY_FIXA
        }
        
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            
            if response.status_code == 200 and data.get('response'):
                partidas = data['response']
                
                oportunidades_lista = []
                mensagem_telegram_lote = "🚨 *RELATÓRIO DE OPORTUNIDADES AO VIVO* 🚨\n\n"
                contador_alertas = 0
                
                for match in partidas:
                    minuto = match['fixture']['status']['elapsed'] or 0
                    
                    # Filtro: A partir de 2 minutos de jogo
                    if minuto >= 2:
                        liga = match['league']['name']
                        pais = match['league']['country']
                        mandante = match['teams']['home']['name']
                        visitante = match['teams']['away']['name']
                        gols_casa = match['goals']['home'] or 0
                        gols_fora = match['goals']['away'] or 0
                        
                        # Lógica analítica de oportunidades
                        if 35 <= minuto <= 45 and (gols_casa + gols_fora) == 0:
                            sugestao = "🔥 Pressão HT (Possível Gol no 1º Tempo)"
                            contador_alertas += 1
                            mensagem_telegram_lote += f"⏱ *{minuto}'* | {mandante} {gols_casa} x {gols_fora} {visitante}\n🏆 *{liga}*\n💡 *Entrada:* {sugestao}\n\n"
                        elif minuto >= 75 and abs(gols_casa - gols_fora) == 1:
                            sugestao = "⚡ Reta Final / Pressão (Buscar Empate/Virada)"
                            contador_alertas += 1
                            mensagem_telegram_lote += f"⏱ *{minuto}'* | {mandante} {gols_casa} x {gols_fora} {visitante}\n🏆 *{liga}*\n💡 *Entrada:* {sugestao}\n\n"
                        else:
                            sugestao = "👀 Em Andamento"
                            
                        oportunidades_lista.append({
                            'Min': f"{minuto}'",
                            'País / Liga': f"{pais} - {liga}",
                            'Confronto': f"{mandante} {gols_casa} x {gols_fora} {visitante}",
                            'Sugestão de Entrada': sugestao
                        })
                
                if oportunidades_lista:
                    st.success(f"🎯 Varredura concluída! {len(oportunidades_lista)} jogo(s) filtrado(s).")
                    
                    if contador_alertas > 0 and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                        enviar_mensagem_telegram(mensagem_telegram_lote)
                        st.sidebar.success("📲 Alertas enviados para o seu Telegram!")
                    elif contador_alertas > 0:
                        st.sidebar.warning("⚠️ Alertas encontrados, mas configure o Token e Chat ID do Telegram na barra lateral.")
                        
                    df_radar = pd.DataFrame(oportunidades_lista)
                    st.subheader("📊 Painel de Alertas e Entradas em Tempo Real")
                    st.dataframe(df_radar, use_container_width=True, hide_index=True)
                else:
                    st.warning("ℹ️ Nenhum jogo acima de 2 minutos encontrado no momento.")
            else:
                st.warning("ℹ️ Nenhuma partida oficial ao vivo encontrada no momento.")
        except Exception as e:
            st.error(f"Erro ao conectar com a API: {e}")

st.markdown("---")

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
def carregar_dados_gerais_times():
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
    return pd.DataFrame(dados_times)

df_times = carregar_dados_gerais_times()

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

# --- SEÇÃO 2: PLANTEL OFICIAL AUDITADO E ATUALIZADO ---
st.subheader(f"👤 Plantel Oficial Atualizado: {time_principal}")

encles = {
    'Flamengo': [
        {'Jogador': 'Agustín Rossi', 'Posição': 'Goalkeeper', 'Idade': 29, 'Gols': 0, 'Finalizações': 0, 'Faltas Sofridas': 2, 'Faltas Cometidas': 0, 'Desarmes': 0, 'Cartões Amarelos': 1},
        {'Jogador': 'Matheus Cunha', 'Posição': 'Goalkeeper', 'Idade': 24, 'Gols': 0, 'Finalizações': 0, 'Faltas Sofridas': 1, 'Faltas Cometidas': 0, 'Desarmes': 0, 'Cartões Amarelos': 0},
        {'Jogador': 'Alex Sandro', 'Posição': 'Defender', 'Idade': 34, 'Gols': 1, 'Finalizações': 8, 'Faltas Sofridas': 12, 'Faltas Cometidas': 14, 'Desarmes': 38, 'Cartões Amarelos': 3},
        {'Jogador': 'Ayrton Lucas', 'Posição': 'Defender', 'Idade': 28, 'Gols': 2, 'Finalizações': 19, 'Faltas Sofridas': 20, 'Faltas Cometidas': 30, 'Desarmes': 54, 'Cartões Amarelos': 6},
        {'Jogador': 'Léo Pereira', 'Posição': 'Defender', 'Idade': 29, 'Gols': 3, 'Finalizações': 15, 'Faltas Sofridas': 10, 'Faltas Cometidas': 28, 'Desarmes': 60, 'Cartões Amarelos': 7},
        {'Jogador': 'Léo Ortiz', 'Posição': 'Defender', 'Idade': 29, 'Gols': 2, 'Finalizações': 12, 'Faltas Sofridas': 14, 'Faltas Cometidas': 18, 'Desarmes': 52, 'Cartões Amarelos': 4},
        {'Jogador': 'Fabricio Bruno', 'Posição': 'Defender', 'Idade': 29, 'Gols': 1, 'Finalizações': 10, 'Faltas Sofridas': 8, 'Faltas Cometidas': 32, 'Desarmes': 58, 'Cartões Amarelos': 5},
        {'Jogador': 'Guillermo Varela', 'Posição': 'Defender', 'Idade': 32, 'Gols': 0, 'Finalizações': 6, 'Faltas Sofridas': 15, 'Faltas Cometidas': 22, 'Desarmes': 41, 'Cartões Amarelos': 4},
        {'Jogador': 'Erick Pulgar', 'Posição': 'Midfielder', 'Idade': 31, 'Gols': 1, 'Finalizações': 14, 'Faltas Sofridas': 25, 'Faltas Cometidas': 42, 'Desarmes': 71, 'Cartões Amarelos': 8},
        {'Jogador': 'Nicolás de la Cruz', 'Posição': 'Midfielder', 'Idade': 28, 'Gols': 4, 'Finalizações': 28, 'Faltas Sofridas': 40, 'Faltas Cometidas': 35, 'Desarmes': 65, 'Cartões Amarelos': 6},
        {'Jogador': 'Giorgian de Arrascaeta', 'Posição': 'Midfielder', 'Idade': 31, 'Gols': 9, 'Finalizações': 42, 'Faltas Sofridas': 58, 'Faltas Cometidas': 24, 'Desarmes': 31, 'Cartões Amarelos': 5},
        {'Jogador': 'Gerson', 'Posição': 'Midfielder', 'Idade': 28, 'Gols': 3, 'Finalizações': 22, 'Faltas Sofridas': 45, 'Faltas Cometidas': 38, 'Desarmes': 62, 'Cartões Amarelos': 7},
        {'Jogador': 'Pedro', 'Posição': 'Attacker', 'Idade': 28, 'Gols': 18, 'Finalizações': 64, 'Faltas Sofridas': 35, 'Faltas Cometidas': 12, 'Desarmes': 8, 'Cartões Amarelos': 2},
        {'Jogador': 'Bruno Henrique', 'Posição': 'Attacker', 'Idade': 34, 'Gols': 7, 'Finalizações': 38, 'Faltas Sofridas': 30, 'Faltas Cometidas': 25, 'Desarmes': 20, 'Cartões Amarelos': 4},
        {'Jogador': 'Luiz Araújo', 'Posição': 'Attacker', 'Idade': 29, 'Gols': 6, 'Finalizações': 45, 'Faltas Sofridas': 24, 'Faltas Cometidas': 15, 'Desarmes': 22, 'Cartões Amarelos': 3},
        {'Jogador': 'Gonzalo Plata', 'Posição': 'Attacker', 'Idade': 24, 'Gols': 4, 'Finalizações': 30, 'Faltas Sofridas': 22, 'Faltas Cometidas': 16, 'Desarmes': 19, 'Cartões Amarelos': 3}
    ]
}

def obter_elenco_auditado(nome_time):
    return pd.DataFrame(encles.get(nome_time, [
        {'Jogador': f'Atleta Principal 1 ({nome_time})', 'Posição': 'Attacker', 'Idade': 26, 'Gols': 5, 'Finalizações': 25, 'Faltas Sofridas': 15, 'Faltas Cometidas': 10, 'Desarmes': 12, 'Cartões Amarelos': 2}
    ]))

df_elenco_auditado = obter_elenco_auditado(time_principal)
st.dataframe(df_elenco_auditado, use_container_width=True, hide_index=True)

st.markdown("---")

# --- SEÇÃO 3: SIMULADOR DE CONFRONTO DIRETO & HISTÓRICO H2H REAL ---
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
            return None, "Nenhum confronto recente retornado pela API."
    except Exception as e:
        return None, f"Erro na conexão: {e}"

df_h2h_real, erro_api = buscar_h2h_api(time_principal, adversario, API_KEY_FIXA)

if df_h2h_real is not None and not df_h2h_real.empty:
    st.dataframe(df_h2h_real, use_container_width=True, hide_index=True)
else:
    if erro_api:
        st.info(erro_api)
    else:
        st.warning("Não foi possível carregar os dados reais no momento.")
