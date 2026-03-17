<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Operacional - Cooperación XI</title>
    
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
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 20px;
            overflow-x: hidden;
        }

        /* Cabeçalho */
        .header {
            display: flex;
            align-items: baseline;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 10px;
            margin-bottom: 20px;
        }

        .zulu-time {
            font-size: 42px;
            font-weight: bold;
            font-family: 'Courier New', Courier, monospace;
            margin-right: 20px;
        }

        .local-time {
            color: var(--accent-yellow);
            font-weight: bold;
            font-size: 18px;
            margin-right: auto;
        }

        .title {
            font-size: 32px;
            font-weight: bold;
            text-transform: uppercase;
            text-shadow: 0 0 10px rgba(0, 242, 255, 0.7);
        }

        /* Timeline Superior */
        .timeline-container {
            background: rgba(0, 22, 45, 0.8);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 45px 20px 20px 20px;
            position: relative;
            margin-bottom: 25px;
        }

        .time-markers {
            display: flex;
            justify-content: space-between;
            position: absolute;
            top: 15px;
            left: 20px;
            right: 20px;
            color: var(--accent-yellow);
            font-size: 12px;
            font-weight: bold;
            border-bottom: 1px solid rgba(255, 204, 0, 0.2);
            padding-bottom: 5px;
        }

        .timeline-track {
            height: 50px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
            position: relative;
            display: flex;
            align-items: center;
        }

        /* Polígono Centralizado */
        .mission-polygon {
            position: absolute;
            height: 36px;
            background: linear-gradient(90deg, #004a7c, #00f2ff);
            clip-path: polygon(3% 0%, 97% 0%, 100% 50%, 97% 100%, 3% 100%, 0% 50%);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 15px rgba(0, 242, 255, 0.3);
        }

        .polygon-text {
            color: white;
            font-weight: bold;
            font-size: 12px;
            text-transform: uppercase;
            white-space: nowrap;
            padding: 0 15px;
        }

        /* Layout Principal: Mapa e Tabela */
        .main-layout {
            display: flex;
            gap: 20px;
            height: 500px;
        }

        #map {
            flex: 2.5;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: #0a0a0a;
        }

        /* Remover Marca d'água/Atribuição do Leaflet */
        .leaflet-control-attribution {
            display: none !important;
        }

        .side-panel {
            flex: 1;
            background-color: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 15px;
            display: flex;
            flex-direction: column;
        }

        .panel-header {
            color: var(--accent-blue);
            font-weight: bold;
            text-transform: uppercase;
            margin-bottom: 15px;
            font-size: 14px;
            letter-spacing: 1px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            text-align: left;
            color: #8899aa;
            font-size: 11px;
            text-transform: uppercase;
            padding: 10px;
            border-bottom: 1px solid var(--border-color);
        }

        td {
            padding: 12px 10px;
            font-size: 13px;
            border-bottom: 1px solid #002244;
        }

        .row-highlight {
            background-color: rgba(0, 242, 255, 0.05);
        }
    </style>
</head>
<body>

    <div class="header">
        <div class="zulu-time" id="zulu-clock">17:19:16Z</div>
        <div class="local-time">LOCAL: 13:19P</div>
        <div class="title">Cooperación XI</div>
    </div>

    <div class="timeline-container">
        <div class="time-markers">
            <span>08:00</span><span>10:00</span><span>12:00</span><span>14:00</span><span>16:00</span><span>18:00</span><span>20:00</span>
        </div>
        <div class="timeline-track">
            <div class="mission-polygon" style="left: 15%; width: 25%;">
                <span class="polygon-text">FAB 1400</span>
            </div>
            <div class="mission-polygon" style="left: 50%; width: 20%; background: linear-gradient(90deg, #7c3a00, #ffcc00);">
                <span class="polygon-text">FAB 2852</span>
            </div>
        </div>
    </div>

    <div class="main-layout">
        <div id="map"></div>

        <div class="side-panel">
            <div class="panel-header">
                <span>📊</span> Vectores em Operação
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Aeronave</th>
                        <th>Misión</th>
                        <th>QTDE</th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="row-highlight">
                        <td>FAB 1400</td>
                        <td>KC390</td>
                        <td>1</td>
                    </tr>
                    <tr>
                        <td>FAB 2852</td>
                        <td>C-105 SAR</td>
                        <td>1</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        // Inicialização do Mapa (Focado em Mato Grosso do Sul)
        const map = L.map('map', {
            zoomControl: false,
            attributionControl: false // Remove a marca d'água por padrão no objeto
        }).setView([-20.46, -54.61], 6);

        // Camada de mapa escura e limpa (sem marcas d'água visíveis)
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            maxZoom: 19
        }).addTo(map);

        // Adicionando um marcador de exemplo (Base Aérea)
        const airbaseIcon = L.divIcon({
            className: 'custom-div-icon',
            html: "<div style='background-color:#00f2ff; width:12px; height:12px; border-radius:50%; border:2px solid white; box-shadow: 0 0 10px #00f2ff;'></div>",
            iconSize: [12, 12],
            iconAnchor: [6, 6]
        });

        L.marker([-20.46, -54.61], {icon: airbaseIcon}).addTo(map)
            .bindPopup('Campo Grande (SBCG)');

        // Relógio Zulu em tempo real
        function updateClock() {
            const now = new Date();
            const h = String(now.getUTCHours()).padStart(2, '0');
            const m = String(now.getUTCMinutes()).padStart(2, '0');
            const s = String(now.getUTCSeconds()).padStart(2, '0');
            document.getElementById('zulu-clock').textContent = `${h}:${m}:${s}Z`;
        }
        setInterval(updateClock, 1000);
        updateClock();
    </script>
</body>
</html>
