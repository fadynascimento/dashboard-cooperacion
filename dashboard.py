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

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(layout="wide", page_title="COOPERACIÓN XI", page_icon="✈️")

# --- AUTO-REFRESH NATIVO (15 segundos) ---
st_autorefresh(interval=15000, limit=None, key="map_refresher")

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
        elif 'N' in c or 'E' in c: val = abs(val)
        elif '-' in c and val > 0: val = -val
        return val
    except: return None

def get_base64(bin_file):
    if os.path.exists(bin_file):
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    return None

# --- ARQUIVOS E DADOS ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSxvtVEGGjxGS316VCXhFUDv7AA9WaPSNql8ncUFu6Kn0d39BPr7XMS6WSSn8JJ6VAVDUAJ9AshQ1bi/pub?output=csv"
ARQUIVO_BOLACHA = "bolcaha cooperacion.png"

# --- ESTILIZAÇÃO CSS (FOCO NO BRILHO VERDE DO MAPA) ---
st.markdown(f"""
    <style>
    .stAppDeployButton {{ display: none !important; }}
    #MainMenu {{ visibility: hidden; }}
    header {{ visibility: hidden; height: 0; }}
    footer {{ visibility: hidden; }}
    [data-testid="stHeader"], [data-testid="stDecoration"], [data-testid="stToolbar"] {{ display: none !important; }}

    .stApp {{ background-color: #001233; background-attachment: fixed; }}
    
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 95px;
        background: rgba(0, 18, 51, 0.85); z-index: 999;
        display: flex; align-items: center; justify-content: center;
        border-bottom: 2px solid rgba(0, 212, 255, 0.5); backdrop-filter: blur(5px);
    }}

    .title-text {{
        font-family: 'Arial Black', sans-serif; color: white; letter-spacing: 10px; 
        font-size: 2.2rem; font-weight: 900; text-transform: uppercase; text-shadow: 0 0 15px #00d4ff;
    }}

    /* MOLDURA DO MAPA COM BRILHO VERDE E PROFUNDIDADE */
    .map-container {{
        border-radius: 15px;
        padding: 5px;
        background: rgba(0, 255, 127, 0.05);
        box-shadow: 0 0 25px rgba(0, 255, 127, 0.3), 10px 15px 30px rgba(0, 0, 0, 0.6);
        border: 1px solid rgba(0, 255, 127, 0.2);
        margin-bottom: 20px;
    }}

    .status-panel {{
        background: rgba(0, 30, 70, 0.3); border-radius: 15px; padding: 15px;
        box-shadow: -10px 0 20px rgba(0, 0, 0, 0.5), inset 0 0 15px rgba(0, 212, 255, 0.05);
        border: 1px solid rgba(0, 212, 255, 0.1);
    }}

    .timeline-card {{
        background: rgba(0, 30, 70, 0.4); border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 12px; padding: 20px; box-shadow: 0 0 30px rgba(0, 212, 255, 0.15); margin-top: 20px;
    }}

    .fixed-logo {{ position: fixed; top: 5px; right: 25px; z-index: 1001; }}
    .main-content {{ margin-top: 110px; }}
    </style>
    """, unsafe_allow_html=True)

# --- TEMPO (GMT-4 - CAMPO GRANDE) ---
now_z = datetime.now(timezone.utc)
now_p = datetime.now(timezone(timedelta(hours=-4)))

# --- HEADER ---
st.markdown(f"""
    <div class="fixed-header">
        <div style="position: absolute; left: 20px; text-align: left; border-left: 3px solid #00d4ff; padding-left: 15px;">
            <div style="color:#00d4ff; font-size:0.7rem; font-weight:bold;">HORÁRIO ZULU (UTC)</div>
            <div style="font-size:1.6rem; color:white; font-family:monospace; font-weight:bold;">{now_z.strftime('%H:%M:%S')} Z</div>
            <div style="color:#ffcc00; font-size:0.8rem; font-weight:bold;">Local (P): {now_p.strftime('%H:%M')} P</div>
        </div>
        <div class="title-text">COOPERACIÓN XI</div>
    </div>
    """, unsafe_allow_html=True)

