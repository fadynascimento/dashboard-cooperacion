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

def format_to_military(decimal_coord, is_lat=True):
    if decimal_coord is None: return "N/A"
    abs_val = abs(decimal_coord)
    degrees = int(abs_val)
    minutes = int((abs_val - degrees) * 60)
    designator = ("S" if decimal_coord < 0 else "N") if is_lat else ("W" if decimal_coord < 0 else "E")
    return f"{degrees:02d}°{minutes:02d}'{designator}"

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
    .block-container {{ padding: 0 1.5rem; }}

    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 80px;
        background: rgba(0, 11, 30, 0.98); z-index: 999;
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 30px; border-bottom: 1px solid rgba(0, 212, 255, 0.2);
    }}
    .zulu-time {{ font-family: 'Segoe UI', sans-serif; font-size: 1.8rem; font-weight: 300; }}
    .mission-title {{
        position: absolute; left: 50%; transform: translateX(-50%);
        font-family: 'Arial Black', sans-serif; font-size: 2.2rem;
        letter-spacing: 3px; text-shadow: 0 0 10px rgba(0, 212, 255, 0.4);
    }}
    .main-content {{ margin-top: 95px; }}
    .section-card {{
        background: rgba(0, 30, 70, 0.3); border: 1px solid rgba(0, 212, 255, 0.1);
        border-radius: 8px; padding: 10px; margin-bottom: 15px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
logo_b64 = get_base64(ARQUIVO_BOLACHA)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" height="60">' if logo_b64 else ""

st.markdown(f"""
    <div class="fixed-header">
        <div class="time-container">
            <div class="zulu-time">{now_z.strftime('%H:%M')}Z</div>
            <div style="font-size: 0.8rem; color: #ffcc00; font-weight: bold;">LOCAL: {now_p.strftime('%H:%M')}P</div>
        </div>
        <div class="mission-title">COOPERACIÓN XI</div>
        <div class="logo-container">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    # --- FILTROS E MAPA ---
    c1, c2 = st.columns([2.5, 1])
    with c1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        f1, f2, f3 = st.columns(3)
        show_met = f1.toggle("☁️ Met", value=True)
        show_foc = f2.toggle("🔥 Focos", value=True)
        show_aero = f3.toggle("✈️ Meios Aéreos", value=True)
        
        active_layers = []
        if show_met: active_layers.append("Meteorologia")
        if show_foc: active_layers.append("Focos Incd")
        if show_aero: active_layers.append("Meios Aéreos")
        
        m = folium.Map(location=[-18.5, -56.5], zoom_start=6, tiles='cartodbpositron', 
                       zoom_control=False, attribution_control=False) # REMOVE ATRIBUIÇÃO
        
        for _, row in df[df['LAYER'].isin(active_layers)].iterrows():
            if row['lat_clean'] is not None:
                color = 'red' if 'Focos' in row['LAYER'] else 'blue'
                icon = 'fire' if 'Focos' in row['LAYER'] else 'plane'
                folium.Marker([row['lat_clean'], row['lon_clean']], 
                              popup=f"{row['aeronave']} - {row['missao']}",
                              icon=folium.Icon(color=color, icon=icon, prefix='fa')).add_to(m)
        
        st_folium(m, width="100%", height=300, key="map_main")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="section-card" style="height: 385px;">', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#00d4ff; font-weight:bold;">📊 VECTORES</p>', unsafe_allow_html=True)
        st.metric("EM OPERAÇÃO", len(df[df['LAYER']=='Meios Aéreos']))
        st.dataframe(df[df['LAYER']=='Meios Aéreos'][['aeronave', 'missao']], hide_index=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TIMELINE (AGORA CENTRALIZADA) ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    df_timeline = df[df['inicio_zulu'].notna() & df['fim_zulu'].notna()].copy()
    if not df_timeline.empty:
        fig = px.timeline(df_timeline, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave", 
                          color="aeronave", template="plotly_dark", height=200)
        fig.add_vline(x=now_z, line_width=3, line_color="#ff4b4b")
        fig.update_layout(
            showlegend=False, margin=dict(l=0, r=0, t=30, b=0),
            xaxis=dict(side="top", title=None, 
                       range=[now_z - timedelta(hours=4), now_z + timedelta(hours=4)]), # CENTRALIZAÇÃO
            yaxis=dict(title=None), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

    # --- TABELA DE DADOS REINTEGRADA ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p style="color:#00ff7f; font-weight:bold; font-size:0.8rem;">📋 DETALHAMENTO DE MISSÕES</p>', unsafe_allow_html=True)
    st.dataframe(df[['LAYER', 'aeronave', 'missao', 'lat', 'lon']].dropna(subset=['aeronave']), 
                 use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
