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
st.set_page_config(layout="wide", page_title="COOPERACIÓN XI - COI", page_icon="✈️")

# --- AUTO-REFRESH NATIVO (15 segundos) ---
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
        elif 'N' in c or 'E' in c: val = abs(val)
        elif '-' in c and val > 0: val = -val
        return val
    except: return None

def get_base64(bin_file):
    if os.path.exists(bin_file):
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    return None

# --- CARREGAMENTO DE DADOS ---
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
        
        df_raw['status_foco'] = df_raw['status_foco'].astype(str).replace('nan', '')
        df_raw['LAYER'] = df_raw['LAYER'].astype(str).replace('nan', '')
        
        df_raw['inicio_zulu'] = pd.to_datetime(df_raw['inicio_zulu'], errors='coerce').dt.tz_localize('UTC')
        df_raw['fim_zulu'] = pd.to_datetime(df_raw['fim_zulu'], errors='coerce').dt.tz_localize('UTC')
        df_raw['lat_clean'] = df_raw['lat'].apply(parse_coordinate)
        df_raw['lon_clean'] = df_raw['lon'].apply(parse_coordinate)
        return df_raw
    except Exception as e:
        st.error(f"Erro ao processar planilha: {e}")
        return None

df = load_data(URL_PLANILHA)

# --- LÓGICA DE TEMPO ---
now_z = datetime.now(timezone.utc)
now_p = datetime.now(timezone(timedelta(hours=-4)))
segundos_restantes = 15 - (int(time.time()) % 15)

# --- LÓGICA DE ALERTA ---
focos_ativos = False
if df is not None:
    focos_ativos = not df[
        (df['LAYER'].str.contains("Focos Incd", case=False, na=False)) & 
        (~df['status_foco'].str.contains("Extinto|Controlado", case=False, na=False))
    ].empty

# --- ESTILIZAÇÃO CSS ---
borda_cor = "rgba(0, 255, 127, 0.4)" if not focos_ativos else "rgba(255, 0, 0, 0.7)"
animacao = "none" if not focos_ativos else "pulse 1.5s infinite"

