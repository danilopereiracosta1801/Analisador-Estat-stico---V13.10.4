import streamlit as st
import requests
from datetime import datetime, timedelta
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="V13 Pro v10.8 - Direct Mode", layout="wide")

class AnalisadorEngineV13:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            "Referer": "https://www.sofascore.com/",
            "Origin": "https://www.sofascore.com"
        }

    def consultar_api(self, endpoint):
        url = f"https://api.sofascore.com/api/v1/{endpoint}"
        try:
            # Timeout curto para não travar a interface
            response = requests.get(url, headers=self.headers, timeout=10, verify=False)
            return response.json() if response.status_code == 200 else {}
        except: return {}

    def obter_id(self, termo):
        # Se o utilizador digitar um número direto, usa como ID
        if termo.isdigit(): return int(termo), f"ID:{termo}"
        
        # Tenta a busca por nome
        dados = self.consultar_api(f"search/all?q={termo}")
        for item in dados.get('results', []):
            if item.get('type') == 'team':
                ent = item['entity']
                return ent['id'], ent.get('name', 'Time')
        return None, termo

    def deep_scan_v13(self, team_id):
        limite_60_dias = datetime.now() - timedelta(days=60)
        # Pega apenas a página 0 para máxima velocidade no Android
        d = self.consultar_api(f"team/{team_id}/events/last/0")
        res = []
        for ev in d.get('events', []):
            if ev.get('status', {}).get('type') != 'finished': continue
            dt = datetime.fromtimestamp(ev['startTimestamp'])
            if dt < limite_60_dias: continue
            
            gols = ev.get('homeScore', {}).get('display', 0) + ev.get('awayScore', {}).get('display', 0)
            res.append({"gols": gols})
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




