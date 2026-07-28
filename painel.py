import requests
from datetime import datetime, timedelta

# --- SUAS CHAVES JÁ CONFIGURADAS ---
API_KEY = "E89cc081ecbaaf1a7074e878c1cae0ff"
TELEGRAM_TOKEN = "8281259090:AAEggXJKpCMxRbhhrcCZymcmNUKWNoOPFfY"
TELEGRAM_CHAT_ID = "-1004464226419"  # 👈 APAGUE ESSE TEXTO E COLOQUE SEU NÚMERO AQUI (EX: 123456789)

# --- CONFIGURAÇÕES DO TIME ---
TEAM_ID = 127  # ID Oficial do Flamengo na API-Football
LEAGUE_ID = 71  # Brasileirão Série A

def enviar_mensagem_telegram(texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
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
