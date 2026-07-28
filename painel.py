import requests
from datetime import datetime, timedelta

# --- SUAS CHAVES JÁ CONFIGURADAS ---
API_KEY = "E89cc081eimport streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

# Configuração da página do Streamlit
st.set_page_config(page_title="Painel Pro - Scout & Insights", layout="wide", initial_sidebar_state="expanded")

# --- ESTILIZAÇÃO PREMIUM (CSS) ---
st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border: 1px solid #374151; }
    div.stButton > button:first-child { background-color: #ef4444; color: white; border-radius: 8px; width: 100%; height: 45px; font-weight: bold; }
    div.stButton > button:first-child:hover { background-color: #dc2626; border-color: #dc2626; }
    .stDataFrame { border: 1px solid #374151; border-radius: 8px; }
</style>
""", unsafe_select=True)

# Chave fixa da API
API_KEY = "E89cc081ecbaaf1a7074e878c1cae0ff"

# --- BLOQUEIO INTELIGENTE DE HORÁRIO ---
def verificar_bloqueio_horario():
    agora_br = datetime.utcnow() - timedelta(hours=3)
    limite_hoje = agora_br.replace(hour=8, minute=0, second=0, microsecond=0)
    
    if agora_br >= limite_hoje:
        st.error("⚠️ O limite de requisições automáticas diárias expirou (Bloqueio pós 08:00h da manhã ativo). As consultas estão suspensas para preservar seus créditos da API.")
        st.stop()

# --- FUNÇÕES DE BUSCA DA API ---
def buscar_dados_api(endpoint, params={}):
    headers = {
        'x-rapidapi-host': 'v3.football.api-sports.io',
        'x-rapidapi-key': API_KEY
    }
    url = f"https://v3.football.api-sports.io/{endpoint}"
    try:
        response = requests.get(url, headers=headers, params=params)
        return response.json()
    except Exception as e:
        st.error(f"Erro na conexão com a API: {e}")
        return None

# --- ESTRUTURA DO PAINEL ---
st.title("📊 Painel de Análise Esportiva Pro")
st.markdown("Selecione os parâmetros na barra lateral para analisar scouts e projetar mercados.")

# Barra lateral para entrada de dados
st.sidebar.header("🔍 Filtros de Análise")
time_id = st.sidebar.text_input("ID do Time (Ex: 127 para Flamengo)", value="127")
campeonato_id = st.sidebar.text_input("ID do Campeonato (Ex: 71 para Brasileirão)", value="71")
buscar = st.sidebar.button("📊 Analisar Últimas 5 Partidas")

if buscar:
    # Ativa a verificação de horário assim que o botão é clicado
    verificar_bloqueio_horario()
    
    with st.spinner("Buscando dados das últimas partidas e gerando scouts..."):
        ano_atual = (datetime.utcnow() - timedelta(hours=3)).year
        
        # 1. Busca os últimos jogos do time
        dados_jogos = buscar_dados_api("fixtures", {"team": time_id, "league": campeonato_id, "last": "5"})
        
        if not dados_jogos or dados_jogos.get('results', 0) == 0:
            st.warning("Nenhum dado encontrado para os IDs informados. Verifique se os IDs estão corretos.")
        else:
            lista_jogos = dados_jogos['response']
            
            # Métricas Gerais das últimas 5 partidas
            gols_marcados = 0
            gols_sofridos = 0
            total_chutes = 0
            total_desarmes = 0
            
            dados_tabela_jogos = []
            
            # Loop para somar estatísticas das últimas partidas
            for partida in lista_jogos:
                f_id = partida['fixture']['id']
                casa = partida['teams']['home']['name']
                fora = partida['teams']['away']['name']
                placar_casa = partida['goals']['home']
                placar_fora = partida['goals']['away']
                
                dados_tabela_jogos.append({
                    "Partida": f"{casa} {placar_casa} x {placar_fora} {fora}",
                    "Status": partida['fixture']['status']['short']
                })
                
                # Contagem de gols baseada na posição do time analisado
                if str(partida['teams']['home']['id']) == str(time_id):
                    gols_marcados += placar_casa if placar_casa else 0
                    gols_sofridos += placar_fora if placar_fora else 0
                else:
                    gols_marcados += placar_fora if placar_fora else 0
                    gols_sofridos += placar_casa if placar_casa else 0
                    
                # Busca estatísticas detalhadas do scout do jogo
                dados_detalhes = buscar_dados_api("fixtures/statistics", {"fixture": f_id, "team": time_id})
                if dados_detalhes and dados_detalhes.get('response'):
                    stats = dados_detalhes['response'][0]['statistics']
                    for s in stats:
                        if s['type'] == 'Total Shots' and s['value']:
                            total_chutes += int(s['value'])
                        if s['type'] == 'Tackles' and s['value']:
                            total_desarmes += int(s['value'])

            # --- EXIBIÇÃO NO PAINEL ---
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Gols Feitos (Últimos 5 j)", gols_marcados)
            col2.metric("Gols Sofridos (Últimos 5 j)", gols_sofridos)
            col3.metric("Média de Chutes", f"{total_chutes/5:.1f}")
            col4.metric("Média de Desarmes", f"{total_desarmes/5:.1f}")
            
            st.subheader("📋 Últimos 5 Confrontos Analisados")
            st.table(pd.DataFrame(dados_tabela_jogos))
            
            # Projeções para o mercado baseadas nas médias
            st.subheader("🤖 Projeções e Tendências Pro")
            if (gols_marcados + gols_sofridos) / 5 >= 2.5:
                st.info("🔥 **Tendência de Gols:** Este time costuma se envolver em jogos movimentados. Boa tendência para o mercado de **Over 2.5 Gols**.")
            else:
                st.info("🛡️ **Tendência de Gols:** Jogos recentes com poucos gols. Boa tendência para o mercado de **Under 2.5 Gols**.")
                
            if total_chutes / 5 >= 12:
                st.success("🎯 **Scout de Chutes:** O time mantém uma linha ofensiva alta com grande volume de finalizações. Fique atento a linhas de chutes ao gol de jogadores.")
        "text": texto,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")

def extrair_medias_gols(stats_data):
    if stats_data.get('results', 0) > 0:
        stats = stats_data['response']
        gf = stats.get('goals', {}).get('for', {}).get('average', {}).get('total', '0')
        gs = stats.get('goals', {}).get('against', {}).get('average', {}).get('total', '0')
        return float(gf) if gf else 0.0, float(gs) if gs else 0.0
    return 0.0, 0.0

def rodar_analise():
    headers = {
        'x-rapidapi-host': 'v3.football.api-sports.io',
        'x-rapidapi-key': API_KEY
    }
    
    # Ajusta para o fuso horário de Brasília (GitHub roda em UTC)
    agora_br = datetime.utcnow() - timedelta(hours=3)
    data_hoje = agora_br.strftime('%Y-%m-%d')
    ano_atual = agora_br.year
    
    print(f"Checando jogos para a data: {data_hoje} (Ano: {ano_atual})")
    
    # 1. Verifica se o Flamengo joga hoje
    url_fixture = f"https://v3.football.api-sports.io/fixtures?team={TEAM_ID}&date={data_hoje}"
    res_fix = requests.get(url_fixture, headers=headers).json()
    
    if res_fix.get('results', 0) == 0:
        print("Hoje não tem jogo do Mengão! Encerrando para poupar créditos.")
        return
    
    # Jogo encontrado! Coleta dados da partida
    partida = res_fix['response'][0]
    venue = partida['fixture']['venue']['name'] or "Não informado"
    
    # Formata a hora do jogo (API entrega em UTC, convertemos para Brasília)
    data_utc = datetime.strptime(partida['fixture']['date'], "%Y-%m-%dT%H:%M:%S%z")
    data_br = data_utc - timedelta(hours=3)
    horario_jogo = data_br.strftime("%H:%M")
    
    # Identifica o adversário
    home_id = partida['teams']['home']['id']
    home_name = partida['teams']['home']['name']
    away_name = partida['teams']['away']['name']
    
    if home_id == TEAM_ID:
        opponent_id = partida['teams']['away']['id']
        opponent_name = away_name
        mando = "Mandante 🏠"
    else:
        opponent_id = partida['teams']['home']['id']
        opponent_name = home_name
        mando = "Visitante 🚌"
        
    print(f"Jogo confirmado hoje: Flamengo x {opponent_name}")
    
    # 2. Busca histórico de Confronto Direto (H2H) - Últimos 5 jogos
    url_h2h = f"https://v3.football.api-sports.io/fixtures/headtohead?h2h={TEAM_ID}-{opponent_id}"
    res_h2h = requests.get(url_h2h, headers=headers).json()
    
    vitorias, empates, derrotas = 0, 0, 0
    if res_h2h.get('results', 0) > 0:
        for jogo in res_h2h['response'][:5]:
            h_winner = jogo['teams']['home']['winner']
            a_winner = jogo['teams']['away']['winner']
            h_id = jogo['teams']['home']['id']
            
            if h_winner is None and a_winner is None:
                empates += 1
            elif (h_id == TEAM_ID and h_winner is True) or (h_id != TEAM_ID and a_winner is True):
                vitorias += 1
            else:
                derrotas += 1
                
    # 3. Busca Estatísticas Coletivas da Temporada para ambos os times
    url_stats_fla = f"https://v3.football.api-sports.io/teams/statistics?league={LEAGUE_ID}&season={ano_atual}&team={TEAM_ID}"
    url_stats_opp = f"https://v3.football.api-sports.io/teams/statistics?league={LEAGUE_ID}&season={ano_atual}&team={opponent_id}"
    
    res_st_fla = requests.get(url_stats_fla, headers=headers).json()
    res_st_opp = requests.get(url_stats_opp, headers=headers).json()
    
    gf_fla, gs_fla = extrair_medias_gols(res_st_fla)
    gf_opp, gs_opp = extrair_medias_gols(res_st_opp)
    
    # 4. Cálculos e Projeções de Tendências
    exp_fla = (gf_fla + gs_opp) / 2
    exp_opp = (gf_opp + gs_fla) / 2
    total_gols_esperados = exp_fla + exp_opp
    
    tendencia_gols = "Mais de 2.5 Gols 🔥" if total_gols_esperados >= 2.5 else "Menos de 2.5 Gols 🛡️"
    ambas_marcam = "Sim ⚽" if (exp_fla > 0.8 and exp_opp > 0.8) else "Não 🚫"
    
    # 5. Monta a mensagem final estilizada em HTML
    mensagem = f"""🚨 <b>RAIO-X PRÉ-LIVE MENGÃO</b> 🚨

⚽ <b>{home_name} x {away_name}</b>
🏆 Campeonato: Brasileirão Série A
⏰ Horário: {horario_jogo}h (Horário de Brasília)
🏟️ Estádio: {venue}
Flamengo joga como: <b>{mando}</b>

📜 <b>HISTÓRICO H2H (Últimos 5 Confrontos):</b>
🟢 Vitórias do Flamengo: {vitorias}
🟡 Empates: {empates}
🔴 Derrotas para o rival: {derrotas}

📊 <b>MÉDIAS NA TEMPORADA:</b>
• Gols Feitos (Fla): {gf_fla:.2f}/j
• Gols Sofridos (Fla): {gs_fla:.2f}/j
• Gols Feitos ({opponent_name}): {gf_opp:.2f}/j
• Gols Sofridos ({opponent_name}): {gs_opp:.2f}/j

🤖 <b>PROJEÇÃO E TENDÊNCIAS:</b>
• Expec. Gols Flamengo: {exp_fla:.2f}
• Expec. Gols {opponent_name}: {exp_opp:.2f}
• Total Estimado: {total_gols_esperados:.2f}
• Tendência de Gols: <b>{tendencia_gols}</b>
• Ambas Marcam: <b>{ambas_marcam}</b>

🎯 <i>Dica: Abra o seu Painel Pro no Streamlit para analisar o scout detalhado de chutes e desarmes dos jogadores para este jogo!</i>"""

    # Envia o alerta
    enviar_mensagem_telegram(mensagem)
    print("Alerta enviado com sucesso para o Telegram!")

if __name__ == "__main__":
    rodar_analise()
