import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
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
        # Coluna A é a primeira coluna do DF
        df_raw['label_timeline'] = df_raw.iloc[:, 0].astype(str)
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

# --- ESTILO CSS PARA TRAVAR LAYOUT ---
st.markdown(f"""
    <style>
    .stAppDeployButton {{ display: none !important; }}
    header {{ visibility: hidden; height: 0; }}
    [data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none !important; }}
    .stApp {{ background-color: #000b1e; color: white; overflow-x: hidden; }}
    
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 120px;
        background: rgba(0, 11, 30, 0.98); z-index: 999;
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 40px; border-bottom: 2px solid #00d4ff;
    }}
    .mission-title {{
        position: absolute; left: 50%; transform: translateX(-50%);
        font-family: 'Arial Black', sans-serif; font-size: 2.5rem;
        letter-spacing: 5px; text-shadow: 0 0 15px #00d4ff;
    }}
    .main-content {{ margin-top: 140px; }}
    
    /* Forçar colunas lado a lado */
    [data-testid="column"] {{ min-width: 300px !important; }}
    
    .section-card {{
        background: rgba(0, 30, 70, 0.5); border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 10px; padding: 15px; margin-bottom: 10px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
logo_b64 = get_base64(ARQUIVO_BOLACHA)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" height="135">' if logo_b64 else ""

st.markdown(f"""
    <div class="fixed-header">
        <div class="time-container">
            <div style="font-size: 1.9rem; font-weight: bold; color: white;">{now_z.strftime('%H:%M:%S')}Z</div>
            <div style="font-size: 1rem; color: #ffcc00; font-weight: bold;">LOCAL: {now_p.strftime('%H:%M')}P</div>
        </div>
        <div class="mission-title">COOPERACIÓN XI</div>
        <div class="logo-container">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    # --- FILA SUPERIOR: MAPA E TABELA LADO A LADO ---
    c_map, c_res = st.columns([2.3, 1])
    
    with c_map:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        f1, f2, f3 = st.columns(3)
        show_aero = f1.toggle("✈️ Meios Aéreos", value=True)
        show_met = f2.toggle("☁️ Met", value=True)
        show_foc = f3.toggle("🔥 Focos", value=True)
        
        m = folium.Map(location=[-18.5, -56.5], zoom_start=6, tiles='cartodbpositron', zoom_control=False, attribution_control=False)
        
        active_layers = [l for l, v in zip(["Meios Aéreos", "Meteorologia", "Focos Incd"], [show_aero, show_met, show_foc]) if v]
        for _, row in df[df['LAYER'].isin(active_layers)].iterrows():
            if row['lat_clean'] is not None:
                icon = 'plane' if 'Meios' in row['LAYER'] else ('fire' if 'Focos' in row['LAYER'] else 'cloud')
                color = 'cadetblue' if 'Meios' in row['LAYER'] else ('red' if 'Focos' in row['LAYER'] else 'lightgray')
                folium.Marker([row['lat_clean'], row['lon_clean']], popup=row['aeronave'],
                              icon=folium.Icon(color=color, icon=icon, prefix='fa')).add_to(m)
        st_folium(m, width="100%", height=380, key="map_coi")
        st.markdown('</div>', unsafe_allow_html=True)

    with c_res:
        st.markdown('<div class="section-card" style="height: 485px; overflow-y: auto;">', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#00d4ff; font-weight:bold;">📊 VECTORES EN OPERACIÓN</p>', unsafe_allow_html=True)
        df_vuelo = df[df['LAYER'] == "Meios Aéreos"].groupby(['aeronave', 'missao'])['surtidas'].sum().reset_index()
        df_vuelo.columns = ['AERONAVE', 'MISIÓN', 'SALIDAS']
        st.dataframe(df_vuelo, hide_index=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TIMELINE COM CONTEÚDO DENTRO E CORES DINÂMICAS ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    df_timeline = df[df['inicio_zulu'].notna() & df['fim_zulu'].notna()].copy()
    
    if not df_timeline.empty:
        # Lógica de Cor: se a coluna 'cor' (ou similar) existir ou se o senhor quiser via Coluna A
        # Aqui, usamos Aeronave para alternar cores se não houver cor específica definida
        fig = px.timeline(df_timeline, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave", 
                          text="label_timeline", # CONTEÚDO DA COLUNA A DENTRO DO POLÍGONO
                          color="aeronave", 
                          template="plotly_dark", height=220)
        
        fig.add_vline(x=now_z, line_width=4, line_color="#ff4b4b")
        fig.update_traces(textposition='inside', insidetextanchor='middle')
        fig.update_layout(
            showlegend=False, margin=dict(l=0, r=0, t=35, b=0),
            xaxis=dict(side="top", range=[now_z - timedelta(hours=4), now_z + timedelta(hours=4)]),
            yaxis=dict(title=None)
        )
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- TABELA FINAL COM LARGURA FIT ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p style="color:#00ff7f; font-weight:bold;">📋 LISTADO GENERAL DE MEDIOS</p>', unsafe_allow_html=True)
    query = st.text_input("🔍 Filtro Inteligente:", key="search_final")
    
    df_f = df[df['LAYER'] == "Meios Aéreos"].copy()
    if query:
        df_f = df_f[df_f['aeronave'].str.contains(query, case=False, na=False) | df_f['missao'].str.contains(query, case=False, na=False)]
    
    df_disp = df_f[['aeronave', 'missao', 'surtidas', 'lat', 'lon']].copy()
    df_disp.columns = ['AERONAVE', 'MISIÓN', 'SALIDAS', 'LAT', 'LON']
    st.dataframe(df_disp, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
