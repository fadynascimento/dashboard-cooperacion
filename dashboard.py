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

# --- AUTO-REFRESH ---
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
        if 'surtidas' not in df_raw.columns: df_raw['surtidas'] = 1
        df_raw['surtidas'] = pd.to_numeric(df_raw['surtidas'], errors='coerce').fillna(1)
        return df_raw
    except: return None

df = load_data(URL_PLANILHA)
now_z = datetime.now(timezone.utc)
now_p = datetime.now(timezone(timedelta(hours=-4)))

# --- ESTILO CSS AVANÇADO ---
st.markdown(f"""
    <style>
    .stAppDeployButton {{ display: none !important; }}
    header {{ visibility: hidden; height: 0; }}
    [data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none !important; }}
    .stApp {{ background-color: #000b1e; color: white; }}
    .block-container {{ padding: 0 1.5rem; }}
    
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 135px;
        background: rgba(0, 11, 30, 0.98); z-index: 999;
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 35px; border-bottom: 2px solid rgba(0, 212, 255, 0.3);
    }}
    .mission-title {{
        position: absolute; left: 50%; transform: translateX(-50%);
        font-family: 'Arial Black', sans-serif; font-size: 2.6rem;
        letter-spacing: 5px; color: #ffffff; text-shadow: 0 0 15px rgba(0, 212, 255, 0.6);
    }}
    .main-content {{ margin-top: 150px; }}
    .section-card {{
        background: rgba(0, 30, 70, 0.4); border: 1px solid rgba(0, 212, 255, 0.2);
        border-radius: 12px; padding: 15px; margin-bottom: 20px;
    }}
    /* Ajuste de largura automática para as tabelas */
    [data-testid="stDataFrame"] {{ width: 100% !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER (BOLACHA AMPLIADA) ---
logo_b64 = get_base64(ARQUIVO_BOLACHA)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" height="125">' if logo_b64 else ""

st.markdown(f"""
    <div class="fixed-header">
        <div class="time-container">
            <div style="font-size: 2rem; font-weight: 300; letter-spacing: 1px;">{now_z.strftime('%H:%M')}Z</div>
            <div style="font-size: 1rem; color: #ffcc00; font-weight: bold;">LOCAL: {now_p.strftime('%H:%M')}P</div>
        </div>
        <div class="mission-title">COOPERACIÓN XI</div>
        <div class="logo-container">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    # --- BLOCO SUPERIOR (MAPA E RESUMO DIREITO) ---
    c_map, c_res = st.columns([2.2, 1])
    
    with c_map:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<p style="color:#00ff7f; font-weight:bold;">📍 CONCIENCIA SITUACIONAL</p>', unsafe_allow_html=True)
        
        f1, f2, f3 = st.columns(3)
        show_aero = f1.toggle("✈️ Meios Aéreos", value=True)
        show_met = f2.toggle("☁️ Met", value=True)
        show_foc = f3.toggle("🔥 Focos", value=True)
        
        m = folium.Map(location=[-18.5, -56.5], zoom_start=6, tiles='cartodbpositron', zoom_control=False, attribution_control=False)
        
        active_layers = []
        if show_aero: active_layers.append("Meios Aéreos")
        if show_met: active_layers.append("Meteorologia")
        if show_foc: active_layers.append("Focos Incd")
        
        for _, row in df[df['LAYER'].isin(active_layers)].iterrows():
            if row['lat_clean'] is not None:
                icon_type = 'plane' if 'Meios' in row['LAYER'] else ('fire' if 'Focos' in row['LAYER'] else 'cloud')
                icon_color = 'cadetblue' if 'Meios' in row['LAYER'] else ('red' if 'Focos' in row['LAYER'] else 'lightgray')
                folium.Marker([row['lat_clean'], row['lon_clean']], 
                              popup=f"{row['aeronave']}",
                              icon=folium.Icon(color=icon_color, icon=icon_type, prefix='fa')).add_to(m)
        st_folium(m, width="100%", height=380, key="map_main")
        st.markdown('</div>', unsafe_allow_html=True)

    with c_res:
        st.markdown('<div class="section-card" style="height: 520px;">', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#00d4ff; font-weight:bold; font-size:1.1rem;">📊 VECTORES EN OPERACIÓN</p>', unsafe_allow_html=True)
        df_vuelo = df[df['LAYER'] == "Meios Aéreos"].groupby(['aeronave', 'missao'])['surtidas'].sum().reset_index()
        df_vuelo.columns = ['AERONAVE', 'MISIÓN', 'SALIDAS']
        st.dataframe(df_vuelo, hide_index=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TIMELINE ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    df_timeline = df[df['inicio_zulu'].notna() & df['fim_zulu'].notna()].copy()
    if not df_timeline.empty:
        fig = px.timeline(df_timeline, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave", template="plotly_dark", height=180)
        fig.add_vline(x=now_z, line_width=3, line_color="#ff4b4b")
        fig.update_layout(xaxis=dict(side="top", range=[now_z - timedelta(hours=4), now_z + timedelta(hours=4)]),
                          yaxis=dict(title=None), showlegend=False, margin=dict(l=0, r=0, t=30, b=0),
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- TABELA FINAL COM LARGURA AJUSTADA ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p style="color:#00ff7f; font-weight:bold;">📋 DETALLE GENERAL DE OPERACIONES</p>', unsafe_allow_html=True)
    search_query = st.text_input("🔍 Filtro de Búsqueda Inteligente:", "")
    
    df_final = df[df['LAYER'] == "Meios Aéreos"].copy()
    if search_query:
        df_final = df_final[df_final['aeronave'].str.contains(search_query, case=False, na=False) | 
                            df_final['missao'].str.contains(search_query, case=False, na=False)]
    
    df_display = df_final[['aeronave', 'missao', 'surtidas', 'lat', 'lon']].copy()
    df_display.columns = ['AERONAVE', 'MISIÓN', 'SALIDAS', 'LAT', 'LON']
    
    # Configuração de colunas para ajuste automático ao conteúdo
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
