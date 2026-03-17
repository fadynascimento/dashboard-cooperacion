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
        df_raw['COLUNA_A'] = df_raw.iloc[:, 0]
        # Mapeamento de colunas H (índice 7) e I (índice 8)
        df_raw['ALERTA_H'] = df_raw.iloc[:, 7].astype(str).str.lower()
        df_raw['STATUS_I'] = df_raw.iloc[:, 8].astype(str)
        
        df_raw['lat_clean'] = df_raw['lat'].apply(parse_coordinate)
        df_raw['lon_clean'] = df_raw['lon'].apply(parse_coordinate)
        df_raw['inicio_zulu'] = pd.to_datetime(df_raw['inicio_zulu'], errors='coerce').dt.tz_localize('UTC')
        df_raw['fim_zulu'] = pd.to_datetime(df_raw['fim_zulu'], errors='coerce').dt.tz_localize('UTC')
        return df_raw
    except: return None

df = load_data(URL_PLANILHA)
now_z = datetime.now(timezone.utc)
now_p = datetime.now(timezone(timedelta(hours=-4)))

# --- ESTILO CSS COM ANIMAÇÃO DE ALERTA ---
st.markdown(f"""
    <style>
    @keyframes blinking {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} 100% {{ opacity: 1; }} }}
    .stAppDeployButton {{ display: none !important; }}
    header {{ visibility: hidden; height: 0; }}
    .stApp {{ background-color: #000b1e; color: white; }}
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
    .alert-bar {{
        width: 100%; padding: 5px; border-radius: 5px; text-align: center;
        font-weight: bold; font-size: 0.9rem; margin-bottom: 10px;
    }}
    .alert-red {{ background: rgba(255, 0, 0, 0.2); border: 1px solid red; color: #ff9999; animation: blinking 2s infinite; }}
    .alert-green {{ background: rgba(0, 255, 127, 0.1); border: 1px solid #00ff7f; color: #00ff7f; }}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
logo_b64 = get_base64(ARQUIVO_BOLACHA)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" height="60">' if logo_b64 else ""
st.markdown(f'<div class="fixed-header"><div class="time-container"><div class="zulu-time">{now_z.strftime("%H:%M")}Z</div><div style="font-size: 0.8rem; color: #ffcc00; font-weight: bold;">LOCAL: {now_p.strftime("%H:%M")}P</div></div><div class="mission-title">COOPERACIÓN XI</div><div class="logo-container">{logo_html}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    # Lógica de Alerta (Coluna H e I)
    has_active_fire = any((df['ALERTA_H'] == 'sim') & (df['STATUS_I'] == 'Ativo'))
    has_extinguished = any(df['STATUS_I'] == 'Extinto')
    
    col1, col2 = st.columns([2.5, 1])
    
    with col1:
        # Barra de Alerta Dinâmica
        if has_active_fire:
            st.markdown('<div class="alert-bar alert-red">⚠️ ALERTA: FOCOS DE INCÊNDIO ATIVOS DETECTADOS</div>', unsafe_allow_html=True)
        elif has_extinguished:
            st.markdown('<div class="alert-bar alert-green">✅ STATUS: FOCOS EXTINTOS / SOB CONTROLE</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card" style="height:500px;">', unsafe_allow_html=True)
        f1, f2, f3 = st.columns(3)
        show_foc = f2.toggle("🔥 Focos Incêndio", value=True)
        show_aero = f3.toggle("✈️ Meios Aéreos", value=True)
        
        m = folium.Map(location=[-18.5, -56.5], zoom_start=6, tiles='cartodbpositron', zoom_control=True)
        
        # Plotagem no Mapa
        for _, row in df.iterrows():
            if row['lat_clean'] and row['lon_clean']:
                # Se for Meio Aéreo
                if row['LAYER'] == 'Meios Aéreos' and show_aero:
                    folium.Marker(
                        [row['lat_clean'], row['lon_clean']],
                        popup=f"Aeronave: {row['aeronave']}<br>Missão: {row['missao']}",
                        icon=folium.Icon(color='blue', icon='plane', prefix='fa')
                    ).add_to(m)
                
                # Se for Foco de Incêndio (Baseado na coluna LAYER ou categoria)
                elif 'Focos' in str(row['LAYER']) and show_foc:
                    cor_foco = 'red' if row['STATUS_I'] == 'Ativo' else 'gray'
                    folium.Marker(
                        [row['lat_clean'], row['lon_clean']],
                        popup=f"Foco: {row['STATUS_I']}",
                        icon=folium.Icon(color=cor_foco, icon='fire', prefix='fa')
                    ).add_to(m)
        
        st_folium(m, width="100%", height=380, key="map_main")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-card" style="height:550px;">', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#00d4ff; font-weight:bold; font-size:1.2rem;">📊 VECTORES</p>', unsafe_allow_html=True)
        df_aero_op = df[df['LAYER']=='Meios Aéreos']
        st.metric("EN OPERACIÓN", len(df_aero_op))
        st.dataframe(df_aero_op[['aeronave', 'missao']].rename(columns={'missao': 'misión'}), hide_index=True, use_container_width=True, height=350)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- LÍNEA DEL TIEMPO ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p style="color:#00d4ff; font-weight:bold; font-size:1.1rem; margin-bottom:10px;">⏳ LÍNEA DEL TIEMPO</p>', unsafe_allow_html=True)
    
    filtro = df['LAYER'].str.upper().isin(['MEIOS AÉREOS', 'REUNIÃO', 'REUNIÓN', 'REUNIAO'])
    df_timeline = df[filtro & df['inicio_zulu'].notna() & df['fim_zulu'].notna()].copy()

    if not df_timeline.empty:
        fig = px.timeline(df_timeline, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave", 
                          color="aeronave", text="COLUNA_A", template="plotly_dark", height=400)
        fig.add_vline(x=now_z, line_width=3, line_color="#ff4b4b")
        fig.update_traces(textposition='inside', insidetextanchor='middle')
        fig.update_layout(showlegend=False, xaxis=dict(side="top", range=[now_z - timedelta(hours=6), now_z + timedelta(hours=6)],
                          rangeslider=dict(visible=True, thickness=0.02)))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
