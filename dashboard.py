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
st.set_page_config(layout="wide", page_title="COOPERACIÓN XI - COI", page_icon="✈️")

# Auto-refresh
st_autorefresh(interval=30000, limit=None, key="refresh_dashboard")

# --- PROCESSAMENTO DE COORDENADAS ---
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
        df_raw['lat_clean'] = df_raw['lat'].apply(parse_coordinate)
        df_raw['lon_clean'] = df_raw['lon'].apply(parse_coordinate)
        df_raw['inicio_zulu'] = pd.to_datetime(df_raw['inicio_zulu'], errors='coerce').dt.tz_localize('UTC')
        df_raw['fim_zulu'] = pd.to_datetime(df_raw['fim_zulu'], errors='coerce').dt.tz_localize('UTC')
        return df_raw
    except: return None

df = load_data(URL_PLANILHA)
now_z = datetime.now(timezone.utc)
now_p = datetime.now(timezone(timedelta(hours=-4)))

# --- CSS RADICAL: POSICIONAMENTO E LIMPEZA ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #000b1e; color: white; }}
    [data-testid="stHeader"] {{ display: none; }}
    
    /* REMOÇÃO DA MARCA D'ÁGUA CARTO/LEAFLET */
    .leaflet-control-attribution, .leaflet-bottom.leaflet-right, .leaflet-control-zoom {{
        display: none !important;
        visibility: hidden !important;
    }}
    
    /* HEADER COMPACTO */
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 80px;
        background: #000b1e; z-index: 999;
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 30px; border-bottom: 2px solid #00d4ff;
    }}
    
    /* BOLACHA FLUTUANTE */
    .floating-logo {{
        position: fixed; top: 10px; right: 20px; z-index: 1001;
        filter: drop-shadow(0 0 10px #000);
    }}
    
    .main-content {{ margin-top: 100px; }}
    
    .section-card {{
        background: rgba(0, 30, 70, 0.4); 
        border: 1px solid rgba(0, 212, 255, 0.1);
        border-radius: 4px; padding: 10px;
    }}

    /* Ajuste para forçar alinhamento lado a lado */
    [data-testid="column"] {{ padding: 0 !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- ELEMENTOS FLUTUANTES E HEADER ---
logo_b64 = get_base64(ARQUIVO_BOLACHA)
if logo_b64:
    st.markdown(f'<div class="floating-logo"><img src="data:image/png;base64,{logo_b64}" height="130"></div>', unsafe_allow_html=True)

st.markdown(f"""
    <div class="fixed-header">
        <div style="min-width: 200px;">
            <div style="font-size: 1.8rem; font-weight: bold; color: white;">{now_z.strftime('%H:%M:%S')}Z</div>
            <div style="font-size: 0.9rem; color: #ffcc00; font-weight: bold;">LOCAL: {now_p.strftime('%H:%M')}P</div>
        </div>
        <div style="font-family: 'Arial Black'; font-size: 2.2rem; color: white; text-shadow: 0 0 10px #00d4ff;">COOPERACIÓN XI</div>
        <div style="min-width: 200px;"></div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    # --- DASHBOARD TÁTICO: MAPA E VECTORES (LADO A LADO FIXO) ---
    col_map, col_table = st.columns([1.8, 1])
    
    with col_map:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        m = folium.Map(location=[-18.5, -56.5], zoom_start=6, tiles='cartodbpositron', zoom_control=False)
        # Plotagem dos marcadores
        for _, row in df.dropna(subset=['lat_clean', 'lon_clean']).iterrows():
            icon_c = 'cadetblue' if 'Meios' in row['LAYER'] else 'red'
            folium.Marker([row['lat_clean'], row['lon_clean']], 
                          icon=folium.Icon(color=icon_c, icon='plane', prefix='fa')).add_to(m)
        
        st_folium(m, width="100%", height=400, key="mapa_operacional_clean")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_table:
        st.markdown('<div class="section-card" style="height: 422px;">', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#00d4ff; font-weight:bold; margin:0;">📊 VECTORES EM OPERAÇÃO</p>', unsafe_allow_html=True)
        
        # Tabela de Vectores com qualidade de dataframe
        df_v = df[df['LAYER'] == "Meios Aéreos"].groupby(['aeronave', 'missao']).size().reset_index()
        df_v.columns = ['AERONAVE', 'MISIÓN', 'QTDE']
        st.dataframe(df_v, use_container_width=True, hide_index=True, height=350)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TIMELINE ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    df_t = df[df['inicio_zulu'].notna() & df['fim_zulu'].notna()].copy()
    if not df_t.empty:
        fig = px.timeline(df_t, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave", 
                          text=df_t.iloc[:, 0], color="aeronave", template="plotly_dark")
        fig.add_vline(x=now_z, line_width=3, line_color="#ff4b4b")
        fig.update_layout(height=220, margin=dict(l=0, r=0, t=20, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- BUSCA E TABELA DETALHADA ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    col_search, _ = st.columns([1, 2])
    with col_search:
        busca = st.text_input("🔍 Filtro Global de Missões", placeholder="Digite aeronave ou local...")
    
    df_f = df[df.apply(lambda r: busca.lower() in r.astype(str).str.lower().values, axis=1)] if busca else df
    st.dataframe(df_f.drop(columns=['lat_clean', 'lon_clean'], errors='ignore'), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
