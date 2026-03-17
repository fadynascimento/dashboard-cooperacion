import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from datetime import datetime, timezone, timedelta
import os
import base64
import time
import re
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAÇÃO DE PÁGINA ---
st.set_page_config(layout="wide", page_title="COOPERACIÓN XI - PAINEL DE OPERAÇÕES", page_icon="✈️")

# Auto-refresh 15s
st_autorefresh(interval=15000, limit=None, key="refresh_dashboard")

# --- FUNÇÕES AUXILIARES ---
def parse_coordinate(coord):
    if pd.isna(coord) or str(coord).strip() == "": return None
    c = str(coord).strip().upper().replace(',', '.')
    parts = re.findall(r"[-+]?\d*\.\d+|\d+", c)
    if not parts: return None
    try:
        if len(parts) == 1: val = float(parts[0])
        elif len(parts) == 2: val = float(parts[0]) + (float(parts[1]) / 60)
        else: val = float(parts[0]) + (float(parts[1]) / 60) + (float(parts[2]) / 3600)
        if 'S' in c or 'W' in c: val = -abs(val)
        return val
    except: return None

def get_base64(bin_file):
    if os.path.exists(bin_file):
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    return None

# --- CARGA DE DADOS ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSxvtVEGGjxGS316VCXhFUDv7AA9WaPSNql8ncUFu6Kn0d39BPr7XMS6WSSn8JJ6VAVDUAJ9AshQ1bi/pub?output=csv"
ARQUIVO_BOLACHA = "bolcaha cooperacion.png"

@st.cache_data(ttl=5)
def load_data(url):
    try:
        df_raw = pd.read_csv(f"{url}&ts={int(time.time())}")
        df_raw.columns = [c.strip() for c in df_raw.columns]
        # Captura Coluna A para a Timeline
        df_raw['coluna_a'] = df_raw.iloc[:, 0].astype(str) 
        df_raw['lat_clean'] = df_raw['lat'].apply(parse_coordinate)
        df_raw['lon_clean'] = df_raw['lon'].apply(parse_coordinate)
        df_raw['inicio_zulu'] = pd.to_datetime(df_raw['inicio_zulu'], errors='coerce').dt.tz_localize('UTC')
        df_raw['fim_zulu'] = pd.to_datetime(df_raw['fim_zulu'], errors='coerce').dt.tz_localize('UTC')
        return df_raw
    except: return None

df = load_data(URL_PLANILHA)
now_z = datetime.now(timezone.utc)
now_l = now_z - timedelta(hours=4)

