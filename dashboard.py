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

# --- AUTO-REFRESH (30 segundos) ---
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
        # Identifica a Coluna A (primeira coluna)
        df_raw['COLUNA_A'] = df_raw.iloc[:, 0] 
        df_raw['lat_clean'] = df_raw['lat'].apply(parse_coordinate)
        df_raw['lon_clean'] = df_raw['lon'].apply(parse_coordinate)
        df_raw['inicio_zulu'] = pd.to_datetime(df_raw['inicio_zulu'], errors='coerce').dt.tz_localize('UTC')
        df_raw['fim_zulu'] = pd.to_datetime(df_raw['fim_zulu'], errors='coerce').dt.tz_localize('UTC')
        return df_raw
    except: return None

df = load_data(URL_PLANILHA)
now_z = datetime.now(timezone.utc)
now_p = datetime.now(timezone(timedelta(hours=-4)))

# --- ESTILO CSS ---
st.markdown(f"""
    <style>
    .stAppDeployButton {{ display: none !important; }}
    header {{ visibility: hidden; height: 0; }}
    [data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none !important; }}
    .stApp {{ background-color: #000b1e; color: white; }}
    .block-container {{ padding: 10px 1.5rem; }}
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 80px;
        background: rgba(0, 11, 30, 0.98); z-index: 999;
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 30px; border-bottom: 1px solid rgba(0, 212, 255, 0.2);
    }}
    .main-content {{ margin-top: 90px; }}
    .section-card {{
        background: rgba(0, 30, 70, 0.3); border: 1px solid rgba(0, 212, 255, 0.1);
        border-radius: 8px; padding: 15px; margin-bottom: 15px;
    }}
    .card-height-align {{ height: 500px; }}
    [data-testid="stMetricValue"] {{ font-size: 2.8rem !important; color: #00d4ff !important; font-weight: bold; }}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
logo_b64 = get_base64(ARQUIVO_BOLACHA)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" height="60">' if logo_b64 else ""
st.markdown(f'<div class="fixed-header"><div class="time-container"><div class="zulu-time">{now_z.strftime("%H:%M")}Z</div><div style="font-size: 0.8rem; color: #ffcc00; font-weight: bold;">LOCAL: {now_p.strftime("%H:%M")}P</div></div><div class="mission-title">COOPERACIÓN XI</div><div class="logo-container">{logo_html}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    # --- BLOCO SUPERIOR: MAPA E VECTORES ---
    col1, col2 = st.columns([2.5, 1])
    
    with col1:
        st.markdown('<div class="section-card card-height-align">', unsafe_allow_html=True)
        # Toggles de filtro
        f1, f2, f3 = st.columns(3)
        show_met = f1.toggle("☁️ Met", value=True)
        show_foc = f2.toggle("🔥 Focos", value=True)
        show_aero = f3.toggle("✈️ Medios Aéreos", value=True)
        
        m = folium.Map(location=[-18.5, -56.5], zoom_start=6, tiles='cartodbpositron', zoom_control=True, attribution_control=False)
        # (Lógica de marcadores do mapa)
        st_folium(m, width="100%", height=360, key="map_main")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-card card-height-align">', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#00d4ff; font-weight:bold; font-size:1.2rem;">📊 VECTORES</p>', unsafe_allow_html=True)
        df_aero = df[df['LAYER']=='Meios Aéreos']
        st.metric("EN OPERACIÓN", len(df_aero))
        st.dataframe(df_aero[['aeronave', 'missao']].rename(columns={'missao': 'misión'}), hide_index=True, use_container_width=True, height=300)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- LÍNEA DEL TIEMPO (CONTEÚDO DA COLUNA A CENTRALIZADO) ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p style="color:#00d4ff; font-weight:bold; font-size:1.1rem; margin-bottom:10px;">⏳ LÍNEA DEL TIEMPO</p>', unsafe_allow_html=True)
    
    # Filtro na coluna G (LAYER) para Meios Aéreos e Reuniões
    filtro = df['LAYER'].str.upper().isin(['MEIOS AÉREOS', 'REUNIÃO', 'REUNIÓN', 'REUNIAO'])
    df_timeline = df[filtro & df['inicio_zulu'].notna() & df['fim_zulu'].notna()].copy()

    if not df_timeline.empty:
        fig = px.timeline(
            df_timeline, 
            x_start="inicio_zulu", 
            x_end="fim_zulu", 
            y="aeronave", 
            color="aeronave", 
            text="COLUNA_A", # EXIBE O CONTEÚDO DA CÉLULA A
            template="plotly_dark", 
            height=400
        )
        
        fig.add_vline(x=now_z, line_width=3, line_color="#ff4b4b")
        
        fig.update_traces(
            textposition='inside', 
            insidetextanchor='middle', # Centralização absoluta
            textfont=dict(size=12, color="white")
        )

        fig.update_layout(
            showlegend=False, 
            margin=dict(l=10, r=10, t=50, b=10),
            xaxis=dict(side="top", title=None, range=[now_z - timedelta(hours=6), now_z + timedelta(hours=6)]),
            yaxis=dict(title=None), 
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

    # --- DETALLE DE MISIONES ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p style="color:#00ff7f; font-weight:bold; font-size:0.9rem;">📋 DETALLE DE MISIONES</p>', unsafe_allow_html=True)
    df_det = df[['LAYER', 'aeronave', 'missao', 'lat', 'lon']].dropna(subset=['aeronave'])
    df_det.columns = ['CAPA', 'AERONAVE', 'MISIÓN', 'LAT', 'LON']
    st.dataframe(df_det, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