st.markdown(f"""
    <style>
    @keyframes pulse {{
        0% {{ box-shadow: 0 0 10px rgba(255, 0, 0, 0.4); border-color: rgba(255, 0, 0, 0.4); }}
        50% {{ box-shadow: 0 0 35px rgba(255, 0, 0, 0.9); border-color: rgba(255, 0, 0, 0.9); }}
        100% {{ box-shadow: 0 0 10px rgba(255, 0, 0, 0.4); border-color: rgba(255, 0, 0, 0.4); }}
    }}
    .stAppDeployButton {{ display: none !important; }}
    #MainMenu {{ visibility: hidden; }}
    header {{ visibility: hidden; height: 0; }}
    footer {{ visibility: hidden; }}
    [data-testid="stHeader"], [data-testid="stDecoration"], [data-testid="stToolbar"] {{ display: none !important; }}
    .stApp {{ background-color: #001233; }}
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 105px;
        background: rgba(0, 18, 51, 0.9); z-index: 999;
        display: flex; align-items: center; justify-content: center;
        border-bottom: 2px solid rgba(0, 212, 255, 0.5); backdrop-filter: blur(10px);
    }}
    .title-text {{
        font-family: 'Arial Black', sans-serif; color: white; letter-spacing: 10px; 
        font-size: 2.2rem; font-weight: 900; text-transform: uppercase; text-shadow: 0 0 15px #00d4ff;
    }}
    .refresh-bar {{
        color: #00ff7f; font-size: 0.65rem; font-family: monospace;
        margin-top: 5px; text-transform: uppercase; letter-spacing: 2px;
    }}
    .map-outer-frame {{
        padding: 10px; background: rgba(0, 0, 0, 0.2); border-radius: 20px;
        box-shadow: 0 0 20px {borda_cor}; border: 2px solid {borda_cor};
        animation: {animacao}; margin-bottom: 10px;
    }}
    .status-panel {{
        background: rgba(0, 30, 70, 0.3); border-radius: 15px; padding: 15px;
        box-shadow: -10px 0 20px rgba(0, 0, 0, 0.5); border: 1px solid rgba(0, 212, 255, 0.1);
    }}
    .timeline-card {{
        background: rgba(0, 30, 70, 0.4); border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 12px; padding: 20px; box-shadow: 0 0 30px rgba(0, 212, 255, 0.15); margin-top: 20px;
    }}
    .fixed-logo {{ position: fixed; top: 5px; right: 25px; z-index: 1001; }}
    .main-content {{ margin-top: 125px; }}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f"""
    <div class="fixed-header">
        <div style="position: absolute; left: 20px; text-align: left; border-left: 3px solid #00d4ff; padding-left: 15px;">
            <div style="color:#00d4ff; font-size:0.7rem; font-weight:bold;">HORÁRIO ZULU (UTC)</div>
            <div style="font-size:1.6rem; color:white; font-family:monospace; font-weight:bold;">{now_z.strftime('%H:%M:%S')} Z</div>
            <div style="color:#ffcc00; font-size:0.8rem; font-weight:bold;">Local (P): {now_p.strftime('%H:%M')} P</div>
            <div class="refresh-bar">Próxima Sincronização em {segundos_restantes}s</div>
        </div>
        <div class="title-text">COOPERACIÓN XI</div>
    </div>
    """, unsafe_allow_html=True)

logo_b64 = get_base64(ARQUIVO_BOLACHA)
if logo_b64:
    st.markdown(f'<div class="fixed-logo"><img src="data:image/png;base64,{logo_b64}" width="180"></div>', unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    c1, c2 = st.columns([2.3, 1])
    
    with c1:
        st.markdown("<h4 style='color:#00ff7f;'>📍 CONSCIÊNCIA SITUACIONAL</h4>", unsafe_allow_html=True)
        st.markdown('<div class="map-outer-frame">', unsafe_allow_html=True)
        
        lt1, lt2, lt3 = st.columns(3)
        with lt1: show_met = st.toggle("☁️ Meteorologia", value=True)
        with lt2: show_foc = st.toggle("🔥 Focos Incd", value=True)
        with lt3: show_aero = st.toggle("✈️ Meios Aéreos", value=True)
        
        active_layers = []
        if show_met: active_layers.append("Meteorologia")
        if show_foc: active_layers.append("Focos Incd")
        if show_aero: active_layers.append("Meios Aéreos")
        
        df_filtered = df[df['LAYER'].isin(active_layers)]
        
        m = folium.Map(location=[-18.5, -56.5], zoom_start=6, tiles='cartodbpositron', zoom_control=False, attribution_control=False)
        
        for _, row in df_filtered.iterrows():
            if row['lat_clean'] is not None and row['lon_clean'] is not None:
                is_met = "meteorologia" in str(row['LAYER']).lower()
                fogo_extinto = "extinto" in str(row['status_foco']).lower() or "controlado" in str(row['status_foco']).lower()
                
                icon_map = {
                    'Meteorologia': ('cloud', 'lightgray'), 
                    'Focos Incd': ('fire', 'green' if fogo_extinto else 'red'), 
                    'Meios Aéreos': ('plane', 'cadetblue')
                }
                icon_type, icon_color = icon_map.get(row['LAYER'], ('info-sign', 'blue'))
                
                # AJUSTE DO POPUP: SUPRESSÃO DE RÓTULOS PARA METAR
                if is_met:
                    popup_text = f"""
                    <div style='font-family: monospace; font-size: 13px; width: 240px; background:#f4f4f4; padding:10px; border-radius:5px; border-left:4px solid #00d4ff;'>
                        {row['missao']}
                    </div>
                    """
                else:
                    popup_text = f"""
                    <div style='font-family: Arial; font-size: 12px; width: 220px;'>
                        <b style='color:#003366;'>ID/VETOR:</b> {row['aeronave']}<br>
                        <b style='color:#003366;'>MISSÃO:</b> {row['missao']}
                        <hr style='margin:5px 0;'>
                        <b>STATUS:</b> {row['status_foco']}<br>
                        <b>SOLUÇÃO:</b> {row['horario_solucao']}
                    </div>
                    """
                
                folium.Marker(
                    [row['lat_clean'], row['lon_clean']], 
                    popup=folium.Popup(popup_text, max_width=280), 
                    icon=folium.Icon(color=icon_color, icon=icon_type, prefix='fa')
                ).add_to(m)
        
        st_folium(m, width="100%", height=420, key="map_coi_vFinal")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="status-panel">', unsafe_allow_html=True)
        st.markdown("<h4 style='color:#00d4ff; text-align:center;'>📊 STATUS OPERACIONAL</h4>", unsafe_allow_html=True)
        df_ma = df[df['LAYER'] == "Meios Aéreos"]
        sm1, sm2 = st.columns(2)
        sm1.metric("VETORES", df_ma['aeronave'].nunique() if not df_ma.empty else 0)
        sm2.metric("MISSÕES", len(df_ma) if not df_ma.empty else 0)
        
        if not df_ma.empty:
            df_resumo = df_ma.groupby(['aeronave', 'missao']).size().reset_index(name='QTD')
            df_resumo.columns = ['AERONAVE', 'TIPO DE MISSÃO', 'QTD']
            st.dataframe(df_resumo, hide_index=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if focos_ativos:
            st.error("🚨 FOCOS DE INCÊNDIO ATIVOS")

    # --- AÇÕES (Z) ---
    st.markdown('<div class="timeline-card">', unsafe_allow_html=True)
    st.markdown(f"""<div style="text-align:center; color:#00d4ff; font-weight:bold; margin-bottom:10px;">AÇÕES (Z)</div>""", unsafe_allow_html=True)
    
    if not df_ma.empty and not df_ma['inicio_zulu'].isna().all():
        fig = px.timeline(df_ma, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave", color="aeronave", text="missao", template="plotly_dark")
        fig.add_vline(x=now_z, line_width=3, line_color="#ff4b4b")
        fig.update_layout(xaxis_range=[now_z - timedelta(hours=4), now_z + timedelta(hours=4)], paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,212,255,0.02)', font_color="white", showlegend=False, height=300, margin=dict(l=10, r=10, t=0, b=10))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- MANIFESTO ---
    st.markdown("<br><h4 style='color:#00d4ff;'>📝 MANIFESTO DE MISSÕES</h4>", unsafe_allow_html=True)
    st.dataframe(df[['aeronave', 'missao', 'LAYER', 'status_foco', 'horario_solucao', 'inicio_zulu', 'fim_zulu']], use_container_width=True, hide_index=True)

else:
    st.warning("🔄 Sincronizando...")

st.markdown('</div>', unsafe_allow_html=True)
