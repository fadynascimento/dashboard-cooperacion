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

# --- AUTO-REFRESH (15 segundos) ---
st_autorefresh(interval=15000, limit=None, key="refresh_dashboard")

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
        elif 'N' in c or 'E' in c: val = abs(val)
        elif '-' in c and val > 0: val = -val
        return val
    except: return None

def format_to_military(decimal_coord, is_lat=True):
    if decimal_coord is None or pd.isna(decimal_coord): 
        return "N/A"
    try:
        abs_val = abs(decimal_coord)
        degrees = int(abs_val)
        minutes = int((abs_val - degrees) * 60)
        seconds = int((abs_val - degrees - minutes/60) * 3600)
        if is_lat:
            designator = "S" if decimal_coord < 0 else "N"
        else:
            designator = "W" if decimal_coord < 0 else "E"
        return f"{degrees:02d}°{minutes:02d}'{seconds:02d}\"{designator}"
    except:
        return "N/A"

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
        required_cols = ['LAYER', 'inicio_zulu', 'fim_zulu', 'lat', 'lon', 'aeronave', 'missao', 'status_foco', 'horario_solucao']
        for col in required_cols:
            if col not in df_raw.columns:
                df_raw[col] = ""
        for col in ['status_foco', 'LAYER', 'aeronave', 'missao']:
            df_raw[col] = df_raw[col].astype(str).replace('nan', '')
        df_raw['inicio_zulu'] = pd.to_datetime(df_raw['inicio_zulu'], errors='coerce').dt.tz_localize('UTC')
        df_raw['fim_zulu'] = pd.to_datetime(df_raw['fim_zulu'], errors='coerce').dt.tz_localize('UTC')
        df_raw['lat_clean'] = df_raw['lat'].apply(parse_coordinate)
        df_raw['lon_clean'] = df_raw['lon'].apply(parse_coordinate)
        return df_raw
    except Exception as e:
        st.error(f"Error al procesar la planilha: {e}")
        return None

df = load_data(URL_PLANILHA)

# --- LÓGICA DE TIEMPO ---
now_z = datetime.now(timezone.utc)
now_p = datetime.now(timezone(timedelta(hours=-4)))

# --- LÓGICA DE ALERTA ---
focos_ativos = False
if df is not None:
    focos_ativos = not df[
        (df['LAYER'].str.contains("Focos Incd", case=False, na=False)) & 
        (~df['status_foco'].str.contains("Extinto|Controlado", case=False, na=False))
    ].empty

# --- ESTILO CSS REESTRUTURADO E REFINADO ---
borda_cor = "rgba(0, 255, 127, 0.4)" if not focos_ativos else "rgba(255, 0, 0, 0.7)"
animacao = "none" if not focos_ativos else "pulse 1.5s infinite"

