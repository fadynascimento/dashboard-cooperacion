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
    if decimal_coord is None: return ""
    abs_val = abs(decimal_coord)
    degrees = int(abs_val)
    minutes = int((abs_val - degrees) * 60)
    seconds = int((abs_val - degrees - minutes/60) * 3600)
    if is_lat:
        designator = "S" if decimal_coord < 0 else "N"
    else:
        designator = "W" if decimal_coord < 0 else "E"
    return f"{degrees:02d}°{minutes:02d}'{seconds:02d}\"{designator}"

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
        
        # Limpeza básica de strings
        for col in ['status_foco', 'LAYER', 'aeronave', 'missao']:
            df_raw[col] = df_raw[col].astype(str).replace('nan', '')
        
        # Conversão de datas
        df_raw['inicio_zulu'] = pd.to_datetime(df_raw['inicio_zulu'], errors='coerce').dt.tz_localize('UTC')
        df_raw['fim_zulu'] = pd.to_datetime(df_raw['fim_zulu'], errors='coerce').dt.tz_localize('UTC')
        
        df_raw['lat_clean'] = df_raw['lat'].apply(parse_coordinate)
        df_raw['lon_clean'] = df_raw['lon'].apply(parse_coordinate)
        return df_raw
    except Exception as e:
        st.error(f"Error al procesar la planilla: {e}")
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

# --- ESTILO CSS ---
borda_cor = "rgba(0, 255, 127, 0.4)" if not focos_ativos else "rgba(255, 0, 0, 0.7)"
animacao = "none" if not focos_ativos else "pulse 1.5s infinite"

