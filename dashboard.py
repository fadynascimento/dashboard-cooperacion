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

# Auto-refresh 15s (Padrão Tático)
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

# --- CSS TÁTICO AVANÇADO ---
st.markdown(f"""
    <style>
    .stApp {{ 
        background-color: #001233; 
        color: white; 
    }}
    [data-testid="stHeader"] {{ display: none; }}
    
    /* HEADER FIXO */
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 130px;
        background: rgba(0, 18, 51, 0.9); backdrop-filter: blur(10px);
        z-index: 1000; display: flex; align-items: center; justify-content: space-between;
        padding: 0 40px; border-bottom: 3px solid #00d4ff;
    }}
    
    .main-content {{ margin-top: 150px; padding: 10px 25px; }}
    
    /* CARDS OPERACIONAIS */
    .section-card {{
        background: rgba(0, 30, 70, 0.5); 
        border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 8px; padding: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    }}

    /* FORCE SIDE-BY-SIDE (Otimização de Colunas) */
    [data-testid="column"] {{
        padding: 0 10px !important;
    }}
    
    /* Estilo de Tabela Compacta */
    .stDataFrame, .stTable {{
        border: none !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER (COM BOLACHA AMPLIADA) ---
logo_b64 = get_base64(ARQUIVO_BOLACHA)
# Aumentado para width=180 conforme diretriz original
logo_html = f'<img src="data:image/png;base64,{logo_b64}" width="180">' if logo_b64 else ""

st.markdown(f"""
    <div class="fixed-header">
        <div style="flex: 1;">
            <div style="font-size: 2.8rem; font-weight: bold; color: white; line-height: 1;">{now_z.strftime('%H:%M:%S')}Z</div>
            <div style="font-size: 1.2rem; color: #ffcc00; font-weight: bold;">LOCAL: {now_p.strftime('%H:%M')}P</div>
        </div>
        <div style="flex: 2; text-align: center;">
            <div style="font-family: 'Arial Black'; font-size: 3rem; letter-spacing: 5px; color: white; text-shadow: 0 0 20px #00d4ff;">COOPERACIÓN XI</div>
        </div>
        <div style="flex: 1; text-align: right;">
            {logo_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    # --- BLOCO 1: MAPA E STATUS (RIGOROSAMENTE LADO A LADO) ---
    c1, c2 = st.columns([1.5, 1])

    with c1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<p style="color:#00d4ff; font-weight:bold; margin-bottom:10px;">📍 SITUAÇÃO GEOGRÁFICA</p>', unsafe_allow_html=True)
        m = folium.Map(location=[-18.5, -56.5], zoom_start=6, tiles='cartodbpositron', zoom_control=False)
        
        for _, row in df.dropna(subset=['lat_clean', 'lon_clean']).iterrows():
            # Diferenciação visual por LAYER
            color = 'blue' if 'Meios' in str(row.get('LAYER', '')) else 'red'
            folium.Marker(
                [row['lat_clean'], row['lon_clean']], 
                icon=folium.Icon(color=color, icon='plane', prefix='fa'),
                tooltip=f"{row['aeronave']} - {row['missao']}"
            ).add_to(m)
        
        # Largura definida para evitar expulsão da coluna 2
        st_folium(m, width="100%", height=350, key="mapa_final")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="section-card" style="height: 412px;">', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#00d4ff; font-weight:bold;">📊 VECTORES EM OPERAÇÃO</p>', unsafe_allow_html=True)
        
        df_v = df[df['LAYER'].str.contains("Meios", na=False)].groupby(['aeronave', 'missao'])['surtidas'].sum().reset_index()
        
        # Tabela tática compacta
        st.dataframe(
            df_v, 
            use_container_width=True, 
            hide_index=True, 
            height=320
        )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<br>', unsafe_allow_html=True)

    # --- BLOCO 2: TIMELINE CENTRALIZADA (T +/- 4h) ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p style="color:#00d4ff; font-weight:bold;">🕒 CRONOGRAMA DE MISSÕES (ZULU)</p>', unsafe_allow_html=True)
    
    df_t = df[df['inicio_zulu'].notna() & df['fim_zulu'].notna()].copy()
    if not df_t.empty:
        fig = px.timeline(
            df_t, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave", 
            text="missao", color="aeronave", template="plotly_dark"
        )
        # Janela de visualização centralizada
        fig.update_layout(
            height=300, 
            margin=dict(l=0, r=0, t=10, b=0), 
            showlegend=False,
            xaxis_range=[now_z - timedelta(hours=4), now_z + timedelta(hours=4)]
        )
        fig.add_vline(x=now_z, line_width=3, line_color="red", line_dash="dash")
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- BLOCO 3: BUSCA E LOG ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    busca = st.text_input("🔍 FILTRAR BANCO DE DADOS:", placeholder="Aeronave, Missão ou Unidade...")
    if busca:
        df_f = df[df.apply(lambda row: busca.lower() in row.astype(str).str.lower().values, axis=1)]
    else:
        df_f = df
        
    st.dataframe(
        df_f.drop(columns=['lat_clean', 'lon_clean'], errors='ignore'), 
        use_container_width=True, 
        hide_index=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
