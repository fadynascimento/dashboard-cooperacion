import streamlit as st
import streamlit.components.v1 as components

# Configuração da página para ocupar a tela toda
st.set_page_config(layout="wide", page_title="Dashboard Cooperación XI")

# O código HTML/CSS completo que montamos
html_code = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        :root {
            --bg-color: #000c1d;
            --panel-bg: #00162d;
            --accent-blue: #00f2ff;
            --accent-yellow: #ffcc00;
            --border-color: #004a7c;
        }
        body {
            background-color: var(--bg-color);
            color: white;
            font-family: 'Segoe UI', sans-serif;
            margin: 0;
            padding: 10px;
            overflow: hidden;
        }
        .header {
            display: flex;
            align-items: baseline;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 5px;
            margin-bottom: 15px;
        }
        .zulu-time { font-size: 38px; font-weight: bold; font-family: monospace; margin-right: 20px; }
        .local-time { color: var(--accent-yellow); font-weight: bold; margin-right: auto; }
        .title { font-size: 28px; font-weight: bold; text-transform: uppercase; text-shadow: 0 0 10px var(--accent-blue); }
        
        /* Timeline */
        .timeline-container {
            background: rgba(0, 22, 45, 0.8);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 40px 20px 15px 20px;
            position: relative;
            margin-bottom: 20px;
        }
        .time-markers {
            display: flex;
            justify-content: space-between;
            position: absolute;
            top: 10px; left: 20px; right: 20px;
            color: var(--accent-yellow);
            font-size: 11px;
            font-weight: bold;
            border-bottom: 1px solid rgba(255, 204, 0, 0.2);
        }
        .timeline-track {
            height: 40px;
            background: rgba(255, 255, 255, 0.05);
            position: relative;
            display: flex;
            align-items: center;
        }
        .mission-polygon {
            position: absolute;
            height: 30px;
            background: linear-gradient(90deg, #004a7c, var(--accent-blue));
            clip-path: polygon(3% 0%, 97% 0%, 100% 50%, 97% 100%, 3% 100%, 0% 50%);
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .polygon-text { color: white; font-weight: bold; font-size: 11px; text-transform: uppercase; }

        /* Mapa e Tabela */
        .main-layout { display: flex; gap: 15px; height: 450px; }
        #map { flex: 2.5; border: 1px solid var(--border-color); border-radius: 8px; }
        .leaflet-control-attribution { display: none !important; }
        
        .side-panel {
            flex: 1;
            background-color: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 15px;
        }
        .panel-header { color: var(--accent-blue); font-weight: bold; text-transform: uppercase; margin-bottom: 10px; font-size: 13px; }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; color: #8899aa; font-size: 10px; padding: 8px; border-bottom: 1px solid var(--border-color); }
        td { padding: 10px 8px; font-size: 12px; border-bottom: 1px solid #002244; }
    </style>
</head>
<body>
    <div class="header">
        <div class="zulu-time" id="zulu-clock">00:00:00Z</div>
        <div class="local-time">LOCAL: 13:19P</div>
        <div class="title">Cooperación XI</div>
    </div>

    <div class="timeline-container">
        <div class="time-markers">
            <span>08:00</span><span>10:00</span><span>12:00</span><span>14:00</span><span>16:00</span><span>18:00</span><span>20:00</span>
        </div>
        <div class="timeline-track">
            <div class="mission-polygon" style="left: 15%; width: 25%;"><span class="polygon-text">FAB 1400</span></div>
            <div class="mission-polygon" style="left: 50%; width: 20%; background: linear-gradient(90deg, #7c3a00, #ffcc00);"><span class="polygon-text">FAB 2852</span></div>
        </div>
    </div>

    <div class="main-layout">
        <div id="map"></div>
        <div class="side-panel">
            <div class="panel-header">📊 Vectores em Operação</div>
            <table>
                <thead><tr><th>Aeronave</th><th>Misión</th><th>QTDE</th></tr></thead>
                <tbody>
                    <tr><td>FAB 1400</td><td>KC390</td><td>1</td></tr>
                    <tr><td>FAB 2852</td><td>C-105 SAR</td><td>1</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const map = L.map('map', { zoomControl: false, attributionControl: false }).setView([-20.46, -54.61], 6);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png').addTo(map);
        
        function updateClock() {
            const now = new Date();
            const h = String(now.getUTCHours()).padStart(2, '0');
            const m = String(now.getUTCMinutes()).padStart(2, '0');
            const s = String(now.getUTCSeconds()).padStart(2, '0');
            document.getElementById('zulu-clock').textContent = h + ':' + m + ':' + s + 'Z';
        }
        setInterval(updateClock, 1000); updateClock();
    </script>
</body>
</html>
"""

# Renderiza o componente no Streamlit
components.html(html_code, height=800, scrolling=True)
