def chamar_api_e_salvar():
    print(f"[{datetime.now()}] 🔄 Rodando rotina diária: Buscando dados da API-Football...")
    
    try:
        url = "https://v3.football.api-sports.io/status"
        headers = {
            "x-apisports-key": "e89cc081ecbaaf1a7074e878c1cae0ff"
        }
        
        resposta = requests.get(url, headers=headers)
        
        if resposta.status_code == 200:
            dados_json = resposta.json()
            
            # Ajustado para pegar especificamente a lista dentro de 'response' do JSON da API-Football
            itens = dados_json.get('response', [])
            
            if itens:
                df_novo = pd.DataFrame(itens)
            else:
                # Fallback caso a estrutura venha de outro formato
                df_novo = pd.DataFrame([dados_json])
            
            df_novo.to_csv("dados_oficiais.csv", index=False)
            print(f"[{datetime.now()}] ✅ Sucesso! Dados atualizados e salvos com sucesso.")
        else:
            print(f"[{datetime.now()}] ⚠️ Erro na API. Status code: {resposta.status_code}")
        
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Erro crítico ao atualizar dados da API: {e}")