st.markdown(f"""
    <style>
    /* Ocultar elementos nativos */
    .stAppDeployButton {{ display: none !important; }}
    #MainMenu {{ visibility: hidden; }}
    header {{ visibility: hidden; height: 0; }}
    footer {{ visibility: hidden; }}
    [data-testid="stHeader"], [data-testid="stDecoration"], [data-testid="stToolbar"] {{ display: none !important; }}
    
    .block-container {{ padding-top: 0rem; padding-bottom: 0rem; padding-left: 1rem; padding-right: 1rem; }}
    .stApp {{ background-color: #001233; }}
    
    /* CABEÇALHO REFINADO COM EFEITO DE VIDRO */
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 120px;
        background: rgba(0, 18, 51, 0.9); z-index: 999;
        border-bottom: 2px solid rgba(0, 212, 255, 0.5);
        backdrop-filter: blur(5px); /* Efeito Frosted Glass */
        padding: 0 30px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}

    /* RELÓGIO ZULU - À ESQUERDA, NÍTIDO E REFINADO */
    .time-block {{
        display: flex;
        align-items: center;
        margin-right: auto;
    }}
    .time-value {{ 
        font-size: 5rem; 
        color: white; 
        font-family: 'Courier New', monospace; 
        font-weight: 900; 
        line-height: 1;
        letter-spacing: -5px;
        margin-right: 20px;
        text-shadow: 0 2px 5px rgba(0,0,0,0.5); /* Sombra para leitura nítida */
    }}
    .local-box {{
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}
    .time-local {{ color: #ffcc00; font-size: 1.5rem; font-weight: bold; margin: 0; text-shadow: 0 1px 2px rgba(0,0,0,0.3); }}
    
    /* TÍTULO - CENTRALIZADO, LIGEIRAMENTE MAIOR QUE O RELÓGIO E IMPOENTE */
    .title-text {{
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
        font-family: 'Arial Black', sans-serif; color: white;
        font-size: 2.8rem; /* Imponente e ligeiramente maior */
        font-weight: 900; text-transform: uppercase;
        text-shadow: 0 0 15px #00d4ff; /* Brilho neon suave */
        white-space: nowrap;
    }}

    /* LOGO - À DIREITA, SEMI-TRANSPARENTE E SUAVE */
    .fixed-logo {{ 
        margin-left: auto;
        display: flex;
        align-items: center;
    }}
    .fixed-logo img {{
        opacity: 0.9; /* Suaviza a logo */
    }}

    .main-content {{ margin-top: 130px; }}
    
    .map-outer-frame {{
        padding: 2px; background: rgba(0, 0, 0, 0.2); border-radius: 10px;
        box-shadow: 0 0 10px {borda_cor}; border: 1px solid {borda_cor};
        animation: {animacao};
    }}
    .status-panel {{
        background: rgba(0, 30, 70, 0.3); border-radius: 10px; padding: 10px;
        border: 1px solid rgba(0, 212, 255, 0.1);
    }}
    .timeline-card {{
        background: rgba(0, 30, 70, 0.4); border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 8px; padding: 5px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER REESTRUTURADO E REFINADO ---
logo_b64 = get_base64(ARQUIVO_BOLACHA)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" width="140">' if logo_b64 else ""

st.markdown(f"""
    <div class="fixed-header">
        <div class="time-block">
            <div class="time-value">{now_z.strftime('%H:%M:%S')}Z</div>
            <div class="local-box">
                <div class="time-local">LOCAL: {now_p.strftime('%H:%M')}P</div>
            </div>
        </div>
        <div class="title-text">COOPERACIÓN XI</div>
        <div class="fixed-logo">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    c1, c2 = st.columns([2.2, 1])
    
    with c1:
        st.markdown('<p style="color:#00ff7f; font-size: 1.1rem; margin:0; font-weight:bold; text-shadow: 0 1px 3px rgba(0,0,0,0.5);">📍 CONCIENCIA SITUACIONAL</p>', unsafe_allow_html=True)
        st.markdown('<div class="map-outer-frame">', unsafe_allow_html=True)
        
        lt1, lt2, lt3 = st.columns(3)
        show_met = lt1.toggle("☁️ Met", value=True, key="t1")
        show_foc = lt2.toggle("🔥 Focos", value=True, key="t2")
        show_aero = lt3.toggle("✈️ Aéreos", value=True, key="t3")
        
        active_layers = []
        if show_met: active_layers.append("Meteorologia")
        if show_foc: active_layers.append("Focos Incd")
        if show_aero: active_layers.append("Meios Aéreos")
        
        df_mapa = df[df['LAYER'].isin(active_layers)]
        m = folium.Map(location=[-18.5, -56.5], zoom_start=6, tiles='cartodbpositron', zoom_control=False, attribution_control=False)
        
        for _, row in df_mapa.iterrows():
            if row['lat_clean'] is not None and row['lon_clean'] is not None:
                icon_map = {'Meteorologia': ('cloud', 'lightgray'), 'Focos Incd': ('fire', 'red'), 'Meios Aéreos': ('plane', 'cadetblue')}
                icon_type, icon_color = icon_map.get(row['LAYER'], ('info-sign', 'blue'))
                lat_mil = format_to_military(row['lat_clean'], is_lat=True)
                lon_mil = format_to_military(row['lon_clean'], is_lat=False)
                # Popup com cor forçada para leitura nítida
                popup_text = f"<div style='color:black !important; font-size:11px; font-family:Arial, sans-serif;'><b>{row['aeronave']}</b><br>{row['missao']}<br>{lat_mil}/{lon_mil}</div>"
                folium.Marker([row['lat_clean'], row['lon_clean']], popup=folium.Popup(popup_text, max_width=200), icon=folium.Icon(color=icon_color, icon=icon_type, prefix='fa')).add_to(m)
        
        st_folium(m, width="100%", height=280, key="map_coi")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="status-panel">', unsafe_allow_html=True)
        st.markdown('<p style="color:#00d4ff; text-align:center; font-size:1rem; margin:0; font-weight:bold; text-shadow: 0 1px 2px rgba(0,0,0,0.3);">📊 ESTADO OPERATIVO</p>', unsafe_allow_html=True)
        df_ma_status = df[df['LAYER'] == "Meios Aéreos"]
        sm1, sm2 = st.columns(2)
        sm1.metric("VECTORES", df_ma_status['aeronave'].nunique() if not df_ma_status.empty else 0)
        sm2.metric("MISIONES", len(df_ma_status) if not df_ma_status.empty else 0)
        st.markdown('</div>', unsafe_allow_html=True)
        if focos_ativos: st.error("🚨 FOCOS ACTIVOS")

    # --- LÍNEA DE TIEMPO ---
    st.markdown('<div class="timeline-card" style="margin-top:10px;">', unsafe_allow_html=True)
    df_timeline = df[df['inicio_zulu'].notna() & df['fim_zulu'].notna()].copy()
    if not df_timeline.empty:
        fig = px.timeline(df_timeline, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave", color="aeronave", text="aeronave", template="plotly_dark")
        fig.add_vline(x=now_z, line_width=2, line_color="#ff4b4b")
        fig.update_traces(textposition='inside', insidetextanchor='middle', textfont=dict(color='white', size=14))
        fig.update_layout(
            xaxis_range=[now_z - timedelta(hours=3), now_z + timedelta(hours=7)],
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,212,255,0.02)',
            showlegend=False, height=280, margin=dict(l=5, r=5, t=5, b=5),
            xaxis=dict(title=None), yaxis=dict(title=None)
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.warning("🔄 Sincronizando...")

st.markdown('</div>', unsafe_allow_html=True)
