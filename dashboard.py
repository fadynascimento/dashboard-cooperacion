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

# --- INICIALIZAÇÃO DO ESTADO DO MAPA (PERSISTÊNCIA) ---
if 'map_center' not in st.session_state:
    st.session_state.map_center = [-18.5, -56.5] # Coordenada inicial (MS)
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 6 # Zoom inicial

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
        # Colunas H (7) e I (8) para os alertas de queimada
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

# --- ESTILO CSS (INCLUINDO MAPA FLUTUANTE) ---
st.markdown(f"""
    <style>
    @keyframes blinking {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} 100% {{ opacity: 1; }} }}
    
    /* Remove bordas/polígonos azuis e sombras do Streamlit */
    [data-testid="stVerticalBlock"] > div > div, [data-testid="column"] {{
        border: none !important;
        box-shadow: none !important;
    }}
    
    .stAppDeployButton {{ display: none !important; }}
    header {{ visibility: hidden; height: 0; }}
    .stApp {{ background-color: #000b1e; color: white; }}
    
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 100px;
        background: rgba(0, 11, 30, 0.98); z-index: 999;
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 40px; border-bottom: 1px solid rgba(0, 212, 255, 0.2);
    }}
    .main-content {{ margin-top: 110px; padding-bottom: 100px; }} /* Espaço para o mapa boiando */
    
    /* Barra de Alerta Dinâmica */
    .alert-bar {{
        width: 100%; padding: 8px; border-radius: 4px; text-align: center;
        font-weight: bold; font-size: 0.9rem; margin-bottom: 15px;
    }}
    .alert-red {{ background: rgba(255, 0, 0, 0.15); border: 1px solid rgba(255,0,0,0.5); color: #ff9999; animation: blinking 2s infinite; }}
    .alert-green {{ background: rgba(0, 255, 127, 0.08); border: 1px solid rgba(0, 255, 127, 0.4); color: #00ff7f; }}
    
    /* --- CONFIGURAÇÃO DO MAPA FLUTUANTE (AJUSTE AQUI A POSIÇÃO) --- */
    #mapa-flutuante-container {{
        position: fixed;
        bottom: 20px;  /* Distância do rodapé */
        right: 20px;   /* Distância da borda direita */
        width: 450px;  /* Largura do mapa boiando */
        height: 350px; /* Altura do mapa boiando */
        z-index: 1000; /* Garante que fique acima de outros itens */
        background: rgba(0, 30, 70, 0.9);
        border: 2px solid rgba(0, 212, 255, 0.3);
        border-radius: 10px;
        box-shadow: 0 0 15px rgba(0, 0, 0, 0.5);
        overflow: hidden;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER (BOLACHA AMPLIADA PARA 180PX) ---
logo_b64 = get_base64(ARQUIVO_BOLACHA)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" height="180" style="margin-top: 40px;">' if logo_b64 else ""
st.markdown(f"""
    <div class="fixed-header">
        <div class="time-container">
            <div style="font-size: 2rem; font-weight: bold; color: #00d4ff;">{now_z.strftime("%H:%M")}Z</div>
            <div style="font-size: 1rem; color: #ffcc00; font-weight: bold;">LOCAL: {now_p.strftime("%H:%M")}P</div>
        </div>
        <div style="font-size: 2.5rem; font-weight: bold; letter-spacing: 2px;">COOPERACIÓN XI</div>
        <div class="logo-container">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    # --- 1. BARRA DE ALERTA DINÂMICA (COLUNA H E I) ---
    has_active_fire = any((df['ALERTA_H'] == 'sim') & (df['STATUS_I'] == 'Ativo'))
    has_extinguished = any(df['STATUS_I'] == 'Extinto')
    
    if has_active_fire:
        st.markdown('<div class="alert-bar alert-red">⚠️ ALERTA: FOCOS DE INCENDIO ACTIVOS DETECTADOS</div>', unsafe_allow_html=True)
    elif has_extinguished:
        st.markdown('<div class="alert-bar alert-green">✅ STATUS: FOCOS EXTINGUIDOS / BAJO CONTROL</div>', unsafe_allow_html=True)

    # --- 2. CONTROLES DO MAPA (TOGGLES) - AGORA ACIMA DO TIMELINE ---
    st.markdown('<p style="color:#888; font-weight:bold; font-size:0.9rem; margin-bottom:0px;">VISUALIZACIÓN MAPA</p>', unsafe_allow_html=True)
    c_toggle1, c_toggle2, _ = st.columns([1.5, 1.5, 6])
    show_foc = c_toggle1.toggle("🔥 Focos Incendio", value=True)
    show_aero = c_toggle2.toggle("✈️ Medios Aéreos", value=True)

    # --- 3. LÍNEA DEL TIEMPO (ZOOM ±2H E FONTE AMPLIADA) ---
    st.markdown('<p style="color:#00d4ff; font-weight:bold; font-size:1.2rem; margin-bottom:10px;">⏳ LÍNEA DEL TIEMPO</p>', unsafe_allow_html=True)
    
    filtro_t = df['LAYER'].str.upper().isin(['MEIOS AÉREOS', 'REUNIÃO', 'REUNIÓN', 'REUNIAO'])
    df_timeline = df[filtro_t & df['inicio_zulu'].notna() & df['fim_zulu'].notna()].copy()

    if not df_timeline.empty:
        fig = px.timeline(df_timeline, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave", 
                          color="aeronave", text="COLUNA_A", template="plotly_dark", height=380)
        fig.add_vline(x=now_z, line_width=4, line_color="#ff4b4b") # Linha vermelha mais grossa
        
        fig.update_traces(
            textposition='inside', 
            insidetextanchor='middle', 
            textfont=dict(size=14, color="white", family="Arial Black") # Aumentado para 14px e Negrito
        )
        
        fig.update_layout(
            showlegend=False,
            xaxis=dict(
                side="top",
                title=None,
                # ZOOM NATIVO ±2H CENTRALIZADO NA LINHA ATUAL
                range=[now_z - timedelta(hours=2), now_z + timedelta(hours=2)],
                rangeslider=dict(visible=True, thickness=0.03),
                rangeselector=dict(buttons=list([
                    dict(count=2, label="2h", step="hour", stepmode="backward"),
                    dict(count=6, label="6h", step="hour", stepmode="backward"),
                    dict(step="all", label="Todo")
                ]), bgcolor="#001e46", y=1.2)),
            margin=dict(l=10, r=10, t=60, b=10)
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'scrollZoom': True})

    st.markdown('<hr style="border: 0.5px solid rgba(0, 212, 255, 0.1); margin: 20px 0;">', unsafe_allow_html=True)

    # --- 4. BLOCO INFERIOR (MAPA FLUTUANTE COM PERSISTÊNCIA + VECTORES) ---
    # Usamos uma coluna vazia à esquerda para o mapa flutuante ocupar espaço visual
    col_vazia, col_vec = st.columns([2.5, 1])
    
    with col_vec:
        st.markdown('<p style="text-align:center; color:#00d4ff; font-weight:bold; font-size:1.2rem;">📊 VECTORES</p>', unsafe_allow_html=True)
        df_op = df[df['LAYER']=='Meios Aéreos']
        st.metric("EN OPERACIÓN", len(df_op))
        st.dataframe(df_op[['aeronave', 'missao']].rename(columns={'missao': 'misión'}), hide_index=True, use_container_width=True, height=350)

    # --- 5. O MAPA FLUTUANTE COM MEMÓRIA DE POSIÇÃO (Lógica Session State) ---
    m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles='cartodbpositron', zoom_control=True)
    
    for _, row in df.iterrows():
        if row['lat_clean'] and row['lon_clean']:
            # Ícone de Aeronave (Azul)
            if row['LAYER'] == 'Meios Aéreos' and show_aero:
                folium.Marker([row['lat_clean'], row['lon_clean']],
                    popup=f"Aeronave: {row['aeronave']}",
                    icon=folium.Icon(color='blue', icon='plane', prefix='fa')).add_to(m)
            # Ícone de Foco de Incêndio (Vermelho Ativo / Cinza Extinto)
            elif 'Focos' in str(row['LAYER']) and show_foc:
                color_f = 'red' if row['STATUS_I'] == 'Ativo' else 'gray'
                folium.Marker([row['lat_clean'], row['lon_clean']],
                    popup=f"Foco: {row['STATUS_I']}",
                    icon=folium.Icon(color=color_f, icon='fire', prefix='fa')).add_to(m)
    
    # Renderizamos o mapa dentro do contêiner flutuante definido no CSS
    with st.container():
        st.markdown('<div id="mapa-flutuante-container">', unsafe_allow_html=True)
        # st_folium retorna os dados atuais do mapa (zoom e centro) para persistência
        map_data = st_folium(m, width=446, height=346, key="map_persist")
        
        # Se o usuário mexer no mapa, salvamos o novo estado para a próxima atualização
        if map_data['center'] is not None:
            st.session_state.map_center = [map_data['center']['lat'], map_data['center']['lng']]
        if map_data['zoom'] is not None:
            st.session_state.map_zoom = map_data['zoom']
            
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 6. DETALLE DE MISIONES (RODAPÉ) ---
    st.markdown('<p style="color:#00ff7f; font-weight:bold; font-size:0.9rem; margin-top:20px;">📋 DETALLE DE MISIONES</p>', unsafe_allow_html=True)
    df_det = df[['LAYER', 'aeronave', 'missao', 'lat', 'lon']].dropna(subset=['aeronave'])
    df_det.columns = ['CAPA', 'AERONAVE', 'MISIÓN', 'LAT', 'LON']
    st.dataframe(df_det, use_container_width=True, hide_index=True)

st.markdown('</div>', unsafe_allow_html=True)
