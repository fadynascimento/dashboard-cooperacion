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

# Auto-refresh 30s
st_autorefresh(interval=30000, limit=None, key="refresh_dashboard")

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
        df_raw['label_timeline'] = df_raw.iloc[:, 0].astype(str)
        df_raw['lat_clean'] = df_raw['lat'].apply(parse_coordinate)
        df_raw['lon_clean'] = df_raw['lon'].apply(parse_coordinate)
        df_raw['inicio_zulu'] = pd.to_datetime(df_raw['inicio_zulu'], errors='coerce').dt.tz_localize('UTC')
        df_raw['fim_zulu'] = pd.to_datetime(df_raw['fim_zulu'], errors='coerce').dt.tz_localize('UTC')
        if 'surtidas' not in df_raw.columns: df_raw['surtidas'] = 1
        return df_raw
    except: return None

df = load_data(URL_PLANILHA)
now_z = datetime.now(timezone.utc)
now_p = datetime.now(timezone(timedelta(hours=-4)))

# --- CSS AVANÇADO ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #000b1e; color: white; }}
    [data-testid="stHeader"] {{ display: none; }}
    
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 110px;
        background: #000b1e; z-index: 1000;
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 40px; border-bottom: 2px solid #00d4ff;
    }}
    
    .main-content {{ margin-top: 130px; }}
    
    .section-card {{
        background: rgba(0, 30, 70, 0.4); 
        border: 1px solid rgba(0, 212, 255, 0.1);
        border-radius: 4px; 
        padding: 15px; 
        margin-bottom: 15px;
    }}

    /* Estilização para garantir que a tabela ocupe o espaço correto */
    div[data-testid="stTable"] {{
        background: transparent !important;
        margin-top: 10px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
logo_b64 = get_base64(ARQUIVO_BOLACHA)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" height="110">' if logo_b64 else ""

st.markdown(f"""
    <div class="fixed-header">
        <div style="min-width: 250px;">
            <div style="font-size: 2.5rem; font-weight: bold; color: white;">{now_z.strftime('%H:%M:%S')}Z</div>
            <div style="font-size: 1.1rem; color: #ffcc00; font-weight: bold;">LOCAL: {now_p.strftime('%H:%M')}P</div>
        </div>
        <div style="font-family: 'Arial Black'; font-size: 2.8rem; letter-spacing: 4px; color: white; text-shadow: 0 0 15px #00d4ff;">COOPERACIÓN XI</div>
        <div style="min-width: 250px; text-align: right;">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    # --- 1. DASHBOARD TÁTICO: MAPA E RESUMO LADO A LADO ---
    col_map, col_stat = st.columns([1.6, 1])
    
    with col_map:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        m = folium.Map(location=[-18.5, -56.5], zoom_start=6, tiles='cartodbpositron', zoom_control=False)
        for _, row in df.dropna(subset=['lat_clean', 'lon_clean']).iterrows():
            c = 'cadetblue' if 'Meios' in str(row.get('LAYER', '')) else 'red'
            folium.Marker([row['lat_clean'], row['lon_clean']], 
                          icon=folium.Icon(color=c, icon='plane', prefix='fa')).add_to(m)
        st_folium(m, width="100%", height=400, key="mapa_coi")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_stat:
        # Tudo aqui dentro será renderizado no painel à direita do mapa
        st.markdown('<div class="section-card" style="height: 425px;">', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#00d4ff; font-weight:bold; margin-bottom: 20px;">📊 VECTORES EM OPERAÇÃO</p>', unsafe_allow_html=True)
        
        # Lógica de dados para a tabela lateral
        df_v = df[df['LAYER'].str.contains("Meios", na=False)].groupby(['aeronave', 'missao'])['surtidas'].sum().reset_index()
        
        # Renderização da tabela DENTRO da coluna lateral
        st.dataframe(df_v, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 2. TIMELINE ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    df_t = df[df['inicio_zulu'].notna() & df['fim_zulu'].notna()].copy()
    if not df_t.empty:
        fig = px.timeline(df_t, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave", 
                          text="label_timeline", color="aeronave", template="plotly_dark")
        fig.add_vline(x=now_z, line_width=3, line_color="red")
        fig.update_layout(height=280, margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. CAMPO DE BUSCA E TABELA DETALHADA ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p style="color:#00d4ff; font-weight:bold;">🔍 BUSCA RÁPIDA DE MISSÕES</p>', unsafe_allow_html=True)
    busca = st.text_input("Filtrar por aeronave, missão ou localidade:", placeholder="Ex: C-105")
    
    if busca:
        df_filtered = df[df.apply(lambda row: busca.lower() in row.astype(str).str.lower().values, axis=1)]
    else:
        df_filtered = df

    st.dataframe(df_filtered.drop(columns=['lat_clean', 'lon_clean', 'label_timeline'], errors='ignore'), 
                  use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