st.markdown(f"""
    <style>
    .block-container {{ padding-top: 0rem; padding-bottom: 0rem; padding-left: 1rem; padding-right: 1rem; }}
    [data-testid="stVerticalBlock"] > div {{ padding-top: 0.1rem; padding-bottom: 0.1rem; }}
    html, body, [data-testid="stTickBarMin"] {{ color: white !important; }}
    p, span, label, div, h1, h2, h3, h4, h5, h6 {{ color: white !important; }}
    .stMetric label {{ color: #00d4ff !important; }}
    .stMetric [data-testid="stMetricValue"] {{ color: white !important; }}
    @keyframes pulse {{
        0% {{ box-shadow: 0 0 5px rgba(255, 0, 0, 0.4); border-color: rgba(255, 0, 0, 0.4); }}
        50% {{ box-shadow: 0 0 20px rgba(255, 0, 0, 0.9); border-color: rgba(255, 0, 0, 0.9); }}
        100% {{ box-shadow: 0 0 5px rgba(255, 0, 0, 0.4); border-color: rgba(255, 0, 0, 0.4); }}
    }}
    .stAppDeployButton {{ display: none !important; }}
    #MainMenu {{ visibility: hidden; }}
    header {{ visibility: hidden; height: 0; }}
    footer {{ visibility: hidden; }}
    [data-testid="stHeader"], [data-testid="stDecoration"], [data-testid="stToolbar"] {{ display: none !important; }}
    .stApp {{ background-color: #001233; }}
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 60px;
        background: rgba(0, 18, 51, 0.95); z-index: 999;
        display: flex; align-items: center; justify-content: space-between;
        border-bottom: 1px solid rgba(0, 212, 255, 0.3); backdrop-filter: blur(5px);
        padding: 0 15px;
    }}
    .title-text {{
        font-family: 'Arial Black', sans-serif; color: white; letter-spacing: 3px; 
        font-size: 1.2rem; font-weight: 900; text-transform: uppercase; text-shadow: 0 0 10px #00d4ff;
    }}
    .time-block {{ text-align: left; border-left: 2px solid #00d4ff; padding-left: 8px; }}
    .time-label {{ color:#00d4ff; font-size:0.6rem; font-weight:bold; margin:0; }}
    .time-value {{ font-size:1.1rem; color:white; font-family:monospace; font-weight:bold; margin:0; line-height:1;}}
    .time-local {{ color:#ffcc00; font-size:0.65rem; font-weight:bold; margin:0; }}
    .main-content {{ margin-top: 65px; }}
    .section-title {{ color:#00ff7f; font-size: 1rem; margin-bottom: 2px; margin-top: 0px; }}
    .map-outer-frame {{
        padding: 2px; background: rgba(0, 0, 0, 0.2); border-radius: 10px;
        box-shadow: 0 0 10px {borda_cor}; border: 1px solid {borda_cor};
        animation: {animacao}; margin-bottom: 5px;
    }}
    .status-panel {{
        background: rgba(0, 30, 70, 0.3); border-radius: 10px; padding: 5px;
        box-shadow: -5px 0 10px rgba(0, 0, 0, 0.5); border: 1px solid rgba(0, 212, 255, 0.1);
        margin-bottom: 5px;
    }}
    .status-title {{ color:#00d4ff; text-align:center; font-size: 0.9rem; margin-bottom: 2px; }}
    .timeline-card {{
        background: rgba(0, 30, 70, 0.4); border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 8px; padding: 5px; box-shadow: 0 0 15px rgba(0, 212, 255, 0.15); 
        margin-top: 0px; margin-bottom: 5px;
    }}
    .timeline-title {{ text-align:center; color:#00d4ff; font-weight:bold; font-size: 0.8rem; margin-bottom: 2px; }}
    .fixed-logo {{ position: fixed; top: 5px; right: 10px; z-index: 1001; }}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f"""
    <div class="fixed-header">
        <div class="time-block">
            <p class="time-label">HORA ZULU (UTC)</p>
            <p class="time-value">{now_z.strftime('%H:%M:%S')} Z</p>
            <p class="time-local">Local (P): {now_p.strftime('%H:%M')} P</p>
        </div>
        <div class="title-text">COOPERACIÓN XI</div>
        <div style="width: 100px;"></div>
    </div>
    """, unsafe_allow_html=True)

logo_b64 = get_base64(ARQUIVO_BOLACHA)
if logo_b64:
    st.markdown(f'<div class="fixed-logo"><img src="data:image/png;base64,{logo_b64}" width="70"></div>', unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    c1, c2 = st.columns([2.5, 1])
    
    with c1:
        st.markdown('<p class="section-title">📍 CONCIENCIA SITUACIONAL</p>', unsafe_allow_html=True)
        st.markdown('<div class="map-outer-frame">', unsafe_allow_html=True)
        
        lt1, lt2, lt3 = st.columns(3)
        show_met = lt1.toggle("☁️ Meteorología", value=True, key="t1")
        show_foc = lt2.toggle("🔥 Focos Incd", value=True, key="t2")
        show_aero = lt3.toggle("✈️ Medios aéreos", value=True, key="t3")
        
        active_layers = []
        if show_met: active_layers.append("Meteorologia")
        if show_foc: active_layers.append("Focos Incd")
        if show_aero: active_layers.append("Meios Aéreos")
        
        # O MAPA FILTRA PELAS CAMADAS
        df_mapa = df[df['LAYER'].isin(active_layers)]
        
        m = folium.Map(location=[-18.5, -56.5], zoom_start=6, tiles='cartodbpositron', zoom_control=False, attribution_control=False)
        
        for _, row in df_mapa.iterrows():
            if row['lat_clean'] is not None and row['lon_clean'] is not None:
                icon_map = {
                    'Meteorologia': ('cloud', 'lightgray'), 
                    'Focos Incd': ('fire', 'green' if "extinto" in str(row['status_foco']).lower() else 'red'), 
                    'Meios Aéreos': ('plane', 'cadetblue')
                }
                icon_type, icon_color = icon_map.get(row['LAYER'], ('info-sign', 'blue'))
                
                lat_mil = format_to_military(row['lat_clean'], is_lat=True)
                lon_mil = format_to_military(row['lon_clean'], is_lat=False)
                
                popup_text = f"""
                <div style='font-family: Arial; font-size: 11px; width: 200px; background:#f4f4f4; padding:8px; border-radius:5px; border-left:3px solid {icon_color}; line-height:1.2; color: black !important;'>
                    <b style='color:#003366 !important;'>{row['aeronave']}</b><br>
                    <span style='color: black !important;'>{row['missao']}</span><br>
                    <hr style='margin:3px 0; border:0; border-top:1px solid #ccc;'>
                    <span style='color:#222 !important; font-size:10px; font-weight:bold; font-family:monospace;'>{lat_mil} / {lon_mil}</span>
                </div>
                """
                folium.Marker([row['lat_clean'], row['lon_clean']], popup=folium.Popup(popup_text, max_width=250), icon=folium.Icon(color=icon_color, icon=icon_type, prefix='fa')).add_to(m)
        
        st_folium(m, width="100%", height=350, key="map_coi_vFinal")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="status-panel">', unsafe_allow_html=True)
        st.markdown('<p class="status-title">📊 ESTADO OPERATIVO</p>', unsafe_allow_html=True)
        # Status Operativo foca nos meios aéreos
        df_ma_status = df[df['LAYER'] == "Meios Aéreos"]
        sm1, sm2 = st.columns(2)
        sm1.metric("VECTORES", df_ma_status['aeronave'].nunique() if not df_ma_status.empty else 0)
        sm2.metric("MISIONES", len(df_ma_status) if not df_ma_status.empty else 0)
        
        if not df_ma_status.empty:
            df_resumo = df_ma_status.groupby(['aeronave', 'missao']).size().reset_index(name='CANT')
            df_resumo.columns = ['VECTOR', 'TIPO DE MISIÓN', 'CANT']
            st.dataframe(df_resumo, hide_index=True, use_container_width=True, height=150)
        st.markdown('</div>', unsafe_allow_html=True)

        if focos_ativos:
            st.error("🚨 FOCOS DE INCENDIO ACTIVOS", icon="🚨")

    # --- LÍNEA DE TIEMPO (Puxa tudo que tem horário) ---
    st.markdown('<div class="timeline-card">', unsafe_allow_html=True)
    st.markdown('<p class="timeline-title">LÍNEA DE TIEMPO (Z)</p>', unsafe_allow_html=True)
    
    # Filtra apenas itens que possuem data/hora de início e fim preenchidos (reuniões e voos)
    df_timeline = df[df['inicio_zulu'].notna() & df['fim_zulu'].notna()]
    
    if not df_timeline.empty:
        fig = px.timeline(df_timeline, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave", color="aeronave", text="missao", template="plotly_dark")
        fig.add_vline(x=now_z, line_width=2, line_color="#ff4b4b")
        fig.update_layout(
            xaxis_range=[now_z - timedelta(hours=4), now_z + timedelta(hours=8)], # Janela um pouco maior para planejamento
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,212,255,0.02)',
            font_color="white", showlegend=False, height=220, margin=dict(l=5, r=5, t=5, b=5),
            xaxis=dict(tickfont=dict(size=10), title=None),
            yaxis=dict(tickfont=dict(size=10), title=None)
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

    # --- MANIFIESTO ---
    st.markdown("<br><p class='section-title' style='color:#00d4ff;'>📝 MANIFIESTO DE LA MISIÓN</p>", unsafe_allow_html=True)
    if df is not None:
        df_display = df[['aeronave', 'missao', 'LAYER', 'status_foco', 'horario_solucao', 'inicio_zulu', 'fim_zulu']].copy()
        df_display.columns = ['VECTOR', 'MISIÓN', 'CAPA', 'ESTADO', 'HORA SOLUCIÓN', 'INICIO (Z)', 'FIN (Z)']
        st.dataframe(df_display, use_container_width=True, hide_index=True, height=200)

else:
    st.warning("🔄 Sincronizando...")

st.markdown('</div>', unsafe_allow_html=True)
