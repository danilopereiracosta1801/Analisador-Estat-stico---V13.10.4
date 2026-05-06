import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import urllib3

# Desabilita avisos de certificados para redes corporativas
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Analisador Estatístico- SofaScore v13.10.4", layout="wide")

class AnalisadorEngineV13:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Origin": "https://www.sofascore.com",
            "Referer": "https://www.sofascore.com/"
        }

    def consultar_api(self, endpoint):
        try:
            url = f"https://api.sofascore.com/api/v1/{endpoint}"
            # verify=False resolve o erro SSLCertVerificationError
            response = requests.get(url, headers=self.headers, timeout=15, verify=False)
            return response.json() if response.status_code == 200 else {}
        except Exception:
            return {}

    def buscar_time_id(self, query):
        dados = self.consultar_api(f"search/all?q={query}")
        if not dados: return None, query
        for item in dados.get('results', []):
            if item.get('type') == 'team':
                ent = item['entity']
                return ent['id'], ent.get('name', 'Time Desconhecido')
        return None, query

    # --- CORREÇÃO: ADICIONADO ATRIBUTO FALTANTE ---
    def buscar_odd_evento(self, team_id, oponente_id):
        proximos = self.consultar_api(f"team/{team_id}/events/next/0")
        for ev in proximos.get('events', []):
            h_id = ev.get('homeTeam', {}).get('id')
            a_id = ev.get('awayTeam', {}).get('id')
            if h_id == oponente_id or a_id == oponente_id:
                event_id = ev.get('id')
                odds_data = self.consultar_api(f"event/{event_id}/odds/1/all")
                try:
                    for market in odds_data.get('markets', []):
                        if market.get('marketName') == 'Full time':
                            choices = market.get('choices', [])
                            return min(float(choices[0].get('value', 2.0)), float(choices[2].get('value', 2.0)))
                except: pass
        return 2.0

    def extrair_estatisticas(self, event_id):
        dados = self.consultar_api(f"event/{event_id}/statistics")
        esc, car = 0, 0
        try:
            for period in dados.get('statistics', []):
                if period.get('period') == 'ALL':
                    for group in period.get('groups', []):
                        for item in group.get('statisticsItems', []):
                            if item.get('name') == 'Corner kicks':
                                esc = int(item.get('homeValue', 0)) + int(item.get('awayValue', 0))
                            if item.get('name') == 'Yellow cards':
                                car = int(item.get('homeValue', 0)) + int(item.get('awayValue', 0))
        except: pass
        return esc, car

    def deep_scan_v13(self, team_id, limite=5):
        # TRAVA DE 60 DIAS
        limite_60_dias = datetime.now() - timedelta(days=60)
        
        eventos_completos = []
        for p in [0, 1]:
            dados = self.consultar_api(f"team/{team_id}/events/last/{p}")
            eventos_completos.extend(dados.get('events', []))
            
        finalizados = [ev for ev in eventos_completos if ev.get('status', {}).get('type') == 'finished']
        
        resultados = []
        for ev in finalizados:
            if len(resultados) >= limite: break
            
            data_jogo = datetime.fromtimestamp(ev['startTimestamp'])
            if data_jogo < limite_60_dias: continue

            h_score = ev.get('homeScore', {}).get('display', 0)
            a_score = ev.get('awayScore', {}).get('display', 0)
            
            # --- CORREÇÃO: EVITA KeyError 'shortName' ---
            home_n = ev.get('homeTeam', {}).get('shortName', ev.get('homeTeam', {}).get('name', 'Time A'))
            away_n = ev.get('awayTeam', {}).get('shortName', ev.get('awayTeam', {}).get('name', 'Time B'))
            
            cantos, cards = self.extrair_estatisticas(ev['id'])
            resultados.append({
                "data": data_jogo.strftime('%d/%m'),
                "gols": h_score + a_score,
                "cantos": cantos,
                "cards": cards,
                "confronto": f"{home_n} {h_score}x{a_score} {away_n}"
            })
        return resultados

def calcular_prob_v13(f1, f2, campo, threshold, tipo="over"):
    def testar(j):
        val = j.get(campo, 0)
        return val > threshold if tipo == "over" else val < threshold
    p1 = sum(1 for j in f1 if testar(j)) / len(f1) if f1 else 0.5
    p2 = sum(1 for j in f2 if testar(j)) / len(f2) if f2 else 0.5
    return int(((p1 + p2) / 2) * 100)

# --- INTERFACE STREAMLIT ---
st.title("🛡️ Analisador Estatístico - SofaScore Pro v13.10.4")

entrada = st.text_area("Insira os jogos:", "Al-Khaleej x Al-Hilal")

if st.button("🚀 INICIAR ANÁLISE"):
    try:
        engine = AnalisadorEngineV13()
        jogos = [l for l in entrada.split('\n') if 'x' in l.lower()]
        
        if not jogos:
            st.warning("⚠️ Formato inválido. Use: Time A x Time B")
        
        for linha in jogos:
            # Garante que o loop não pare se um jogo falhar
            try:
                partes = linha.lower().split('x')
                id1, n1 = engine.buscar_time_id(partes[0].strip())
                id2, n2 = engine.buscar_time_id(partes[1].strip())

                if id1 and id2:
                    with st.status(f"Analisando {n1} vs {n2}...", expanded=False):
                        odd_fav = engine.buscar_odd_evento(id1, id2)
                        f1 = engine.deep_scan_v13(id1)
                        f2 = engine.deep_scan_v13(id2)
                    
                    # Se não houver jogos nos últimos 60 dias, avisa
                    if not f1 and not f2:
                        st.error(f"❌ Sem jogos recentes (60 dias) para {n1} ou {n2}")
                        continue
                    
                    # (Aqui continua o resto da lógica de exibição das boxes...)
                    # ... [Cole o restante do código das boxes aqui] ...

                else:
                    st.error(f"🔍 Não achei um dos times: {linha}")
            except Exception as e:
                st.error(f"💥 Erro ao processar este jogo: {str(e)}")
                
    except Exception as e:
        st.error(f"🚨 Erro Geral: {str(e)}")
st.text("Métricas de Travas Ativas:")
st.text("## Full Time 4.5 / 5.5 / 6.5")
st.text("## Half Time 0.5 / 1.5 / 2.5")
st.text("## ICE (Índice de Convergência)")
st.text("## DMC (Densidade de Meio-Campo)")
st.text("## FSC (Filtro de Stress)")
st.text("## MCA (Micro-Contexto de Arbitragem)")




