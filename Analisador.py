import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="V13 Pro v10.6 - Final", layout="wide")

class AnalisadorEngineV13:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.sofascore.com/",
            "Origin": "https://www.sofascore.com"
        }

    def consultar_api(self, endpoint):
        url = f"https://api.sofascore.com/api/v1/{endpoint}"
        for _ in range(3):
            try:
                response = requests.get(url, headers=self.headers, timeout=20, verify=False)
                if response.status_code == 200: return response.json()
                time.sleep(0.5)
            except: continue
        return {}

    def buscar_time_id(self, query):
        # Tenta a busca original
        dados = self.consultar_api(f"search/all?q={query}")
        
        # Se falhar e for sigla, tenta expandir (ex: PSG -> Paris Saint-Germain)
        if not dados.get('results') and query.upper() == "PSG":
            dados = self.consultar_api("search/all?q=Paris%20Saint-Germain")
        
        for item in dados.get('results', []):
            if item.get('type') == 'team':
                ent = item['entity']
                return ent['id'], ent.get('name', 'Time')
        return None, query

    def buscar_odd_evento(self, team_id, oponente_id):
        proximos = self.consultar_api(f"team/{team_id}/events/next/0")
        for ev in proximos.get('events', []):
            h_id = ev.get('homeTeam', {}).get('id')
            a_id = ev.get('awayTeam', {}).get('id')
            if h_id == oponente_id or a_id == oponente_id:
                try:
                    odds = self.consultar_api(f"event/{ev['id']}/odds/1/all")
                    for m in odds.get('markets', []):
                        if m.get('marketName') == 'Full time':
                            c = m.get('choices', [])
                            return min(float(c[0]['value']), float(c[2]['value']))
                except: pass
        return 2.0

    def deep_scan_v13(self, team_id, limite=5):
        limite_60_dias = datetime.now() - timedelta(days=60)
        eventos = []
        for p in [0, 1]:
            d = self.consultar_api(f"team/{team_id}/events/last/{p}")
            eventos.extend(d.get('events', []))
            
        res = []
        for ev in [e for e in eventos if e.get('status', {}).get('type') == 'finished']:
            if len(res) >= limite: break
            dt = datetime.fromtimestamp(ev['startTimestamp'])
            if dt < limite_60_dias: continue
            
            h_n = ev.get('homeTeam', {}).get('shortName', ev.get('homeTeam', {}).get('name', 'Casa'))
            a_n = ev.get('awayTeam', {}).get('shortName', ev.get('awayTeam', {}).get('name', 'Fora'))
            res.append({"data": dt.strftime('%d/%m'), "gols": ev['homeScore']['display'] + ev['awayScore']['display'], "confronto": f"{h_n} x {a_n}"})
        return res

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




