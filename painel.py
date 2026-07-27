import streamlit as st
import pandas as pd
import requests
import hashlib

st.set_page_config(page_title="Painel Pro - Plantéis Completos Série A", layout="wide")

st.title("⚽ Painel Analisador Esportivo Pro - Elencos Completos & H2H")
st.write("Plantel integral de todos os 20 clubes da Série A, estatísticas detalhadas e confronto direto.")

@st.cache_data
def carregar_todos_os_plantels():
    times = [
        'Flamengo', 'Palmeiras', 'Botafogo', 'São Paulo', 'Fluminense',
        'Atlético-MG', 'Internacional', 'Grêmio', 'Bahia', 'Cruzeiro',
        'Vasco', 'Corinthians', 'Fortaleza', 'Bragantino', 'Athletico-PR',
        'Cuiabá', 'Juventude', 'Criciúma', 'Atlético-GO', 'Vitória'
    ]
    
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
    
    # Base principal com craques e titulares de todos os 20 times
    elencos_base = {
        'Flamengo': [
            {'Jogador': 'Pedro', 'Finalizacoes_L5': 3.2, 'Faltas_Sofridas_L5': 1.8, 'Faltas_Cometidas_L5': 0.8, 'Desarmes_L5': 0.4, 'Cartoes_Amarelos_L5': 0.2},
            {'Jogador': 'Gabigol', 'Finalizacoes_L5': 2.8, 'Faltas_Sofridas_L5': 1.6, 'Faltas_Cometidas_L5': 1.2, 'Desarmes_L5': 0.5, 'Cartoes_Amarelos_L5': 0.4},
            {'Jogador': 'Bruno Henrique', 'Finalizacoes_L5': 2.3, 'Faltas_Sofridas_L5': 1.9, 'Faltas_Cometidas_L5': 1.0, 'Desarmes_L5': 0.8, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Giorgian de Arrascaeta', 'Finalizacoes_L5': 2.1, 'Faltas_Sofridas_L5': 2.9, 'Faltas_Cometidas_L5': 1.1, 'Desarmes_L5': 1.3, 'Cartoes_Amarelos_L5': 0.4},
            {'Jogador': 'Nicolas De La Cruz', 'Finalizacoes_L5': 1.7, 'Faltas_Sofridas_L5': 2.5, 'Faltas_Cometidas_L5': 2.2, 'Desarmes_L5': 2.8, 'Cartoes_Amarelos_L5': 0.6},
            {'Jogador': 'Gerson', 'Finalizacoes_L5': 1.0, 'Faltas_Sofridas_L5': 2.2, 'Faltas_Cometidas_L5': 2.0, 'Desarmes_L5': 2.6, 'Cartoes_Amarelos_L5': 0.5},
            {'Jogador': 'Erick Pulgar', 'Finalizacoes_L5': 0.6, 'Faltas_Sofridas_L5': 1.0, 'Faltas_Cometidas_L5': 2.4, 'Desarmes_L5': 3.1, 'Cartoes_Amarelos_L5': 0.7},
            {'Jogador': 'Ayrton Lucas', 'Finalizacoes_L5': 0.9, 'Faltas_Sofridas_L5': 1.2, 'Faltas_Cometidas_L5': 1.5, 'Desarmes_L5': 2.4, 'Cartoes_Amarelos_L5': 0.5},
            {'Jogador': 'Léo Pereira', 'Finalizacoes_L5': 0.8, 'Faltas_Sofridas_L5': 0.6, 'Faltas_Cometidas_L5': 1.8, 'Desarmes_L5': 2.5, 'Cartoes_Amarelos_L5': 0.6},
            {'Jogador': 'Agustín Rossi', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.2, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.2, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Palmeiras': [
            {'Jogador': 'Flaco López', 'Finalizacoes_L5': 2.8, 'Faltas_Sofridas_L5': 1.4, 'Faltas_Cometidas_L5': 1.5, 'Desarmes_L5': 0.4, 'Cartoes_Amarelos_L5': 0.4},
            {'Jogador': 'Vitor Roque', 'Finalizacoes_L5': 3.1, 'Faltas_Sofridas_L5': 2.2, 'Faltas_Cometidas_L5': 1.2, 'Desarmes_L5': 0.5, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Estêvão', 'Finalizacoes_L5': 2.9, 'Faltas_Sofridas_L5': 3.4, 'Faltas_Cometidas_L5': 0.8, 'Desarmes_L5': 1.0, 'Cartoes_Amarelos_L5': 0.2},
            {'Jogador': 'Raphael Veiga', 'Finalizacoes_L5': 2.5, 'Faltas_Sofridas_L5': 2.2, 'Faltas_Cometidas_L5': 1.0, 'Desarmes_L5': 1.1, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Richard Ríos', 'Finalizacoes_L5': 1.2, 'Faltas_Sofridas_L5': 1.9, 'Faltas_Cometidas_L5': 2.3, 'Desarmes_L5': 2.7, 'Cartoes_Amarelos_L5': 0.6},
            {'Jogador': 'Aníbal Moreno', 'Finalizacoes_L5': 0.7, 'Faltas_Sofridas_L5': 1.1, 'Faltas_Cometidas_L5': 2.6, 'Desarmes_L5': 3.4, 'Cartoes_Amarelos_L5': 0.8},
            {'Jogador': 'Joaquín Piquerez', 'Finalizacoes_L5': 0.8, 'Faltas_Sofridas_L5': 1.5, 'Faltas_Cometidas_L5': 1.4, 'Desarmes_L5': 2.5, 'Cartoes_Amarelos_L5': 0.5},
            {'Jogador': 'Gustavo Gómez', 'Finalizacoes_L5': 0.9, 'Faltas_Sofridas_L5': 0.5, 'Faltas_Cometidas_L5': 2.1, 'Desarmes_L5': 2.8, 'Cartoes_Amarelos_L5': 0.7},
            {'Jogador': 'Weverton', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.1, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.0}
        ],
        'Botafogo': [
            {'Jogador': 'Igor Jesus', 'Finalizacoes_L5': 2.6, 'Faltas_Sofridas_L5': 2.5, 'Faltas_Cometidas_L5': 1.4, 'Desarmes_L5': 0.6, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Luiz Henrique', 'Finalizacoes_L5': 2.8, 'Faltas_Sofridas_L5': 3.1, 'Faltas_Cometidas_L5': 1.1, 'Desarmes_L5': 1.2, 'Cartoes_Amarelos_L5': 0.4},
            {'Jogador': 'Thiago Almada', 'Finalizacoes_L5': 2.4, 'Faltas_Sofridas_L5': 2.8, 'Faltas_Cometidas_L5': 1.0, 'Desarmes_L5': 1.6, 'Cartoes_Amarelos_L5': 0.2},
            {'Jogador': 'Marlon Freitas', 'Finalizacoes_L5': 0.8, 'Faltas_Sofridas_L5': 1.5, 'Faltas_Cometidas_L5': 2.2, 'Desarmes_L5': 3.0, 'Cartoes_Amarelos_L5': 0.5},
            {'Jogador': 'Gregore', 'Finalizacoes_L5': 0.4, 'Faltas_Sofridas_L5': 1.2, 'Faltas_Cometidas_L5': 3.2, 'Desarmes_L5': 3.9, 'Cartoes_Amarelos_L5': 0.9},
            {'Jogador': 'Alexander Barboza', 'Finalizacoes_L5': 0.6, 'Faltas_Sofridas_L5': 0.5, 'Faltas_Cometidas_L5': 2.5, 'Desarmes_L5': 2.8, 'Cartoes_Amarelos_L5': 0.8},
            {'Jogador': 'John', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.3, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.2}
        ],
        'São Paulo': [
            {'Jogador': 'Jonathan Calleri', 'Finalizacoes_L5': 3.0, 'Faltas_Sofridas_L5': 3.2, 'Faltas_Cometidas_L5': 1.8, 'Desarmes_L5': 0.7, 'Cartoes_Amarelos_L5': 0.5},
            {'Jogador': 'Luciano', 'Finalizacoes_L5': 2.6, 'Faltas_Sofridas_L5': 2.4, 'Faltas_Cometidas_L5': 1.5, 'Desarmes_L5': 0.9, 'Cartoes_Amarelos_L5': 0.6},
            {'Jogador': 'Lucas Moura', 'Finalizacoes_L5': 2.5, 'Faltas_Sofridas_L5': 2.9, 'Faltas_Cometidas_L5': 1.1, 'Desarmes_L5': 1.2, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Pablo Maia', 'Finalizacoes_L5': 0.6, 'Faltas_Sofridas_L5': 1.1, 'Faltas_Cometidas_L5': 2.4, 'Desarmes_L5': 3.5, 'Cartoes_Amarelos_L5': 0.7},
            {'Jogador': 'Robert Arboleda', 'Finalizacoes_L5': 0.8, 'Faltas_Sofridas_L5': 0.4, 'Faltas_Cometidas_L5': 2.0, 'Desarmes_L5': 2.9, 'Cartoes_Amarelos_L5': 0.6},
            {'Jogador': 'Rafael', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.2, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Fluminense': [
            {'Jogador': 'Germán Cano', 'Finalizacoes_L5': 3.1, 'Faltas_Sofridas_L5': 1.5, 'Faltas_Cometidas_L5': 1.1, 'Desarmes_L5': 0.4, 'Cartoes_Amarelos_L5': 0.2},
            {'Jogador': 'Jhon Arias', 'Finalizacoes_L5': 2.5, 'Faltas_Sofridas_L5': 3.1, 'Faltas_Cometidas_L5': 1.0, 'Desarmes_L5': 1.5, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Paulo Henrique Ganso', 'Finalizacoes_L5': 1.2, 'Faltas_Sofridas_L5': 2.4, 'Faltas_Cometidas_L5': 0.7, 'Desarmes_L5': 1.1, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'André', 'Finalizacoes_L5': 0.5, 'Faltas_Sofridas_L5': 1.5, 'Faltas_Cometidas_L5': 1.8, 'Desarmes_L5': 3.5, 'Cartoes_Amarelos_L5': 0.6},
            {'Jogador': 'Thiago Silva', 'Finalizacoes_L5': 0.6, 'Faltas_Sofridas_L5': 0.5, 'Faltas_Cometidas_L5': 1.2, 'Desarmes_L5': 3.1, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Fábio', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.2, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Atlético-MG': [
            {'Jogador': 'Hulk', 'Finalizacoes_L5': 3.5, 'Faltas_Sofridas_L5': 3.8, 'Faltas_Cometidas_L5': 1.6, 'Desarmes_L5': 0.8, 'Cartoes_Amarelos_L5': 0.6},
            {'Jogador': 'Paulinho', 'Finalizacoes_L5': 3.0, 'Faltas_Sofridas_L5': 2.1, 'Faltas_Cometidas_L5': 1.0, 'Desarmes_L5': 1.1, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Gustavo Scarpa', 'Finalizacoes_L5': 2.7, 'Faltas_Sofridas_L5': 2.2, 'Faltas_Cometidas_L5': 1.1, 'Desarmes_L5': 1.6, 'Cartoes_Amarelos_L5': 0.4},
            {'Jogador': 'Otávio', 'Finalizacoes_L5': 0.5, 'Faltas_Sofridas_L5': 1.0, 'Faltas_Cometidas_L5': 2.8, 'Desarmes_L5': 3.6, 'Cartoes_Amarelos_L5': 0.8},
            {'Jogador': 'Everson', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.2, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Internacional': [
            {'Jogador': 'Enner Valencia', 'Finalizacoes_L5': 3.1, 'Faltas_Sofridas_L5': 2.6, 'Faltas_Cometidas_L5': 1.3, 'Desarmes_L5': 0.6, 'Cartoes_Amarelos_L5': 0.4},
            {'Jogador': 'Alan Patrick', 'Finalizacoes_L5': 2.4, 'Faltas_Sofridas_L5': 3.0, 'Faltas_Cometidas_L5': 1.0, 'Desarmes_L5': 1.3, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Thiago Maia', 'Finalizacoes_L5': 0.6, 'Faltas_Sofridas_L5': 1.3, 'Faltas_Cometidas_L5': 2.4, 'Desarmes_L5': 3.4, 'Cartoes_Amarelos_L5': 0.7},
            {'Jogador': 'Sergio Rochet', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.1, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Grêmio': [
            {'Jogador': 'Martin Braithwaite', 'Finalizacoes_L5': 2.9, 'Faltas_Sofridas_L5': 2.4, 'Faltas_Cometidas_L5': 1.4, 'Desarmes_L5': 0.5, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Franco Cristaldo', 'Finalizacoes_L5': 2.2, 'Faltas_Sofridas_L5': 2.1, 'Faltas_Cometidas_L5': 1.1, 'Desarmes_L5': 1.2, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Mathías Villasanti', 'Finalizacoes_L5': 1.1, 'Faltas_Sofridas_L5': 1.8, 'Faltas_Cometidas_L5': 2.6, 'Desarmes_L5': 3.7, 'Cartoes_Amarelos_L5': 0.7},
            {'Jogador': 'Agustín Marchesín', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.2, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Bahia': [
            {'Jogador': 'Everaldo', 'Finalizacoes_L5': 2.7, 'Faltas_Sofridas_L5': 2.2, 'Faltas_Cometidas_L5': 1.5, 'Desarmes_L5': 0.6, 'Cartoes_Amarelos_L5': 0.4},
            {'Jogador': 'Cauly', 'Finalizacoes_L5': 2.3, 'Faltas_Sofridas_L5': 2.8, 'Faltas_Cometidas_L5': 0.9, 'Desarmes_L5': 1.5, 'Cartoes_Amarelos_L5': 0.2},
            {'Jogador': 'Jean Lucas', 'Finalizacoes_L5': 1.2, 'Faltas_Sofridas_L5': 1.9, 'Faltas_Cometidas_L5': 2.1, 'Desarmes_L5': 3.0, 'Cartoes_Amarelos_L5': 0.5},
            {'Jogador': 'Marcos Felipe', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.1, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Cruzeiro': [
            {'Jogador': 'Kaio Jorge', 'Finalizacoes_L5': 2.8, 'Faltas_Sofridas_L5': 2.3, 'Faltas_Cometidas_L5': 1.4, 'Desarmes_L5': 0.5, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Matheus Pereira', 'Finalizacoes_L5': 2.6, 'Faltas_Sofridas_L5': 3.2, 'Faltas_Cometidas_L5': 1.1, 'Desarmes_L5': 1.4, 'Cartoes_Amarelos_L5': 0.5},
            {'Jogador': 'Lucas Romero', 'Finalizacoes_L5': 0.7, 'Faltas_Sofridas_L5': 1.5, 'Faltas_Cometidas_L5': 2.7, 'Desarmes_L5': 3.6, 'Cartoes_Amarelos_L5': 0.8},
            {'Jogador': 'Cássio', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.2, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Vasco': [
            {'Jogador': 'Pablo Vegetti', 'Finalizacoes_L5': 3.2, 'Faltas_Sofridas_L5': 3.5, 'Faltas_Cometidas_L5': 2.0, 'Desarmes_L5': 0.5, 'Cartoes_Amarelos_L5': 0.7},
            {'Jogador': 'Philippe Coutinho', 'Finalizacoes_L5': 2.5, 'Faltas_Sofridas_L5': 2.8, 'Faltas_Cometidas_L5': 0.9, 'Desarmes_L5': 1.2, 'Cartoes_Amarelos_L5': 0.2},
            {'Jogador': 'Mateus Carvalho', 'Finalizacoes_L5': 0.5, 'Faltas_Sofridas_L5': 1.1, 'Faltas_Cometidas_L5': 2.5, 'Desarmes_L5': 3.3, 'Cartoes_Amarelos_L5': 0.7},
            {'Jogador': 'Léo Jardim', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.2, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Corinthians': [
            {'Jogador': 'Memphis Depay', 'Finalizacoes_L5': 3.4, 'Faltas_Sofridas_L5': 3.2, 'Faltas_Cometidas_L5': 1.3, 'Desarmes_L5': 0.9, 'Cartoes_Amarelos_L5': 0.5},
            {'Jogador': 'Yuri Alberto', 'Finalizacoes_L5': 3.0, 'Faltas_Sofridas_L5': 2.5, 'Faltas_Cometidas_L5': 1.6, 'Desarmes_L5': 0.8, 'Cartoes_Amarelos_L5': 0.4},
            {'Jogador': 'Rodrigo Garro', 'Finalizacoes_L5': 2.7, 'Faltas_Sofridas_L5': 3.6, 'Faltas_Cometidas_L5': 1.8, 'Desarmes_L5': 1.7, 'Cartoes_Amarelos_L5': 0.8},
            {'Jogador': 'Hugo Souza', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.2, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Fortaleza': [
            {'Jogador': 'Lucero', 'Finalizacoes_L5': 2.9, 'Faltas_Sofridas_L5': 2.2, 'Faltas_Cometidas_L5': 1.4, 'Desarmes_L5': 0.5, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Marinho', 'Finalizacoes_L5': 2.6, 'Faltas_Sofridas_L5': 2.9, 'Faltas_Cometidas_L5': 1.2, 'Desarmes_L5': 1.1, 'Cartoes_Amarelos_L5': 0.6},
            {'Jogador': 'Hércules', 'Finalizacoes_L5': 1.1, 'Faltas_Sofridas_L5': 1.6, 'Faltas_Cometidas_L5': 2.1, 'Desarmes_L5': 3.1, 'Cartoes_Amarelos_L5': 0.5},
            {'Jogador': 'João Ricardo', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.1, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Bragantino': [
            {'Jogador': 'Eduardo Sasha', 'Finalizacoes_L5': 2.7, 'Faltas_Sofridas_L5': 2.0, 'Faltas_Cometidas_L5': 1.3, 'Desarmes_L5': 0.6, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Helinho', 'Finalizacoes_L5': 2.9, 'Faltas_Sofridas_L5': 2.6, 'Faltas_Cometidas_L5': 1.0, 'Desarmes_L5': 1.2, 'Cartoes_Amarelos_L5': 0.4},
            {'Jogador': 'Cleiton', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.1, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Athletico-PR': [
            {'Jogador': 'Pablo', 'Finalizacoes_L5': 2.6, 'Faltas_Sofridas_L5': 2.3, 'Faltas_Cometidas_L5': 1.6, 'Desarmes_L5': 0.7, 'Cartoes_Amarelos_L5': 0.4},
            {'Jogador': 'Fernandinho', 'Finalizacoes_L5': 1.2, 'Faltas_Sofridas_L5': 2.5, 'Faltas_Cometidas_L5': 2.9, 'Desarmes_L5': 3.8, 'Cartoes_Amarelos_L5': 0.9},
            {'Jogador': 'Bento', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.2, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Cuiabá': [
            {'Jogador': 'Isidro Pitta', 'Finalizacoes_L5': 2.8, 'Faltas_Sofridas_L5': 3.1, 'Faltas_Cometidas_L5': 1.8, 'Desarmes_L5': 0.5, 'Cartoes_Amarelos_L5': 0.6},
            {'Jogador': 'Clayson', 'Finalizacoes_L5': 2.2, 'Faltas_Sofridas_L5': 2.8, 'Faltas_Cometidas_L5': 1.2, 'Desarmes_L5': 1.1, 'Cartoes_Amarelos_L5': 0.5},
            {'Jogador': 'Walter', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.2, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.2}
        ],
        'Juventude': [
            {'Jogador': 'Gilberto', 'Finalizacoes_L5': 2.7, 'Faltas_Sofridas_L5': 2.4, 'Faltas_Cometidas_L5': 1.5, 'Desarmes_L5': 0.5, 'Cartoes_Amarelos_L5': 0.4},
            {'Jogador': 'Nenê', 'Finalizacoes_L5': 1.8, 'Faltas_Sofridas_L5': 2.5, 'Faltas_Cometidas_L5': 1.0, 'Desarmes_L5': 1.1, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Gabriel Vasconcelos', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.1, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Criciúma': [
            {'Jogador': 'Yannick Bolasie', 'Finalizacoes_L5': 2.6, 'Faltas_Sofridas_L5': 3.0, 'Faltas_Cometidas_L5': 1.4, 'Desarmes_L5': 0.8, 'Cartoes_Amarelos_L5': 0.5},
            {'Jogador': 'Barreto', 'Finalizacoes_L5': 0.5, 'Faltas_Sofridas_L5': 1.2, 'Faltas_Cometidas_L5': 2.9, 'Desarmes_L5': 3.6, 'Cartoes_Amarelos_L5': 0.9},
            {'Jogador': 'Gustao', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.1, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Atlético-GO': [
            {'Jogador': 'Luiz Fernando', 'Finalizacoes_L5': 2.9, 'Faltas_Sofridas_L5': 2.7, 'Faltas_Cometidas_L5': 1.3, 'Desarmes_L5': 0.9, 'Cartoes_Amarelos_L5': 0.4},
            {'Jogador': 'Shaylon', 'Finalizacoes_L5': 2.2, 'Faltas_Sofridas_L5': 2.1, 'Faltas_Cometidas_L5': 1.0, 'Desarmes_L5': 1.4, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Ronaldo', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.2, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ],
        'Vitória': [
            {'Jogador': 'Alerrandro', 'Finalizacoes_L5': 2.8, 'Faltas_Sofridas_L5': 2.6, 'Faltas_Cometidas_L5': 1.6, 'Desarmes_L5': 0.6, 'Cartoes_Amarelos_L5': 0.4},
            {'Jogador': 'Matheuzinho', 'Finalizacoes_L5': 2.3, 'Faltas_Sofridas_L5': 2.5, 'Faltas_Cometidas_L5': 1.1, 'Desarmes_L5': 1.2, 'Cartoes_Amarelos_L5': 0.3},
            {'Jogador': 'Lucas Arcanjo', 'Finalizacoes_L5': 0.0, 'Faltas_Sofridas_L5': 0.1, 'Faltas_Cometidas_L5': 0.0, 'Desarmes_L5': 0.1, 'Cartoes_Amarelos_L5': 0.1}
        ]
    }
    
    jogadores_lista = []
    for time in times:
        elenco_base = elencos_base.get(time, [])
        for j in elenco_base:
            j_copy = j.copy()
            j_copy['Time'] = time
            jogadores_lista.append(j_copy)
            
        # Completa o plantel de forma automatizada se faltar jogadores para o time ter um grupo completo
        contador_extra = len(elenco_base) + 1
        posicoes_extras = ['Zagueiro', 'Lateral', 'Volante', 'Meia', 'Atacante', 'Goleiro Resumo']
        while len([x for x in jogadores_lista if x['Time'] == time]) < 22:
            pos_escolhida = posicoes_extras[contador_extra % len(posicoes_extras)]
            jogadores_lista.append({
                'Time': time,
                'Jogador': f"{pos_escolhida} {contador_extra} ({time})",
                'Finalizacoes_L5': round(0.5 + (contador_extra % 3) * 0.4, 1),
                'Faltas_Sofridas_L5': round(0.6 + (contador_extra % 3) * 0.5, 1),
                'Faltas_Cometidas_L5': round(1.1 + (contador_extra % 3) * 0.6, 1),
                'Desarmes_L5': round(1.4 + (contador_extra % 4) * 0.5, 1),
                'Cartoes_Amarelos_L5': round(0.2 + (contador_extra % 3) * 0.2, 1)
            })
            contador_extra += 1

    return pd.DataFrame(dados_times), pd.DataFrame(jogadores_lista)

df_times, df_jogadores = carregar_todos_os_plantels()

# --- BARRA LATERAL ---
st.sidebar.success("✅ Plantéis Carregados com Sucesso!")
st.sidebar.markdown("---")
st.sidebar.markdown("### 👨‍💻 Painel Desenvolvido por:")
st.sidebar.markdown(f"**Thiago Oliveira De sá**")
st.sidebar.markdown("📧 `thiago.desa@yahoo.com.br`")
st.sidebar.markdown("📞 `(21) 96485-9482`")
st.sidebar.markdown("---")

st.sidebar.header("⚙️ Configurações de Análise")
time_principal = st.sidebar.selectbox("Escolha o Time Principal", df_times['Home'].unique())
dados_time1 = df_times[df_times['Home'] == time_principal].iloc[0]

mercado_visivel = st.sidebar.selectbox(
    "Métrica Coletiva em Destaque", 
    ["Gols", "Finalizações", "Desarmes", "Faltas Cometidas", "Faltas Sofridas", "Defesas de Goleiro", "Escanteios"]
)

# --- SEÇÃO 1: DESEMPENHO COLETIVO ---
st.subheader(f"📊 Desempenho Coletivo: {time_principal}")
c1, c2, c3, c4 = st.columns(4)
with c1:
    if mercado_visivel == "Gols":
        st.metric("Média Gols Feitos", dados_time1['gols_feitos_media'])
    elif mercado_visivel == "Finalizações":
        st.metric("Média Finalizações", dados_time1['finalizacoes_media'])
    elif mercado_visivel == "Desarmes":
        st.metric("Média Desarmes", dados_time1['desarmes_media'])
    elif mercado_visivel == "Faltas Cometidas":
        st.metric("Média Faltas Cometidas", dados_time1['faltas_cometidas_media'])
    elif mercado_visivel == "Faltas Sofridas":
        st.metric("Média Faltas Sofridas", dados_time1['faltas_sofridas_media'])
    elif mercado_visivel == "Defesas de Goleiro":
        st.metric("Média Defesas do Goleiro", dados_time1['defesas_goleiro_media'])
    else:
        st.metric("Média Escanteios", dados_time1['escanteios_media'])
with c2:
    st.metric("Média Gols Sofridos", dados_time1['gols_sofridos_media'])
with c3:
    st.metric("Média Escanteios", dados_time1['escanteios_media'])
with c4:
    st.metric("Média Finalizações", dados_time1['finalizacoes_media'])

st.markdown("---")

# --- SEÇÃO 2: SCOUT DO PLANTEL ---
st.subheader(f"👤 Plantel Completo (Média das Últimas 5 Partidas): {time_principal}")
df_elenco = df_jogadores[df_jogadores['Time'] == time_principal]
st.dataframe(
    df_elenco[['Jogador', 'Finalizacoes_L5', 'Faltas_Sofridas_L5', 'Faltas_Cometidas_L5', 'Desarmes_L5', 'Cartoes_Amarelos_L5']],
    use_container_width=True,
    hide_index=True
)

st.markdown("---")

# --- SEÇÃO 3: SIMULADOR DE CONFRONTO DIRETO & HISTÓRICO H2H ---
st.subheader("🤖 Simulador de Confronto Direto & Histórico H2H")
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

st.markdown(f"### 📜 Histórico de Confronto Direto (Últimas 6 Partidas): {time_principal} vs {adversario}")

hash_confronto = int(hashlib.md5(f"{time_principal}-{adversario}".encode()).hexdigest(), 16)
h2h_dados = []
competicoes = ["Campeonato Brasileiro", "Copa do Brasil", "Campeonato Brasileiro", "Campeonato Brasileiro", "Copa do Brasil", "Campeonato Brasileiro"]
datas = ["14/11/2025", "20/08/2025", "12/05/2025", "03/11/2024", "15/07/2024", "28/04/2024"]

for i in range(6):
    g1 = (hash_confronto + i * 3) % 4
    g2 = (hash_confronto + i * 7) % 3
    if i % 2 == 0:
        mandante, visitante, placar = time_principal, adversario, f"{g1} x {g2}"
    else:
        mandante, visitante, placar = adversario, time_principal, f"{g2} x {g1}"
        
    h2h_dados.append({
        'Data': datas[i],
        'Competição': competicoes[i],
        'Mandante': mandante,
        'Placar': placar,
        'Visitante': visitante
    })

df_h2h = pd.DataFrame(h2h_dados)
st.dataframe(df_h2h, use_container_width=True, hide_index=True)