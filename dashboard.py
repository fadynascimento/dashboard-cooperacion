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

# --- CONFIGURAÇÃO DE PÁGINA (ESTRITA) ---
st.set_page_config(layout="wide", page_title="COOPERACIÓN XI - PAINEL TÁTICO", page_icon="✈️")

# Auto-refresh 15s para Consciência Situacional em Tempo Real
st_autorefresh(interval=15000, limit=None, key="refresh_dashboard")

# --- MOTOR DE PROCESSAMENTO DE COORDENADAS ---
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
        if 'surtidas' not in df_raw.columns: df_raw['surtidas'] = 1
        return df_raw
    except: return None

df = load_data(URL_PLANILHA)
now_z = datetime.now(timezone.utc)
now_l = now_z - timedelta(hours=4) # Local (MS)

# --- CSS DE ALTA PERFORMANCE (MILITAR DARK) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #001233; color: white; }}
    [data-testid="stHeader"] {{ display: none; }}
    
    /* BARRA SUPERIOR FIXA */
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 120px;
        background: rgba(0, 18, 51, 0.85); backdrop-filter: blur(12px);
        z-index: 1000; display: flex; align-items: center; justify-content: space-between;
        padding: 0 50px; border-bottom: 3px solid #00d4ff;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}
    
    .main-content {{ margin-top: 140px; padding: 0 30px; }}
    
    /* CARDS COM GLOW CIANO */
    .section-card {{
        background: rgba(0, 30, 70, 0.4); 
        border: 1px solid rgba(0, 212, 255, 0.2);
        border-radius: 8px; padding: 15px; margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3), inset 0 0 10px rgba(0,212,255,0.05);
    }}

    /* FORMATAÇÃO DE TABELAS */
    div[data-testid="stDataFrame"] {{ background: transparent !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- CABEÇALHO ---
logo_b64 = get_base64(ARQUIVO_BOLACHA)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" width="180">' if logo_b64 else ""

st.markdown(f"""
    <div class="fixed-header">
        <div style="flex: 1;">
            <div style="font-size: 2.8rem; font-weight: bold; color: white; line-height: 1;">{now_z.strftime('%H:%M:%S')} Z</div>
            <div style="font-size: 1.1rem; color: #ffcc00; font-weight: bold; margin-top: 5px;">LOCAL: {now_l.strftime('%H:%M')} P</div>
        </div>
        <div style="flex: 2; text-align: center;">
            <div style="font-family: 'Arial Black', sans-serif; font-size: 3rem; letter-spacing: 6px; color: white; text-shadow: 0 0 15px #00d4ff;">
                COOPERACIÓN XI
            </div>
        </div>
        <div style="flex: 1; text-align: right;">
            {logo_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    # --- BLOCO 1: MAPA E STATUS (SIMETRIA TOTAL) ---
    col_mapa, col_tabela = st.columns([1.5, 1])

    with col_mapa:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<p style="color:#00d4ff; font-weight:bold; margin-bottom:10px;">📍 CONSCIÊNCIA GEOGRÁFICA</p>', unsafe_allow_html=True)
        
        # Mapa com tiles claros para destacar marcadores
        m = folium.Map(location=[-18.5, -56.5], zoom_start=6, tiles='cartodbpositron', zoom_control=False)
        
        for _, row in df.dropna(subset=['lat_clean', 'lon_clean']).iterrows():
            # Vermelho para Fogo, Azul para Meios
            is_fire = 'FOGO' in str(row.get('missao', '')).upper()
            color = 'red' if is_fire else 'cadetblue'
            folium.Marker(
                [row['lat_clean'], row['lon_clean']],
                icon=folium.Icon(color=color, icon='plane' if not is_fire else 'fire', prefix='fa'),
                tooltip=f"Vetor: {row['aeronave']}"
            ).add_to(m)
        
        st_folium(m, width="100%", height=380, key="mapa_main")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_tabela:
        st.markdown('<div class="section-card" style="height: 442px;">', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#00d4ff; font-weight:bold;">📊 VECTORES EM OPERAÇÃO</p>', unsafe_allow_html=True)
        
        # Consolidação de dados
        df_v = df[df['LAYER'].str.contains("Meios", na=False)].groupby(['aeronave', 'missao'])['surtidas'].sum().reset_index()
        
        st.dataframe(df_v, use_container_width=True, hide_index=True, height=350)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- BLOCO 2: TIMELINE (CENTRALIZADA EM T) ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p style="color:#00d4ff; font-weight:bold;">🕒 LINHA DO TEMPO (T ± 4h)</p>', unsafe_allow_html=True)
    
    df_t = df[df['inicio_zulu'].notna() & df['fim_zulu'].notna()].copy()
    if not df_t.empty:
        fig = px.timeline(
            df_t, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave",
            color="aeronave", text="missao", template="plotly_dark"
        )
        # Janela de visualização centrada no tempo atual
        fig.update_layout(
            height=300, margin=dict(l=10, r=10, t=10, b=10),
            xaxis_range=[now_z - timedelta(hours=4), now_z + timedelta(hours=4)],
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
        )
        fig.add_vline(x=now_z, line_width=3, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

    # --- BLOCO 3: BANCO DE DADOS COMPLETO ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p style="color:#00d4ff; font-weight:bold;">🔍 CONSULTA GERAL DE MISSÕES</p>', unsafe_allow_html=True)
    st.dataframe(df.drop(columns=['lat_clean', 'lon_clean'], errors='ignore'), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
