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
        df_raw['lat_clean'] = df_raw['lat'].apply(parse_coordinate)
        df_raw['lon_clean'] = df_raw['lon'].apply(parse_coordinate)
        df_raw['inicio_zulu'] = pd.to_datetime(df_raw['inicio_zulu'], errors='coerce').dt.tz_localize('UTC')
        df_raw['fim_zulu'] = pd.to_datetime(df_raw['fim_zulu'], errors='coerce').dt.tz_localize('UTC')
        # Garantir que surtidas seja numérico para a soma
        if 'surtidas' not in df_raw.columns: df_raw['surtidas'] = 1
        df_raw['surtidas'] = pd.to_numeric(df_raw['surtidas'], errors='coerce').fillna(1)
        return df_raw
    except: return None

df = load_data(URL_PLANILHA)
now_z = datetime.now(timezone.utc)
now_p = datetime.now(timezone(timedelta(hours=-4)))

# --- ESTILO CSS REFINADO ---
st.markdown(f"""
    <style>
    .stAppDeployButton {{ display: none !important; }}
    header {{ visibility: hidden; height: 0; }}
    [data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none !important; }}
    .stApp {{ background-color: #000b1e; color: white; }}
    .block-container {{ padding: 0 1.5rem; }}

    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 120px;
        background: rgba(0, 11, 30, 0.98); z-index: 999;
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 30px; border-bottom: 1px solid rgba(0, 212, 255, 0.2);
    }}
    .zulu-time {{ font-family: 'Segoe UI', sans-serif; font-size: 1.8rem; font-weight: 300; }}
    .mission-title {{
        position: absolute; left: 50%; transform: translateX(-50%);
        font-family: 'Arial Black', sans-serif; font-size: 2.5rem;
        letter-spacing: 4px; text-shadow: 0 0 15px rgba(0, 212, 255, 0.5);
    }}
    .main-content {{ margin-top: 135px; }}
    
    /* Estilo para tabelas e métricas */
    .section-card {{
        background: rgba(0, 30, 70, 0.4); border: 1px solid rgba(0, 212, 255, 0.2);
        border-radius: 10px; padding: 15px; height: 100%;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER COM BOLACHA AMPLIADA ---
logo_b64 = get_base64(ARQUIVO_BOLACHA)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" height="110">' if logo_b64 else ""

st.markdown(f"""
    <div class="fixed-header">
        <div class="time-container">
            <div class="zulu-time">{now_z.strftime('%H:%M')}Z</div>
            <div style="font-size: 0.9rem; color: #ffcc00; font-weight: bold;">LOCAL: {now_p.strftime('%H:%M')}P</div>
        </div>
        <div class="mission-title">COOPERACIÓN XI</div>
        <div class="logo-container">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    # --- LAYOUT PRINCIPAL: MAPA (ESQ) E TABELA DE VETORES (DIR) ---
    col_mapa, col_tabela = st.columns([2, 1])
    
    with col_mapa:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<p style="color:#00ff7f; font-weight:bold; margin-bottom:10px;">📍 CONCIENCIA SITUACIONAL</p>', unsafe_allow_html=True)
        
        # Filtros rápidos
        f1, f2, f3 = st.columns(3)
        show_met = f1.toggle("☁️ Met", value=True)
        show_foc = f2.toggle("🔥 Focos", value=True)
        show_aero = f3.toggle("✈️ Aéreos", value=True)
        
        m = folium.Map(location=[-18.5, -56.5], zoom_start=6, tiles='cartodbpositron', 
                       zoom_control=False, attribution_control=False)
        
        # Lógica de visualização de vetores no mapa
        active_layers = []
        if show_met: active_layers.append("Meteorologia")
        if show_foc: active_layers.append("Focos Incd")
        if show_aero: active_layers.append("Meios Aéreos")
        
        for _, row in df[df['LAYER'].isin(active_layers)].iterrows():
            if row['lat_clean'] is not None:
                icon_type = 'plane' if 'Meios' in row['LAYER'] else 'fire'
                icon_color = 'cadetblue' if 'Meios' in row['LAYER'] else 'red'
                folium.Marker([row['lat_clean'], row['lon_clean']], 
                              popup=f"{row['aeronave']}",
                              icon=folium.Icon(color=icon_color, icon=icon_type, prefix='fa')).add_to(m)
        
        st_folium(m, width="100%", height=380, key="map_coi_v2")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_tabela:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#00d4ff; font-weight:bold; font-size:1.2rem;">📊 RESUMEN DE FLOTA</p>', unsafe_allow_html=True)
        
        # Agregando surtidas por aeronave
        df_resumo = df[df['LAYER'] == "Meios Aéreos"].groupby(['aeronave', 'missao'])['surtidas'].sum().reset_index()
        df_resumo.columns = ['AERONAVE', 'MISIÓN', 'SALIDAS'] # Tradução para espanhol
        
        st.metric("VECTORES ACTIVOS", len(df_resumo))
        st.dataframe(df_resumo, hide_index=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TIMELINE CENTRALIZADA ---
    st.markdown('<div style="margin-top:15px;" class="section-card">', unsafe_allow_html=True)
    df_timeline = df[df['inicio_zulu'].notna() & df['fim_zulu'].notna()].copy()
    if not df_timeline.empty:
        fig = px.timeline(df_timeline, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave", 
                          color="aeronave", template="plotly_dark", height=180)
        fig.add_vline(x=now_z, line_width=3, line_color="#ff4b4b")
        fig.update_layout(
            showlegend=False, margin=dict(l=0, r=0, t=30, b=0),
            xaxis=dict(side="top", title=None, range=[now_z - timedelta(hours=4), now_z + timedelta(hours=4)]),
            yaxis=dict(title=None), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