logo_b64 = get_base64(ARQUIVO_BOLACHA)
if logo_b64:
    st.markdown(f'<div class="fixed-logo"><img src="data:image/png;base64,{logo_b64}" width="180"></div>', unsafe_allow_html=True)

# --- CARGA DE DADOS ---
@st.cache_data(ttl=5)
def load_and_clean_data(url):
    try:
        df_raw = pd.read_csv(f"{url}&ts={int(time.time())}")
        df_raw['inicio_zulu'] = pd.to_datetime(df_raw['inicio_zulu']).dt.tz_localize('UTC')
        df_raw['fim_zulu'] = pd.to_datetime(df_raw['fim_zulu']).dt.tz_localize('UTC')
        df_raw['lat_clean'] = df_raw['lat'].apply(parse_coordinate)
        df_raw['lon_clean'] = df_raw['lon'].apply(parse_coordinate)
        return df_raw
    except: return None

df = load_and_clean_data(URL_PLANILHA)

# --- DASHBOARD ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    c1, c2 = st.columns([2.3, 1])
    with c1:
        st.markdown("<h4 style='color:#00ff7f; text-shadow: 0 0 10px rgba(0,255,127,0.5);'>📍 CONSCIÊNCIA SITUACIONAL</h4>", unsafe_allow_html=True)
        # Aplicando a moldura com brilho verde
        st.markdown('<div class="map-container">', unsafe_allow_html=True)
        m = folium.Map(location=[-18.5, -56.5], zoom_start=6, tiles='cartodbpositron', zoom_control=False, attribution_control=False)
        for _, row in df.iterrows():
            if row['lat_clean'] is not None and row['lon_clean'] is not None:
                color = 'red' if 'Foco' in str(row['foco']) else 'blue'
                folium.Marker([row['lat_clean'], row['lon_clean']], 
                              popup=f"<b>{row['aeronave']}</b>", icon=folium.Icon(color=color, icon='plane', prefix='fa')).add_to(m)
        st_folium(m, width="100%", height=380, key="map_v8")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="status-panel">', unsafe_allow_html=True)
        st.markdown("<h4 style='color:#00d4ff; text-align:center;'>📊 STATUS OPERACIONAL</h4>", unsafe_allow_html=True)
        sm1, sm2 = st.columns(2)
        sm1.metric("VETORES", df['aeronave'].nunique())
        sm2.metric("MISSÕES", len(df))
        df_status = df.groupby('aeronave').agg({'missao': 'last', 'aeronave': 'size'}).rename(columns={'missao': 'TIPO DE MISSÃO', 'aeronave': 'QTD'}).reset_index()
        st.dataframe(df_status[['aeronave', 'TIPO DE MISSÃO', 'QTD']], hide_index=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TIMELINE ---
    st.markdown('<div class="timeline-card">', unsafe_allow_html=True)
    st.markdown(f"""<div style="text-align:center; margin-bottom:10px; background:linear-gradient(90deg, transparent, rgba(0,212,255,0.1), transparent); padding:10px; border-radius:20px;">
                    <span style="color:#00d4ff; font-size:0.8rem; letter-spacing:2px;">REFERÊNCIA TEMPORAL (Z)</span><br>
                    <span style="font-size:2rem; color:white; font-family:monospace; font-weight:bold;">{now_z.strftime('%H:%M:%S')}Z</span></div>""", unsafe_allow_html=True)
    
    fig = px.timeline(df, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave", color="aeronave", text="missao", template="plotly_dark")
    fig.add_vline(x=now_z, line_width=3, line_color="#ff4b4b")
    fig.update_layout(xaxis_range=[now_z - timedelta(hours=4), now_z + timedelta(hours=4)], 
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,212,255,0.02)', 
                      font_color="white", showlegend=False, height=320, margin=dict(l=10, r=10, t=0, b=10),
                      modebar_add=['zoomIn2d', 'zoomOut2d', 'pan2d', 'autoScale2d'])
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br><h4 style='color:#00d4ff;'>📝 MANIFESTO</h4>", unsafe_allow_html=True)
    st.dataframe(df[['aeronave', 'missao', 'foco', 'inicio_zulu', 'fim_zulu']], use_container_width=True, hide_index=True)

else: st.error("⚠️ Falha na sincronização.")

st.markdown('</div>', unsafe_allow_html=True)
