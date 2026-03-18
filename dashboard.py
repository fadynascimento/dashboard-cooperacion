import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from datetime import datetime, timezone, timedelta
os, base64, time, re
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="COOPERACIÓN XI - COI", page_icon="✈️")

# --- AUTO-REFRESH (30 segundos) ---
st_autorefresh(interval=30000, limit=None, key="refresh_dashboard")

# --- INICIALIZAÇÃO DO ESTADO DO MAPA (PERSISTÊNCIA) ---
if 'map_center' not in st.session_state:
    st.session_state.map_center = [-18.5, -56.5] # Coordenada inicial
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

# --- ESTILO CSS ---
st.markdown(f"""
    <style>
    @keyframes blinking {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} 100% {{ opacity: 1; }} }}
    [data-testid="stVerticalBlock"] > div > div, [data-testid="column"] {{ border: none !important; box-shadow: none !important; }}
    header {{ visibility: hidden; height: 0; }}
    .stApp {{ background-color: #000b1e; color: white; }}
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 100px;
        background: rgba(0, 11, 30, 0.98); z-index: 999;
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 40px; border-bottom: 1px solid rgba(0, 212, 255, 0.2);
    }}
    .main-content {{ margin-top: 110px; padding-bottom: 100px; }}
    .alert-bar {{ width: 100%; padding: 8px; border-radius: 4px; text-align: center; font-weight: bold; font-size: 0.9rem; margin-bottom: 15px; }}
    .alert-red {{ background: rgba(255, 0, 0, 0.15); border: 1px solid rgba(255,0,0,0.5); color: #ff9999; animation: blinking 2s infinite; }}
    .alert-green {{ background: rgba(0, 255, 127, 0.08); border: 1px solid rgba(0, 255, 127, 0.4); color: #00ff7f; }}
    
    #mapa-flutuante-container {{
        position: fixed; bottom: 20px; right: 20px; width: 450px; height: 350px;
        z-index: 1000; background: rgba(0, 30, 70, 0.9);
        border: 2px solid rgba(0, 212, 255, 0.3); border-radius: 10px;
        box-shadow: 0 0 15px rgba(0, 0, 0, 0.5); overflow: hidden;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
logo_b64 = get_base64(ARQUIVO_BOLACHA)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" height="180" style="margin-top: 40px;">' if logo_b64 else ""
st.markdown(f'<div class="fixed-header"><div><div style="font-size: 2rem; font-weight: bold; color: #00d4ff;">{now_z.strftime("%H:%M")}Z</div><div style="font-size: 1rem; color: #ffcc00; font-weight: bold;">LOCAL: {now_p.strftime("%H:%M")}P</div></div><div style="font-size: 2.5rem; font-weight: bold; letter-spacing: 2px;">COOPERACIÓN XI</div><div class="logo-container">{logo_html}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if df is not None:
    # 1. ALERTAS
    has_active_fire = any((df['ALERTA_H'] == 'sim') & (df['STATUS_I'] == 'Ativo'))
    if has_active_fire: st.markdown('<div class="alert-bar alert-red">⚠️ ALERTA: FOCOS DE INCENDIO ACTIVOS</div>', unsafe_allow_html=True)
    elif any(df['STATUS_I'] == 'Extinto'): st.markdown('<div class="alert-bar alert-green">✅ STATUS: FOCOS EXTINGUIDOS</div>', unsafe_allow_html=True)

    # 2. CONTROLES ACIMA DA TIMELINE
    st.markdown('<p style="color:#888; font-weight:bold; font-size:0.9rem;">VISUALIZACIÓN MAPA</p>', unsafe_allow_html=True)
    c_t1, c_t2, _ = st.columns([1.5, 1.5, 6])
    show_foc = c_t1.toggle("🔥 Focos", value=True)
    show_aero = c_t2.toggle("✈️ Medios", value=True)

    # 3. LÍNEA DEL TIEMPO (2h past / 2h future)
    filtro_t = df['LAYER'].str.upper().isin(['MEIOS AÉREOS', 'REUNIÃO', 'REUNIÓN', 'REUNIAO'])
    df_t = df[filtro_t & df['inicio_zulu'].notna() & df['fim_zulu'].notna()].copy()
    if not df_t.empty:
        fig = px.timeline(df_t, x_start="inicio_zulu", x_end="fim_zulu", y="aeronave", color="aeronave", text="COLUNA_A", template="plotly_dark", height=380)
        fig.add_vline(x=now_z, line_width=4, line_color="#ff4b4b")
        fig.update_traces(textposition='inside', insidetextanchor='middle', textfont=dict(size=14, color="white", family="Arial Black"))
        fig.update_layout(showlegend=False, xaxis=dict(side="top", range=[now_z - timedelta(hours=2), now_z + timedelta(hours=2)], rangeslider=dict(visible=True, thickness=0.03)), margin=dict(l=10, r=10, t=60, b=10))
        st.plotly_chart(fig, use_container_width=True)

    # 4. MAPA FLUTUANTE COM PERSISTÊNCIA
    m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles='cartodbpositron', zoom_control=True)
    
    for _, row in df.iterrows():
        if row['lat_clean'] and row['lon_clean']:
            if row['LAYER'] == 'Meios Aéreos' and show_aero:
                folium.Marker([row['lat_clean'], row['lon_clean']], icon=folium.Icon(color='blue', icon='plane', prefix='fa')).add_to(m)
            elif 'Focos' in str(row['LAYER']) and show_foc:
                folium.Marker([row['lat_clean'], row['lon_clean']], icon=folium.Icon(color='red' if row['STATUS_I'] == 'Ativo' else 'gray', icon='fire', prefix='fa')).add_to(m)

    with st.container():
        st.markdown('<div id="mapa-flutuante-container">', unsafe_allow_html=True)
        # O pulo do gato: st_folium retorna os dados atuais do mapa (zoom e centro)
        map_data = st_folium(m, width=446, height=346, key="map_persist")
        
        # Se o usuário mexer no mapa, salvamos o novo estado para a próxima atualização
        if map_data['center'] is not None:
            st.session_state.map_center = [map_data['center']['lat'], map_data['center']['lng']]
        if map_data['zoom'] is not None:
            st.session_state.map_zoom = map_data['zoom']
            
        st.markdown('</div>', unsafe_allow_html=True)

    # 5. VECTORES E DETALHE
    cv1, cv2 = st.columns([2.5, 1])
    with cv2:
        st.metric("EN OPERACIÓN", len(df[df['LAYER']=='Meios Aéreos']))
        st.dataframe(df[df['LAYER']=='Meios Aéreos'][['aeronave', 'missao']], hide_index=True)

st.markdown('</div>', unsafe_allow_html=True)
