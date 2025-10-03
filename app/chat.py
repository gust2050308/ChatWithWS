from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
from typing import Dict, List
import uvicorn
from datetime import datetime

# 🔐 NUEVAS IMPORTACIONES
from websocket_crypto import crypto_manager
import asyncio
import time

app = FastAPI()

# Diccionario para almacenar las conexiones WebSocket activas
# Clave: username, Valor: WebSocket connection
active_connections: Dict[str, WebSocket] = {}

# Lista para almacenar conexiones de monitores (para ver mensajes en tiempo real)
monitor_connections: List[WebSocket] = []

# Lista para almacenar historial de mensajes (opcional)
message_history: List[dict] = []


# 🔐 NUEVA FUNCIÓN: Limpieza periódica de claves
async def periodic_key_cleanup():
    """Tarea de limpieza automática de claves expiradas"""
    while True:
        await asyncio.sleep(3600)  # Ejecutar cada hora
        try:
            crypto_manager._clean_old_keys()
            print("🔑 Claves expiradas limpiadas automáticamente")
        except Exception as e:
            print(f"❌ Error en limpieza de claves: {e}")


async def periodic_key_rotation():
    """Rotación automática de claves cada hora"""
    while True:
        await asyncio.sleep(3600)  # Cada hora
        try:
            if crypto_manager.rotate_key_if_needed():
                print("🔄 Clave rotada automáticamente")

                # Notificar a todos los clientes activos
                key_id, key_base64 = crypto_manager.get_current_key_base64()
                disconnected = []

                for username, ws in active_connections.items():
                    try:
                        await ws.send_text(json.dumps({
                            "type": "key_rotation",
                            "key_id": key_id,
                            "key_base64": key_base64,
                            "message": "Clave rotada, actualizando..."
                        }))
                    except:
                        disconnected.append(username)

                # Limpiar desconectados
                for user in disconnected:
                    del active_connections[user]

        except Exception as e:
            print(f"❌ Error en rotación de claves: {e}")


@app.on_event("startup")
async def startup_event():
    """Iniciar tareas en background al arrancar la aplicación"""
    asyncio.create_task(periodic_key_cleanup())
    asyncio.create_task(periodic_key_rotation())  # NUEVA LÍNEA
    print("🚀 Servidor iniciado con cifrado WebSocket habilitado")


