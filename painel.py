from datetime import datetime
import json
import os
import requests
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Smart Tipster - Gestão de Bilhetes", page_icon="⚽", layout="wide"
)

st.title("🤖 Smart Tipster - Gerador e Conferente de Bilhetes")


# Função para enviar mensagens ao Telegram
def enviar_telegram(token, chat_id, mensagem):
  if not token or not chat_id:
    return False
  url = f"https://api.telegram.org/bot{token}/sendMessage"
  payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
  try:
    response = requests.post(url, json=payload)
    return response.status_code == 200
  except Exception:
    return False


# Função para salvar o bilhete no histórico local
def salvar_bilhete_historico(dados_bilhete, data_str):
  arquivo = "historico_bilhetes.json"
  historico = []
  if os.path.exists(arquivo):
    try:
      with open(arquivo, "r", encoding="utf-8") as f:
        historico = json.load(f)
    except:
      historico = []

  historico.append({"data": data_str, "jogos": dados_bilhete})

  with open(arquivo, "w", encoding="utf-8") as f:
    json.dump(historico, f, ensure_ascii=False, indent=4)


# Função para buscar resultados reais da API-Sports
def conferir_resultados_dia(data_str, key):
  if not key:
    return []
  url = f"https://v3.football.api-sports.io/fixtures?date={data_str}"
  headers = {
      "x-rapidapi-host": "v3.football.api-sports.io",
      "x-rapidapi-key": key,
  }
  try:
    res = requests.get(url, headers=headers)
    data = res.json()
    resultados_conferencia = []

    if data.get("results", 0) > 0:
      for f in data["response"]:
        status = f["fixture"]["status"]["short"]

        # Considera apenas jogos encerrados (Full Time, AET, Penalidades)
        if status in ["FT", "AET", "PEN"]:
          home_name = f["teams"]["home"]["name"]
          away_name = f["teams"]["away"]["name"]
          g_home = f["goals"]["home"]
          g_away = f["goals"]["away"]

          if g_home is not None and g_away is not None:
            total_gols = g_home + g_away
            resultados_conferencia.append({
                "home": home_name,
                "away": away_name,
                "g_home": g_home,
                "g_away": g_away,
                "total_gols": total_gols,
            })
    return resultados_conferencia
  except Exception:
    return []


# --- BARRA LATERAL (CONFIGURAÇÕES) ---
st.sidebar.header("⚙️ Configurações")
api_key_input = st.sidebar.text_input(
    "API-Sports Key", type="password", value=""
)
telegram_token_input = st.sidebar.text_input(
    "Telegram Bot Token", type="password", value=""
)
telegram_chat_id_input = st.sidebar.text_input("Telegram Chat ID", value="")

data_hoje_str = datetime.now().strftime("%Y-%m-%d")
st.sidebar.markdown(f"**Data de Referência:** {data_hoje_str}")

st.sidebar.markdown("---")

# --- CORPO PRINCIPAL ---
st.subheader("📋 Painel de Controle do Bilhete")

col1, col2 = st.columns(2)

with col1:
  if st.button("🚀 Gerar & Enviar Bilhete do Dia", use_container_width=True):
    if not telegram_token_input or not telegram_chat_id_input:
      st.error(
          "Por favor, configure o Token e o Chat ID do Telegram na barra lateral."
      )
    else:
      # Exemplo de bilhete (substitua aqui pela lógica do seu algoritmo de seleção de jogos)
      bilhete_exemplo = [
          {"home": "Flamengo", "away": "Vasco", "mercado": "Over 2.5 Gols"},
          {"home": "Palmeiras", "away": "São Paulo", "mercado": "Ambas Marcam"},
      ]

      # Formata mensagem para o Telegram
      msg = (
          f"🔥 <b>BILHETE INTELIGENTE - {data_hoje_str}</b> 🔥\n\nConfira as"
          " entradas selecionadas:\n\n"
      )
      for j in bilhete_exemplo:
        msg += (
            f"⚽ <b>{j['home']} vs {j['away']}</b>\n   🎯 Palpite:"
            f" {j['mercado']}\n\n"
        )

      msg += "Boa sorte a todos! 🚀"

      # Envia para o Telegram e salva no histórico local
      if enviar_telegram(telegram_token_input, telegram_chat_id_input, msg):
        salvar_bilhete_historico(bilhete_exemplo, data_hoje_str)
        st.success("✅ Bilhete gerado, enviado ao Telegram e salvo com sucesso!")
      else:
        st.error(
            "❌ Erro ao enviar mensagem para o Telegram. Verifique suas"
            " credenciais."
        )

with col2:
  if st.button(
      "🏆 Conferir Resultados & Enviar Balanço", use_container_width=True
  ):
    if not api_key_input:
      st.error("Por favor, informe a API-Sports Key na barra lateral.")
    elif not telegram_token_input or not telegram_chat_id_input:
      st.error("Configure as credenciais do Telegram na barra lateral.")
    else:
      with st.spinner(
          "Buscando placares finais na API e calculando Greens/Reds..."
      ):
        placar_final_jogos = conferir_resultados_dia(
            data_hoje_str, api_key_input
        )

        if placar_final_jogos:
          msg_balanco = f"📈 <b>BALANÇO DOS BILHETES - {data_hoje_str}</b> 📈\n\n"

          for j in placar_final_jogos:
            # Validação simples de exemplo para o mercado de Over 2.5
            status_gols = (
                "🟢 GREEN (Over 2.5)"
                if j["total_gols"] > 2.5
                else "🔴 RED (Under 2.5)"
            )

            msg_balanco += (
                f"⚽ <b>{j['home']} {j['g_home']} x {j['g_away']}"
                f" {j['away']}</b>\n"
            )
            msg_balanco += (
                f"   • Placar Final: {j['g_home']}x{j['g_away']} (Total:"
                f" {j['total_gols']} gols) ➔ {status_gols}\n\n"
            )

          if enviar_telegram(
              telegram_token_input, telegram_chat_id_input, msg_balanco
          ):
            st.success("✅ Balanço de resultados enviado ao Telegram!")
          else:
            st.error("❌ Falha ao enviar balanço ao Telegram.")
        else:
          st.warning(
              "⚠️ Nenhum jogo finalizado (Status FT) encontrado na API para a"
              f" data {data_hoje_str} ainda."
          )
