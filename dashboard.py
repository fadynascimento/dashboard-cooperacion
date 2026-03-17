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

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="COOPERACIÓN XI - COI", page_icon="✈️")

# Auto-refresh a cada 30 segundos para manter os dados vivos
st_autorefresh(interval=30000, limit=None, key="refresh_dashboard")

# --- FUNCIONES AUXILIARES ---
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

# --- CARGA DE DATOS ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSxvtVEGGjxGS316VCXhFUDv7AA9WaPSNql8ncUFu6Kn0d39BPr7XMS6WSSn8JJ6VAVDUAJ9AshQ1bi/pub?output=csv"
ARQUIVO_BOLACHA = "bolcaha cooperacion.png"

@st.cache_data(ttl=5)
def load_data(url):
    try:
        df_raw = pd.read_csv(f"{url}&ts={int(time.time())}")
        df_raw.columns = [c.strip() for c in df_raw.columns]
        df_raw['label_timeline'] = df_raw.iloc[:, 0].astype(str)
        df_raw['lat_clean'] = df_raw['lat'].apply(parse_coordinate)
        df_raw['lon_clean'] = df_raw['lon'].apply(parse_coordinate)
        df_raw['inicio_zulu'] = pd.to_datetime(df_raw['inicio_zulu'], errors='coerce').dt.tz_localize('UTC')
        df_raw['fim_zulu'] = pd.to_datetime(df_raw['fim_zulu'], errors='coerce').dt.tz_localize('UTC')
        return df_raw
    except: return None

df = load_data(URL_PLANILHA)
now_z = datetime.now(timezone.utc)
now_p = datetime.now(timezone(timedelta(hours=-4)))

# --- CSS PARA REMOVER O POLÍGONO AZUL E TRAVAR POSIÇÃO ---
st.markdown(f"""
    <style>
    /* Reset Geral */
    .stApp {{ background-color: #000b1e; color: white; }}
    [data-testid="stHeader"] {{ display: none; }}
    
    /* Remove o polígono azul/bordas de todos os blocos */
    [data-testid="stVerticalBlock"], [data-testid="column"], .st-emotion-cache-1r6slb0 {{
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
    }}
    
    /* Limpeza do Mapa */
    .leaflet-control-attribution {{ display: none !important; }}
    .leaflet-control-zoom {{ display: none !important; }}
    
    /* Header Fixo e Estilizado */
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 100px;
        background: #000b1e; z-index: 1000;
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 30px; border-bottom: 2px solid #00d4ff;
    }}
    
    .main-content {{ margin-top: 120px; }}
    
    .section-card {{
        background: rgba(0, 30, 70, 0.4); 
        border-radius: 4px; padding: 10px;
    }}
    
    /* Ajuste da Tabela */
    table {{ width: 100% !important; background-color: transparent !important; color: white !important; }}
    th {{ color: #00d4ff !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
logo_b64 = get_base64(ARQUIVO_BOLACHA)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" height="110">' if logo_b64 else ""

st.markdown(f"""
    <div class="fixed-header">
        <div style="min-width: 200px;">
            <div style="font-size: 2.2rem; font-weight: bold; color: white;">{now_z.strftime('%H:%M:%S')}Z</div>
            <div style="font-size: 1rem; color: #ffcc00; font-weight: bold;">LOCAL: {now_p.strftime('%H:%M')}P</div>
        </div>
        <div style="font-family: 'Arial Black'; font-size: 2.5rem; color: white; text-shadow: 0 0 10px #00d4ff;">COOPERACIÓN XI</div>
        <div style="min-width: 200px; text-align: right;">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    # --- DASHBOARD SUPERIOR: MAPA E TABELA LADO A LADO (TRAVADO) ---
    col_mapa, col_tabela = st.columns([1.5, 1]) # Proporção ideal para caber lado a lado
    
    with col_mapa:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        m = folium.Map(location=[-18.5, -56.5], zoom_start=6, tiles='cartodbpositron', zoom_control=False)
        
        # Plotagem dos marcadores
        for _, row in df.dropna(subset=['lat_clean', 'lon_clean']).iterrows():
            icon_color = 'cadetblue' if 'Meios' in row['LAYER'] else 'red'
            folium.Marker([row['lat_clean'], row['lon_clean']], 
                          icon=folium.Icon(color=icon_color, icon='plane', prefix='fa')).add_to(m)
        
        st_folium(m, width="100%", height=380, key="mapa_operacional")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_tabela:
        st.markdown('<div class="section-card" style="height: 405px;">', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#00d4ff; font-weight:bold; font-size:1.1rem;">📊 VECTORES EM OPERAÇÃO</p>', unsafe_allow_html=True)
        
        df_v = df[df['LAYER'] == "Meios Aéreos"].groupby(['aeronave', 'missao']).size().reset_index()
        df_v.columns = ['AERONAVE', 'MISIÓN', 'SALIDAS']
        
        # Usando st.table para evitar o container azul de interação do dataframe
        st.table(df_v)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TIMELINE (ABAIXO, LARGURA TOTAL) ---
    st.markdown('<div class="section-card" style="margin-top:15px;">', unsafe_allow_html=True)
    df_t = df[df['inicio_zulu'].notna() & df['fim_zulu'].notna()].copy()
    if not df_t.empty:
        fig = px.timeline(df_t, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave", 
                          text="label_timeline", color="aeronave", template="plotly_dark")
        fig.add_vline(x=now_z, line_width=3, line_color="#ff4b4b")
        fig.update_layout(height=250, margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
        fig.update_traces(textposition='inside')
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