@app.get("/monitor")
async def monitor_page():
    """Página de monitoreo con estilo Classroom"""
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Brainstorm - Tiempo Real</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap" rel="stylesheet">
            <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                body {
                    font-family: 'Google Sans', sans-serif;
                    background-color: #f8f9fa;
                    height: 100vh;
                    display: flex;
                    flex-direction: column;
                }
                .header {
                    background: linear-gradient(135deg, #1976d2, #42a5f5);
                    color: white;
                    padding: 1.5rem 2rem;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                }
                .header h1 {
                    font-size: 1.8rem;
                    font-weight: 500;
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                    margin-bottom: 0.5rem;
                }
                .header p {
                    opacity: 0.9;
                    font-size: 1rem;
                }
                .dashboard {
                    display: flex;
                    flex: 1;
                    overflow: hidden;
                }
                .sidebar {
                    width: 300px;
                    background: white;
                    border-right: 1px solid #e8eaed;
                    display: flex;
                    flex-direction: column;
                }
                .stats-section {
                    padding: 2rem;
                    border-bottom: 1px solid #e8eaed;
                }
                .stat-card {
                    background: #f8f9fa;
                    padding: 1rem;
                    border-radius: 12px;
                    margin-bottom: 1rem;
                    border-left: 4px solid #1976d2;
                }
                .stat-number {
                    font-size: 2rem;
                    font-weight: 700;
                    color: #1976d2;
                    display: block;
                }
                .stat-label {
                    color: #5f6368;
                    font-size: 0.9rem;
                    margin-top: 0.25rem;
                }
                .controls-section {
                    padding: 2rem;
                    flex: 1;
                }
                .control-group {
                    margin-bottom: 2rem;
                }
                .control-group h3 {
                    color: #3c4043;
                    font-size: 1.1rem;
                    margin-bottom: 1rem;
                    font-weight: 500;
                }
                .control-btn {
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    width: 100%;
                    padding: 0.75rem 1rem;
                    border: 1px solid #e8eaed;
                    background: white;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    margin-bottom: 0.5rem;
                    font-family: inherit;
                    font-size: 0.9rem;
                    color: #3c4043;
                }
                .control-btn:hover {
                    border-color: #1976d2;
                    color: #1976d2;
                    box-shadow: 0 1px 3px rgba(25, 118, 210, 0.1);
                }
                .control-btn.active {
                    background: #e3f2fd;
                    border-color: #1976d2;
                    color: #1976d2;
                }
                .monitor-area {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    background: white;
                    margin: 1rem;
                    border-radius: 12px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
                    overflow: hidden;
                }
                .monitor-header {
                    padding: 1rem 2rem;
                    background: #f8f9fa;
                    border-bottom: 1px solid #e8eaed;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }
                .monitor-title {
                    font-size: 1.2rem;
                    font-weight: 500;
                    color: #3c4043;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                }
                .connection-status {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    padding: 0.5rem 1rem;
                    border-radius: 20px;
                    font-size: 0.8rem;
                    font-weight: 500;
                }
                .connection-status.connected {
                    background: #e8f5e8;
                    color: #137333;
                }
                .connection-status.disconnected {
                    background: #fce8e6;
                    color: #d93025;
                }
                .status-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: currentColor;
                    animation: pulse 2s infinite;
                }
                .messages-area {
                    flex: 1;
                    overflow-y: auto;
                    padding: 1rem;
                    background: #fafbfc;
                }
                .message-item {
                    background: white;
                    border: 1px solid #e8eaed;
                    border-radius: 12px;
                    padding: 1rem;
                    margin-bottom: 0.75rem;
                    animation: slideIn 0.3s ease;
                    transition: all 0.2s ease;
                }
                .message-item:hover {
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                .message-item.system {
                    background: #fff3cd;
                    border-color: #ffc107;
                    border-left: 4px solid #ffc107;
                }
                .message-item.error {
                    background: #f8d7da;
                    border-color: #dc3545;
                    border-left: 4px solid #dc3545;
                }
                .message-item.encrypted {
                    border-left: 4px solid #9c27b0;
                    background: #f3e5f5;
                }
                @keyframes slideIn {
                    from { opacity: 0; transform: translateX(-10px); }
                    to { opacity: 1; transform: translateX(0); }
                }
                .message-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 0.5rem;
                }
                .message-user {
                    font-weight: 500;
                    color: #1976d2;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    flex: 1;
                }
                .message-time {
                    font-size: 0.8rem;
                    color: #5f6368;
                }
                .message-content {
                    color: #3c4043;
                    line-height: 1.4;
                    word-wrap: break-word;
                }
                .encryption-badge {
                    font-size: 0.7rem;
                    background: #9c27b0;
                    color: white;
                    padding: 0.2rem 0.5rem;
                    border-radius: 10px;
                    margin-left: 0.5rem;
                }
                .user-avatar {
                    width: 24px;
                    height: 24px;
                    background: linear-gradient(135deg, #1976d2, #42a5f5);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 0.7rem;
                    font-weight: 500;
                }
                .empty-state {
                    text-align: center;
                    padding: 3rem;
                    color: #5f6368;
                }
                .empty-state i {
                    font-size: 3rem;
                    margin-bottom: 1rem;
                    opacity: 0.5;
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>
                    <i class="material-icons">monitor</i>
                    Brainstorm en Tiempo Real
                </h1>
                <p>Supervisión completa de todas las conversaciones del servidor</p>
            </div>

            <div class="dashboard">
                <div class="sidebar">
                    <div class="stats-section">
                        <div class="stat-card">
                            <span class="stat-number" id="activeUsers">0</span>
                            <div class="stat-label">Usuarios Activos</div>
                        </div>
                        <div class="stat-card">
                            <span class="stat-number" id="totalMessages">0</span>
                            <div class="stat-label">Mensajes Total</div>
                        </div>
                        <div class="stat-card">
                            <span class="stat-number" id="messagesPerMinute">0</span>
                            <div class="stat-label">Mensajes/Minuto</div>
                        </div>
                        <div class="stat-card">
                            <span class="stat-number" id="activeKeys">0</span>
                            <div class="stat-label">Claves Activas</div>
                        </div>
                    </div>

                    <div class="controls-section">
                        <div class="control-group">
                            <h3>Controles</h3>
                            <button class="control-btn" onclick="clearMessages()">
                                <i class="material-icons">clear_all</i>
                                Limpiar Monitor
                            </button>
                            <button class="control-btn active" id="autoScrollBtn" onclick="toggleAutoScroll()">
                                <i class="material-icons">keyboard_arrow_down</i>
                                Auto-scroll Activo
                            </button>
                            <button class="control-btn" onclick="exportMessages()">
                                <i class="material-icons">download</i>
                                Exportar Mensajes
                            </button>
                        </div>

                        <div class="control-group">
                            <h3>Filtros</h3>
                            <button class="control-btn active" onclick="toggleFilter('all')">
                                <i class="material-icons">forum</i>
                                Todos los Mensajes
                            </button>
                            <button class="control-btn" onclick="toggleFilter('users')">
                                <i class="material-icons">person</i>
                                Solo Usuarios
                            </button>
                            <button class="control-btn" onclick="toggleFilter('system')">
                                <i class="material-icons">settings</i>
                                Solo Sistema
                            </button>
                            <button class="control-btn" onclick="toggleFilter('encrypted')">
                                <i class="material-icons">lock</i>
                                Mensajes Cifrados
                            </button>
                        </div>
                    </div>
                </div>

                <div class="monitor-area">
                    <div class="monitor-header">
                        <div class="monitor-title">
                            <i class="material-icons">chat</i>
                            Feed de Mensajes
                        </div>
                        <div class="connection-status disconnected" id="connectionStatus">
                            <div class="status-dot"></div>
                            <span>Conectando...</span>
                        </div>
                    </div>

                    <div class="messages-area" id="messagesArea">
                        <div class="empty-state">
                            <i class="material-icons">chat_bubble_outline</i>
                            <p>Esperando mensajes...</p>
                        </div>
                    </div>
                </div>
            </div>

            <script>
                // Variables globales para el monitor
                let monitorWS = null;
                let messageCount = 0;
                let autoScroll = true;
                let currentFilter = 'all';
                let messagesPerMinute = 0;
                let messageTimestamps = [];

                // Referencias DOM
                const messagesArea = document.getElementById('messagesArea');
                const connectionStatus = document.getElementById('connectionStatus');
                const autoScrollBtn = document.getElementById('autoScrollBtn');

                // Función para inicializar el WebSocket del monitor
                function initializeMonitorWebSocket() {
                    try {
                        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                        monitorWS = new WebSocket(protocol + '//' + window.location.host + '/monitor/ws');
                        
                        monitorWS.onopen = function(event) {
                            console.log("Monitor conectado");
                            updateConnectionStatus('connected', 'Conectado');
                            addSystemMessage('Monitor conectado exitosamente');
                        };

                        monitorWS.onmessage = function(event) {
                            try {
                                const data = JSON.parse(event.data);
                        
                                if (data.type === 'message') {
                                    // Mostrar mensaje del usuario
                                    addMessage(data.username, data.message, data.timestamp, data.is_encrypted ? 'encrypted' : 'user');
                                    updateMessageStats();
                                } 
                                else if (data.type === 'user_connected') {
                                    addSystemMessage(`Usuario conectado: ${data.username}`);
                                    updateUserCount(data.active_count);
                                } 
                                else if (data.type === 'user_disconnected') {
                                    addSystemMessage(`Usuario desconectado: ${data.username}`);
                                    updateUserCount(data.active_count);
                                } 
                                else if (data.type === 'status_update') {
                                    updateUserCount(data.active_count);
                                    // No mostrar en el feed
                                } 
                                else if (data.type === 'key_info') {
                                    updateKeyInfo(data.key_info);
                                    // No mostrar en el feed
                                }
                            } catch (e) {
                                console.error('Error procesando mensaje del monitor:', e);
                            }
                        };
                        monitorWS.onclose = function(event) {
                            console.log("Monitor desconectado");
                            updateConnectionStatus('disconnected', 'Desconectado');
                            addSystemMessage('Monitor desconectado', true);
                        };

                        monitorWS.onerror = function(error) {
                            console.log("Error en monitor:", error);
                            updateConnectionStatus('disconnected', 'Error de conexión');
                            addSystemMessage('Error de conexión', true);
                        };
                    } catch (error) {
                        console.error("Error al crear WebSocket del monitor:", error);
                        updateConnectionStatus('disconnected', 'Error');
                    }
                }

                function updateConnectionStatus(status, text) {
                    connectionStatus.className = `connection-status ${status}`;
                    connectionStatus.querySelector('span').textContent = text;
                }

                function updateUserCount(count) {
                    document.getElementById('activeUsers').textContent = count;
                }

                function updateKeyInfo(keyInfo) {
                    document.getElementById('activeKeys').textContent = keyInfo.total_keys;
                }

                function updateMessageStats() {
                    messageCount++;
                    document.getElementById('totalMessages').textContent = messageCount;

                    // Calcular mensajes por minuto
                    const now = Date.now();
                    messageTimestamps.push(now);

                    // Mantener solo timestamps de los últimos 60 segundos
                    messageTimestamps = messageTimestamps.filter(time => now - time < 60000);
                    messagesPerMinute = messageTimestamps.length;
                    document.getElementById('messagesPerMinute').textContent = messagesPerMinute;
                }

                function addMessage(username, message, timestamp, type = 'user') {
                    // Limpiar empty state si existe
                    if (messagesArea.querySelector('.empty-state')) {
                        messagesArea.innerHTML = '';
                    }

                    const messageDiv = document.createElement('div');
                    messageDiv.className = `message-item ${type}`;
                    messageDiv.setAttribute('data-type', type);

                    const time = new Date(timestamp).toLocaleTimeString();
                    const userInitial = username.charAt(0).toUpperCase();

                    let encryptionBadge = '';
                    if (type === 'encrypted') {
                        encryptionBadge = '<span class="encryption-badge">CIFRADO</span>';
                    }

                    messageDiv.innerHTML = `
                        <div class="message-header">
                            <div class="message-user">
                                <div class="user-avatar">${userInitial}</div>
                                <span>${username}</span>
                                ${encryptionBadge}
                            </div>
                            <div class="message-time">${time}</div>
                        </div>
                        <div class="message-content">${message}</div>
                    `;

                    messagesArea.appendChild(messageDiv);

                    // Aplicar filtro
                    applyCurrentFilter();

                    // Auto-scroll
                    if (autoScroll) {
                        messagesArea.scrollTop = messagesArea.scrollHeight;
                    }
                }

                function addSystemMessage(message, isError = false) {
                    addMessage('Sistema', message, new Date().toISOString(), isError ? 'error' : 'system');
                }

                function clearMessages() {
                    messagesArea.innerHTML = `
                        <div class="empty-state">
                            <i class="material-icons">chat_bubble_outline</i>
                            <p>Monitor limpiado. Esperando nuevos mensajes...</p>
                        </div>
                    `;
                    messageCount = 0;
                    document.getElementById('totalMessages').textContent = messageCount;
                    messageTimestamps = [];
                    document.getElementById('messagesPerMinute').textContent = 0;
                }

                function toggleAutoScroll() {
                    autoScroll = !autoScroll;
                    autoScrollBtn.classList.toggle('active');
                    autoScrollBtn.innerHTML = `
                        <i class="material-icons">${autoScroll ? 'keyboard_arrow_down' : 'pause'}</i>
                        Auto-scroll ${autoScroll ? 'Activo' : 'Pausado'}
                    `;
                }

                function toggleFilter(filter) {
                    // Actualizar botones
                    document.querySelectorAll('.control-group:last-child .control-btn').forEach(btn => {
                        btn.classList.remove('active');
                    });
                    event.target.classList.add('active');

                    currentFilter = filter;
                    applyCurrentFilter();
                }

                function applyCurrentFilter() {
                    const messages = messagesArea.querySelectorAll('.message-item');
                    messages.forEach(msg => {
                        const type = msg.getAttribute('data-type');
                        let show = false;

                        switch(currentFilter) {
                            case 'all':
                                show = true;
                                break;
                            case 'users':
                                show = type === 'user' || type === 'encrypted';
                                break;
                            case 'system':
                                show = type === 'system' || type === 'error';
                                break;
                            case 'encrypted':
                                show = type === 'encrypted';
                                break;
                        }

                        msg.style.display = show ? 'block' : 'none';
                    });
                }

                function exportMessages() {
                    const messages = messagesArea.querySelectorAll('.message-item:not([style*="display: none"])');
                    let exportData = 'REPORTE DE CHAT - ' + new Date().toLocaleString() + '\\n';
                    exportData += '='.repeat(50) + '\\n\\n';

                    messages.forEach(msg => {
                        const user = msg.querySelector('.message-user span').textContent;
                        const time = msg.querySelector('.message-time').textContent;
                        const content = msg.querySelector('.message-content').textContent;
                        const isEncrypted = msg.classList.contains('encrypted');
                        exportData += `[${time}] ${user}${isEncrypted ? ' [CIFRADO]' : ''}: ${content}\\n`;
                    });

                    const blob = new Blob([exportData], { type: 'text/plain' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `chat-monitor-${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.txt`;
                    a.click();
                    window.URL.revokeObjectURL(url);
                }

                // Inicialización
                document.addEventListener('DOMContentLoaded', function() {
                    console.log("Monitor iniciando...");
                    initializeMonitorWebSocket();
                });

                // Reconexión automática
                setInterval(function() {
                    if (monitorWS && monitorWS.readyState === WebSocket.CLOSED) {
                        updateConnectionStatus('disconnected', 'Reconectando...');
                        setTimeout(initializeMonitorWebSocket, 2000);
                    }
                }, 10000);
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/imAClient/{username}")
async def client_page(username: str):
    """Página del cliente con interfaz WebSocket y estilo Classroom"""
    # Usamos replace para evitar conflictos con format()
    template = """
    <!DOCTYPE html>
<html>
<head>
    <title>Cliente con Cifrado (HTTP Compatible)</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
        body {
            font-family: 'Google Sans', sans-serif;
            background: #f8f9fa;
            margin: 0;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #1976d2, #42a5f5);
            color: white;
            padding: 1.2rem 2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }
        .header h1 {
            font-size: 1.5rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin: 0;
        }
        .encryption-info {
            margin-top: 0.5rem;
            font-size: 0.85rem;
            opacity: 0.9;
        }
        .chat-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            margin: 1rem;
            background: white;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
            overflow: hidden;
        }
        .messages-area {
            flex: 1;
            padding: 1rem;
            overflow-y: auto;
            background: #fafbfc;
        }
        .message-item {
            background: white;
            border: 1px solid #e8eaed;
            border-radius: 12px;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
            animation: slideIn 0.2s ease;
        }
        .message-item.encrypted {
            border-left: 4px solid #9c27b0;
            background: #f3e5f5;
        }
        .message-item.decrypted {
            border-left: 4px solid #4caf50;
            background: #e8f5e8;
        }
        .message-item.system {
            background: #fff3cd;
            border-color: #ffc107;
        }
        .message-item.warning {
            background: #ffebee;
            border-color: #f44336;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(5px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .input-area {
            display: flex;
            border-top: 1px solid #e8eaed;
            padding: 0.75rem;
            background: #f8f9fa;
            gap: 0.5rem;
        }
        .input-area input {
            flex: 1;
            border: 1px solid #e8eaed;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            font-family: inherit;
            font-size: 0.9rem;
        }
        .input-area button {
            background: #1976d2;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.75rem 1.2rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: background 0.2s;
        }
        .input-area button:hover {
            background: #1565c0;
        }
        .input-area button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
    </style>
    <!-- Librería CryptoJS para cifrado compatible con HTTP -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.1.1/crypto-js.min.js"></script>
</head>
<body>
    <div class="header">
        <h1>
            <i class="material-icons">lock</i>
            Cliente con Cifrado Compatible
        </h1>
        <div class="encryption-info" id="encryptionInfo">
            Inicializando...
        </div>
    </div>

    <div class="chat-container">
        <div class="messages-area" id="messages"></div>
        <div class="input-area">
            <input type="text" id="messageText" placeholder="Escribe tu mensaje...">
            <button id="sendButton" disabled>
                <i class="material-icons">send</i> Enviar
            </button>
        </div>
    </div>

    <script>
        let ws = null;
        let cryptoKey = null;
        let currentKeyId = null;
        let useWebCrypto = false;
        const username = window.location.pathname.split('/').pop(); // Obtiene el username de la URL

        // Detectar si Web Crypto API está disponible
        function checkWebCryptoAvailability() {
            if (window.crypto && window.crypto.subtle) {
                useWebCrypto = true;
                addMessage('Sistema', '✅ Web Crypto API disponible (cifrado fuerte)', 'system');
                return true;
            } else {
                useWebCrypto = false;
                addMessage('Sistema', '❌ Web Crypto API NO disponible', 'warning');
                addMessage('Sistema', 'ACCEDE VÍA: https://... o http://localhost:8000', 'warning');
                addMessage('Sistema', 'El cifrado NO funcionará sin HTTPS', 'warning');
                // Deshabilitar envío de mensajes
                document.getElementById('sendButton').disabled = true;
                return false;
            }
        }

        // === CIFRADO CON WEB CRYPTO API (cuando está disponible) ===
        function base64ToArrayBuffer(base64) {
            const binaryString = atob(base64);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            return bytes.buffer;
        }

        function arrayBufferToBase64(buffer) {
            const bytes = new Uint8Array(buffer);
            let binary = '';
            for (let i = 0; i < bytes.byteLength; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            return btoa(binary);
        }

        async function importKeyWebCrypto(keyBase64) {
            const keyBuffer = base64ToArrayBuffer(keyBase64);
            cryptoKey = await crypto.subtle.importKey(
                'raw',
                keyBuffer,
                { name: 'AES-GCM', length: 256 },
                false,
                ['encrypt', 'decrypt']
            );
        }

        async function encryptWebCrypto(message) {
            const nonce = crypto.getRandomValues(new Uint8Array(12));
            const encoder = new TextEncoder();
            const messageBytes = encoder.encode(message);
            const encryptedBuffer = await crypto.subtle.encrypt(
                { name: 'AES-GCM', iv: nonce },
                cryptoKey,
                messageBytes
            );
            return {
                encrypted: arrayBufferToBase64(encryptedBuffer),
                nonce: arrayBufferToBase64(nonce)
            };
        }

        async function decryptWebCrypto(encryptedBase64, nonceBase64) {
            const encryptedBuffer = base64ToArrayBuffer(encryptedBase64);
            const nonce = base64ToArrayBuffer(nonceBase64);
            const decryptedBuffer = await crypto.subtle.decrypt(
                { name: 'AES-GCM', iv: nonce },
                cryptoKey,
                encryptedBuffer
            );
            const decoder = new TextDecoder();
            return decoder.decode(decryptedBuffer);
        }

        // === CIFRADO CON CRYPTOJS (fallback para HTTP) ===
        function importKeyCryptoJS(keyBase64) {
            cryptoKey = keyBase64;
        }

        function encryptCryptoJS(message) {
            // Generar IV aleatorio
            const iv = CryptoJS.lib.WordArray.random(16);
            
            // Convertir clave base64 a WordArray
            const keyWordArray = CryptoJS.enc.Base64.parse(cryptoKey);
            
            // Cifrar con AES-256-CBC (CryptoJS no soporta GCM nativamente)
            const encrypted = CryptoJS.AES.encrypt(message, keyWordArray, {
                iv: iv,
                mode: CryptoJS.mode.CBC,
                padding: CryptoJS.pad.Pkcs7
            });

            return {
                encrypted: encrypted.ciphertext.toString(CryptoJS.enc.Base64),
                nonce: iv.toString(CryptoJS.enc.Base64)
            };
        }

        function decryptCryptoJS(encryptedBase64, nonceBase64) {
            const keyWordArray = CryptoJS.enc.Base64.parse(cryptoKey);
            const iv = CryptoJS.enc.Base64.parse(nonceBase64);
            const ciphertext = CryptoJS.enc.Base64.parse(encryptedBase64);
            
            const decrypted = CryptoJS.AES.decrypt(
                { ciphertext: ciphertext },
                keyWordArray,
                {
                    iv: iv,
                    mode: CryptoJS.mode.CBC,
                    padding: CryptoJS.pad.Pkcs7
                }
            );

            return decrypted.toString(CryptoJS.enc.Utf8);
        }

        // === FUNCIONES UNIFICADAS ===
        async function importKey(keyBase64) {
            try {
                if (useWebCrypto) {
                    await importKeyWebCrypto(keyBase64);
                } else {
                    importKeyCryptoJS(keyBase64);
                }
                addMessage('Sistema', '✅ Clave importada correctamente', 'system');
                document.getElementById('sendButton').disabled = false;
                updateEncryptionInfo();
                return true;
            } catch (error) {
                addMessage('Sistema', '❌ Error importando clave: ' + error.message, 'system');
                return false;
            }
        }

        async function encryptMessage(message) {
            if (useWebCrypto) {
                return await encryptWebCrypto(message);
            } else {
                return encryptCryptoJS(message);
            }
        }

        async function decryptMessage(encryptedBase64, nonceBase64) {
            if (useWebCrypto) {
                return await decryptWebCrypto(encryptedBase64, nonceBase64);
            } else {
                return decryptCryptoJS(encryptedBase64, nonceBase64);
            }
        }

        function updateEncryptionInfo() {
            const method = useWebCrypto ? 'AES-256-GCM (Web Crypto)' : 'AES-256-CBC (CryptoJS)';
            document.getElementById('encryptionInfo').innerHTML = 
                `🔐 Cifrado Activo: <strong>${method}</strong> | Clave: ${currentKeyId ? currentKeyId.substring(0, 12) + '...' : 'N/A'}`;
        }

        // WebSocket
        function connectWebSocket() {
            ws = new WebSocket("wss://" + window.location.host + "/ws/" + username);

            ws.onopen = function() {
                addMessage('Sistema', '🔌 Conectado al servidor', 'system');
                checkWebCryptoAvailability();
            };

            ws.onmessage = async function(event) {
                try {
                    const data = JSON.parse(event.data);
            
                    if (data.type === 'welcome') {
                        addMessage('Sistema', data.message, 'system');
                        
                        if (data.key_base64) {
                            currentKeyId = data.key_id;
                            await importKey(data.key_base64);
                        }
                    }
                    else if (data.type === 'key_rotation') {
                        addMessage('Sistema', '🔄 Rotación de clave detectada', 'warning');
                        currentKeyId = data.key_id;
                        await importKey(data.key_base64);
                    }
                    else if (data.encrypted && data.nonce && data.key_id) {
                        // NO mostrar el mensaje cifrado, solo descifrar y mostrar
                        try {
                            const decrypted = await decryptMessage(data.encrypted, data.nonce);
                        } catch (error) {
                            addMessage('Sistema', '❌ Error descifrando: ' + error.message, 'system');
                        }
                    }
                    else if (data.error) {
                        addMessage('Error', data.error, 'system');
                    }
                } catch (e) {
                    addMessage('Servidor', event.data, 'system');
                }
            };
            
            ws.onclose = function() {
                addMessage('Sistema', '❌ Conexión cerrada', 'system');
                document.getElementById('sendButton').disabled = true;
            };
        }

        async function sendEncryptedMessage() {
            const input = document.getElementById('messageText');
            const message = input.value.trim();
            
            if (!message || !ws || ws.readyState !== WebSocket.OPEN) return;
        
            try {
                // Mostrar mensaje enviado con el username de la URL
                addMessage(username, message, 'encrypted');
                
                const encrypted = await encryptMessage(message);
                
                ws.send(JSON.stringify({
                    ...encrypted,
                    key_id: currentKeyId,
                    timestamp: Date.now()
                }));
                
                input.value = '';
            } catch (error) {
                addMessage('Sistema', '❌ Error cifrando: ' + error.message, 'system');
            }
        }
        
        function addMessage(user, text, type = 'system') {
            const messagesDiv = document.getElementById('messages');
            const messageElement = document.createElement('div');
            messageElement.className = 'message-item ' + type;
            messageElement.innerHTML = `<strong>${user}:</strong> ${text}`;
            messagesDiv.appendChild(messageElement);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        document.getElementById('sendButton').addEventListener('click', sendEncryptedMessage);
        document.getElementById('messageText').addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !document.getElementById('sendButton').disabled) {
                sendEncryptedMessage();
            }
        });

        connectWebSocket();
    </script>
</body>
</html>
    """

    # Reemplazar el placeholder con el username real
    html_content = template.replace("USERNAME_PLACEHOLDER", username)

    return HTMLResponse(content=html_content, status_code=200)


@app.get("/test/crypto-client")
async def test_crypto_client():
    """Cliente específico para testing de cifrado"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Cifrado</title>
        <style>
            body { font-family: Arial; padding: 20px; }
            .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
            .encrypted { background: #e8f5e8; border-left: 4px solid #4caf50; }
            .decrypted { background: #e3f2fd; border-left: 4px solid #2196f3; }
            .error { background: #ffebee; border-left: 4px solid #f44336; }
            input { width: 300px; padding: 8px; margin: 5px; }
            button { padding: 8px 15px; margin: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
        <h2>🔐 Test de Cifrado WebSocket</h2>

        <div>
            <input type="text" id="messageInput" placeholder="Mensaje a enviar">
            <br>
            <button onclick="sendPlain()">📝 Texto Plano</button>
            <button onclick="sendTestEncrypted()">🧪 Cifrado Test</button>
            <button onclick="sendRealEncrypted()">🔐 Cifrado Real</button>
            <button onclick="clearLog()">🗑️ Limpiar</button>
        </div>

        <div id="log" style="margin-top: 20px;"></div>

        <script>
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(protocol + "//" + window.location.host + "/ws/" + username);
            const log = document.getElementById('log');
            let currentKeyId = null;

            function addLog(message, type = '') {
                const div = document.createElement('div');
                div.className = `message ${type}`;
                div.innerHTML = `<strong>[${new Date().toLocaleTimeString()}]</strong> ${message}`;
                log.appendChild(div);
                log.scrollTop = log.scrollHeight;
            }

            ws.onopen = () => addLog("✅ Conectado al servidor", "decrypted");

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'welcome') {
                        currentKeyId = data.current_key_id || data.key_info?.current_key_id;
                        addLog(`🔑 Clave actual del servidor: ${currentKeyId}`, "decrypted");
                    }
                    else if (data.encrypted) {
                        addLog(`🔐 Mensaje cifrado recibido - Key: ${data.key_id}`, "encrypted");
                    }
                    else if (data.error) {
                        addLog(`❌ Error: ${data.error} - ${data.details}`, "error");
                        if (data.available_keys) {
                            addLog(`🔑 Claves disponibles: ${data.available_keys.join(', ')}`, "decrypted");
                        }
                    }
                    else {
                        addLog(`📝 Respuesta: ${JSON.stringify(data)}`, "decrypted");
                    }
                } catch {
                    addLog(`📝 Texto plano: ${event.data}`, "decrypted");
                }
            };

            function sendPlain() {
                const input = document.getElementById('messageInput');
                ws.send(input.value);
                addLog(`📤 Enviado texto plano: "${input.value}"`, "decrypted");
                input.value = '';
            }

            function sendTestEncrypted() {
                const input = document.getElementById('messageInput');
                const messageData = {
                    encrypted: btoa(unescape(encodeURIComponent(input.value))),
                    nonce: btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(12)))),
                    key_id: 'test_key',
                    timestamp: Date.now(),
                    is_test: true
                };
                ws.send(JSON.stringify(messageData));
                addLog(`🧪 Enviado cifrado TEST: "${input.value}"`, "encrypted");
                input.value = '';
            }

            function sendRealEncrypted() {
                const input = document.getElementById('messageInput');
                if (!currentKeyId) {
                    addLog("❌ No hay clave disponible. Espera a que el servidor envíe la clave actual.", "error");
                    return;
                }
                const messageData = {
                    encrypted: btoa(unescape(encodeURIComponent(input.value))),
                    nonce: btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(12)))),
                    key_id: currentKeyId,
                    timestamp: Date.now()
                };
                ws.send(JSON.stringify(messageData));
                addLog(`🔐 Enviado cifrado REAL con clave ${currentKeyId}: "${input.value}"`, "encrypted");
                input.value = '';
            }

            function clearLog() {
                log.innerHTML = '';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.websocket("/monitor/ws")
async def monitor_websocket(websocket: WebSocket):
    """WebSocket para el monitor de mensajes en tiempo real"""
    await websocket.accept()
    monitor_connections.append(websocket)

    print("🖥️ Monitor conectado")

    try:
        # Enviar estado inicial
        await websocket.send_text(json.dumps({
            "type": "status_update",
            "active_count": len(active_connections)
        }))

        # Enviar información de claves
        key_info = crypto_manager.get_key_info()
        await websocket.send_text(json.dumps({
            "type": "key_info",
            "key_info": key_info
        }))

        # Mantener la conexión activa
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        monitor_connections.remove(websocket)
        print("🖥️ Monitor desconectado")


async def notify_monitors(message_type: str, data: dict):
    """Función para notificar a todos los monitores conectados"""
    if not monitor_connections:
        return

    message = json.dumps({
        "type": message_type,
        **data
    })

    # Lista de monitores desconectados para limpiar
    disconnected_monitors = []

    for monitor in monitor_connections:
        try:
            await monitor.send_text(message)
        except:
            disconnected_monitors.append(monitor)

    # Limpiar monitores desconectados
    for monitor in disconnected_monitors:
        if monitor in monitor_connections:
            monitor_connections.remove(monitor)

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    active_connections[username] = websocket

    print(f"✅ Cliente conectado: {username}")

    await notify_monitors("user_connected", {
        "username": username,
        "active_count": len(active_connections)
    })

    try:
        # ENVIAR CLAVE AL CLIENTE
        key_id, key_base64 = crypto_manager.get_current_key_base64()
        await websocket.send_text(json.dumps({
            "type": "welcome",
            "message": "Conexión establecida con cifrado",
            "key_id": key_id,
            "key_base64": key_base64
        }))

        while True:
            data = await websocket.receive_text()
            timestamp = datetime.now().isoformat()

            try:
                message_data = json.loads(data)

                if all(k in message_data for k in ['encrypted', 'nonce', 'key_id']):
                    try:
                        # Intentar descifrado (funciona con ambos tipos)
                        decrypted = crypto_manager.decrypt_message(
                            message_data['encrypted'],
                            message_data['nonce'],
                            message_data['key_id']
                        )

                        print(f"🔐 {username}: {decrypted}")

                        message_history.append({
                            "username": username,
                            "message": decrypted,
                            "timestamp": timestamp,
                            "is_encrypted": True
                        })

                        await notify_monitors("message", {
                            "username": username,
                            "message": decrypted,
                            "timestamp": timestamp,
                            "is_encrypted": True
                        })

                        # Responder cifrado
                        encrypted_response = crypto_manager.encrypt_message(
                            f"✓ {decrypted}"
                        )
                        await websocket.send_text(json.dumps(encrypted_response))

                    except Exception as e:
                        print(f"❌ Error descifrando de {username}: {e}")
                        await websocket.send_text(json.dumps({
                            "error": "Error descifrando mensaje",
                            "details": str(e)
                        }))

            except json.JSONDecodeError:
                print(f"{username}: {data}")

    except WebSocketDisconnect:
        if username in active_connections:
            del active_connections[username]
        print(f"❌ Cliente desconectado: {username}")


@app.get("/messages/history")
async def get_message_history(limit: int = 100):
    """Endpoint para obtener el historial de mensajes"""
    return {
        "messages": message_history[-limit:],
        "total": len(message_history)
    }


@app.post("/broadcast/{sender_username}")
async def broadcast_message(sender_username: str, message: dict):
    """Endpoint para enviar mensajes a todos los clientes conectados"""
    message_text = message.get("message", "")

    if not message_text:
        return {"error": "No se proporcionó mensaje"}

    # Mostrar en consola
    print(f"{sender_username}: {message_text}")

    # Enviar a todos los clientes conectados excepto al remitente
    disconnected_users = []
    for username, websocket in active_connections.items():
        if username != sender_username:
            try:
                # Cifrar mensaje específicamente para cada usuario
                encrypted_message = crypto_manager.encrypt_message(
                    f"{sender_username}: {message_text}"
                )
                await websocket.send_text(json.dumps(encrypted_message))
            except Exception as e:
                print(f"❌ Error enviando mensaje cifrado a {username}: {e}")
                disconnected_users.append(username)

    # Limpiar conexiones desconectadas
    for user in disconnected_users:
        if user in active_connections:
            del active_connections[user]
        print(f"❌ Cliente desconectado (error): {user}")

    return {
        "message": "Mensaje cifrado enviado a todos los clientes",
        "recipients": len(active_connections) - (1 if sender_username in active_connections else 0)
    }


@app.get("/crypto/keys")
async def get_crypto_keys():
    """Endpoint para obtener información de las claves de cifrado"""
    return crypto_manager.get_key_info()


@app.post("/crypto/rotate")
async def rotate_crypto_key():
    """Endpoint para forzar la rotación de claves"""
    crypto_manager._generate_new_key()
    return {
        "message": "Clave rotada manualmente",
        "new_key_id": crypto_manager.current_key_id
    }


@app.get("/test/encryption")
async def test_encryption():
    """Endpoint para testing de cifrado"""
    test_message = "Mensaje de prueba para cifrado"

    # Cifrar un mensaje de ejemplo
    encrypted = crypto_manager.encrypt_message(test_message)

    # Descifrar para verificar
    try:
        decrypted = crypto_manager.decrypt_message(
            encrypted['encrypted'],
            encrypted['nonce'],
            encrypted['key_id']
        )
        status = "✅ CIFRADO FUNCIONANDO"
    except Exception as e:
        status = f"❌ ERROR: {e}"
        decrypted = None

    return {
        "status": status,
        "test_message": test_message,
        "encrypted_data": encrypted,
        "decrypted_message": decrypted,
        "key_info": crypto_manager.get_key_info()
    }


if __name__ == "__main__":
    import socket
    import os

    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    use_ssl = os.path.exists("cert.pem") and os.path.exists("key.pem")
    protocol = "https" if use_ssl else "http"

    print("🚀 Iniciando servidor FastAPI con WebSockets y Cifrado...")

    if use_ssl:
        print(f"📍 Acceso local: https://localhost:8000")
        print(f"🌐 Acceso en red: https://{local_ip}:8000")
        print("🔒 SSL/TLS habilitado - Cifrado completamente funcional")
        print("⚠️  Los navegadores mostrarán advertencia de certificado (es normal)")
        print("\n🔗 Endpoints:")
        print(f"   Cliente: https://localhost:8000/imAClient/{{username}}")
        print(f"   Monitor: https://localhost:8000/monitor")
        print(f"   Testing: https://localhost:8000/test/crypto-client")

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            ssl_keyfile="key.pem",
            ssl_certfile="cert.pem"
        )
    else:
        print(f"📍 Acceso local: http://localhost:8000")
        print(f"🌐 Acceso en red: http://{local_ip}:8000")
        print("⚠️  IMPORTANTE: El cifrado solo funciona en:")
        print("   - http://localhost:8000 (Web Crypto disponible)")
        print("   - https://... (Web Crypto disponible)")
        print(f"   - http://{local_ip}:8000 NO tendrá cifrado funcional")
        print("\n🔗 Endpoints:")
        print(f"   Cliente: http://localhost:8000/imAClient/{{username}}")
        print(f"   Monitor: http://localhost:8000/monitor")
        print(f"   Testing: http://localhost:8000/test/crypto-client")

        uvicorn.run(app, host="0.0.0.0", port=8000)