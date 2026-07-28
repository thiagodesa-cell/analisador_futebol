import streamlit as st
import pandas as pd
import requests

# --- CONFIGURAÇÕES DO TELEGRAM ---
# Dica: Substitua pelos seus dados reais do bot do Telegram se já tiver configurado
TELEGRAM_BOT_TOKEN = "SEU_BOT_TOKEN_AQUI"
TELEGRAM_CHAT_ID = "SEU_CHAT_ID_AQUI"

def enviar_mensagem_telegram(mensagem):
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

# --- COMPONENTE ISOLADO: RADAR AO VIVO + ALERTA TELEGRAM ---
def renderizar_radar_com_telegram(api_key):
    st.sidebar.markdown("---")
    st.sidebar.subheader("📡 Radar Ao Vivo & Telegram")
    st.sidebar.write("Varre a partir de 2 min e envia as oportunidades direto para o seu Telegram.")
    
    if st.sidebar.button("🚀 Disparar Varredura e Notificar", type="primary"):
        with st.spinner("Varrendo partidas, filtrando e disparando alertas no Telegram..."):
            url = "https://v3.football.api-sports.io/fixtures?live=all"
            headers = {
                'x-rapidapi-host': 'v3.football.api-sports.io',
                'x-rapidapi-key': api_key
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
                        st.success(f"🎯 Varredura concluída! {len(oportunidades_lista)} jogo(s) encontrados.")
                        
                        # Se encontrou boas oportunidades de entrada, dispara o bloco no Telegram
                        if contador_alertas > 0:
                            enviar_mensagem_telegram(mensagem_telegram_lote)
                            st.sidebar.success("📲 Alertas enviados para o seu Telegram!")
                        else:
                            enviar_mensagem_telegram("🔍 Varredura executada, mas nenhum jogo atingiu os critérios de pressão exatos neste momento.")
                            st.info("ℹ️ Jogos encontrados, mas nenhum com alerta crítico de entrada no momento.")
                            
                        df_radar = pd.DataFrame(oportunidades_lista)
                        st.subheader("📊 Painel de Alertas e Entradas em Tempo Real")
                        st.dataframe(df_radar, use_container_width=True, hide_index=True)
                    else:
                        st.warning("ℹ️ Nenhum jogo acima de 2 minutos encontrado no momento.")
                else:
                    st.warning("ℹ️ Nenhuma partida oficial ao vivo encontrada.")
            except Exception as e:
                st.error(f"Erro ao conectar com a API: {e}")