# --- CSS PERSONALIZADO ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
    
    .stApp {{ 
        background-color: #001233; 
        background-image: radial-gradient(circle at 50% 50%, #001e4d 0%, #001233 100%);
        color: #e0e0e0; 
    }}
    
    [data-testid="stHeader"] {{ display: none; }}
    
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 100px;
        background: rgba(0, 18, 51, 0.9); backdrop-filter: blur(10px);
        z-index: 1000; display: flex; align-items: center; justify-content: space-between;
        padding: 0 30px; border-bottom: 2px solid #00d4ff;
    }}

    .main-content {{ margin-top: 110px; }}

    .section-card {{
        background: rgba(0, 30, 70, 0.4); 
        border-radius: 4px; padding: 15px; 
        box-shadow: 5px 5px 15px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }}

    .status-panel {{
        background: rgba(0, 40, 85, 0.6);
        border: 1px solid #00d4ff;
        padding: 12px; border-radius: 8px;
    }}

    [data-testid="stMetricValue"] {{ font-size: 1.5rem !important; font-family: 'Orbitron'; color: #ffffff; }}
    [data-testid="stMetricLabel"] {{ font-size: 0.8rem !important; color: #00d4ff; }}

    h3, h4 {{ font-family: 'Orbitron', sans-serif !important; color: #00d4ff !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
logo_b64 = get_base64(ARQUIVO_BOLACHA)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" width="180">' if logo_b64 else ""

st.markdown(f"""
    <div class="fixed-header">
        <div style="flex: 1;">
            <div style="font-family: 'Orbitron'; font-size: 1.8rem; color: #ffffff;">{now_z.strftime('%H:%M:%S')} Z</div>
            <div style="font-size: 0.9rem; color: #ffcc00; font-weight: bold;">LOCAL: {now_l.strftime('%H:%M')} P</div>
        </div>
        <div style="flex: 2; text-align: center;">
            <div style="font-family: 'Orbitron'; font-size: 2.2rem; font-weight: bold; letter-spacing: 5px; text-shadow: 0 0 10px #00d4ff;">
                COOPERACIÓN XI
            </div>
        </div>
        <div style="flex: 1; text-align: right;">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    # --- FILTRO PARA MEIOS AÉREOS (Tabela Direita e Métricas) ---
    # Filtra apenas linhas onde a coluna LAYER contenha "Meios" (case insensitive)
    df_aereo = df[df['LAYER'].str.contains("Meios", case=False, na=False)].copy()

    # --- LINHA 1: MAPA E STATUS ---
    col_map, col_stat = st.columns([2.3, 1])

    with col_map:
        st.markdown('<div class="section-card" style="border-left: 4px solid #00d4ff;">', unsafe_allow_html=True)
        m = folium.Map(location=[-19.5, -57.0], zoom_start=6, tiles='cartodbpositron', zoom_control=False)
        for _, row in df.dropna(subset=['lat_clean', 'lon_clean']).iterrows():
            is_fire = 'FOGO' in str(row.get('missao', '')).upper()
            color = 'red' if is_fire else 'blue'
            folium.Marker(
                [row['lat_clean'], row['lon_clean']],
                icon=folium.Icon(color=color, icon='plane' if not is_fire else 'fire', prefix='fa')
            ).add_to(m)
        st_folium(m, width="100%", height=400, key="mapa_operacional")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_stat:
        st.markdown('<div class="status-panel">', unsafe_allow_html=True)
        st.markdown('<h4 style="font-size: 0.85rem; text-align: center; margin-bottom:15px;">📊 STATUS MEIOS AÉREOS</h4>', unsafe_allow_html=True)
        
        m1, m2 = st.columns(2)
        m1.metric("VETORES", df_aereo['aeronave'].nunique())
        m2.metric("MISSÕES", len(df_aereo))
        
        st.markdown('<div style="margin: 10px 0; border-top: 1px solid rgba(0,212,255,0.2);"></div>', unsafe_allow_html=True)
        
        # Tabela apenas com Meios Aéreos
        df_resumo = df_aereo.groupby(['aeronave', 'missao']).size().reset_index(name='QTD')
        st.dataframe(df_resumo, use_container_width=True, hide_index=True, height=265)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- LINHA 2: TIMELINE (CENTRALIZADA NA COLUNA A + GLOW LINE) ---
    st.markdown('<div class="section-card" style="border-left: 4px solid #ffcc00;">', unsafe_allow_html=True)
    st.markdown('<h3 style="font-size: 1.2rem; margin-bottom:15px;">🕒 CRONOGRAMA OPERACIONAL (COLUNA A)</h3>', unsafe_allow_html=True)
    
    df_t = df[df['inicio_zulu'].notna() & df['fim_zulu'].notna()].copy()
    if not df_t.empty:
        # Usando 'coluna_a' para o eixo Y e texto
        fig = px.timeline(
            df_t, x_start="inicio_zulu", x_end="fim_zulu", y="coluna_a",
            color="aeronave", text="coluna_a", template="plotly_dark"
        )
        
        t_min, t_max = now_z - timedelta(hours=4), now_z + timedelta(hours=4)
        
        # Estilização da Linha de Tempo com GLOW
        fig.add_vline(x=now_z, line_width=4, line_color="rgba(255, 0, 0, 0.8)")
        # Camada de Glow (linha mais grossa e transparente por baixo)
        fig.add_vline(x=now_z, line_width=10, line_color="rgba(255, 0, 0, 0.2)")

        fig.update_layout(
            height=350,
            xaxis_range=[t_min, t_max],
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="HORA ZULU"),
            yaxis=dict(title=None, gridcolor="rgba(255,255,255,0.05)"),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

    # --- DETALHAMENTO INFERIOR ---
    with st.expander("🔍 LOG COMPLETO DE DADOS"):
        st.dataframe(df.drop(columns=['lat_clean', 'lon_clean'], errors='ignore'), use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)
