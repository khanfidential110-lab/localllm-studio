"""
Professional Web UI
====================
Modern, beautiful web interface for LocalLLM Studio.
"""

import json
import time
import sys
import os
from typing import Optional

try:
    from flask import Flask, render_template_string, request, Response, jsonify, send_from_directory
except ImportError:
    Flask = None

# Handle imports for multiple execution contexts:
# 1. Installed package: from localllm_studio.backends import ...
# 2. Running as module: from ..backends import ...
# 3. Running from desktop.py or direct execution: from backends import ...

try:
    # Try absolute imports first (installed package)
    from localllm_studio.backends import LlamaCppBackend, GenerationConfig
    from localllm_studio.backends.base import InferenceBackend
    from localllm_studio.models import GGUF_MODELS, get_models_that_fit, get_best_model_for_memory, ModelCategory
    from localllm_studio.utils import detect_hardware, get_ram_info
except ImportError:
    try:
        # Try relative imports (running as package module)
        from ..backends import LlamaCppBackend, GenerationConfig
        from ..backends.base import InferenceBackend
        from ..models import GGUF_MODELS, get_models_that_fit, get_best_model_for_memory, ModelCategory
        from ..utils import detect_hardware, get_ram_info
    except ImportError:
        # Direct imports (running from desktop.py or script)
        from backends import LlamaCppBackend, GenerationConfig
        from backends.base import InferenceBackend
        from models import GGUF_MODELS, get_models_that_fit, get_best_model_for_memory, ModelCategory
        from utils import detect_hardware, get_ram_info


# Beautiful HTML template with modern glassmorphism design
WEB_UI_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LocalLLM Studio</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --secondary: #8b5cf6;
            --accent: #06b6d4;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --bg-dark: #0f172a;
            --bg-card: rgba(30, 41, 59, 0.8);
            --bg-input: rgba(15, 23, 42, 0.6);
            --text: #f1f5f9;
            --text-muted: #94a3b8;
            --bg-input: rgba(15, 23, 42, 0.6);
            --text: #f1f5f9;
            --text-muted: #94a3b8;
            --border: rgba(148, 163, 184, 0.1);
        }
        
        .btn-danger {
            background: linear-gradient(135deg, var(--error), #dc2626) !important;
            box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3) !important;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
            min-height: 100vh;
            color: var(--text);
            overflow-x: hidden;
        }
        
        /* Animated background */
        .bg-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            opacity: 0.4;
        }
        
        .bg-animation::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, var(--primary) 0%, transparent 50%);
            animation: pulse 15s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.3; }
            50% { transform: translate(20%, 20%) scale(1.2); opacity: 0.5; }
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Header */
        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px 30px;
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            border: 1px solid var(--border);
            margin-bottom: 24px;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .logo-icon {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        
        .logo h1 {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--text), var(--accent));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .logo span {
            font-size: 0.75rem;
            color: var(--text-muted);
            font-weight: 400;
        }
        
        .header-status {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .status-badge {
            padding: 8px 16px;
            border-radius: 100px;
            font-size: 0.85rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .status-badge.connected {
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        
        .status-badge.disconnected {
            background: rgba(239, 68, 68, 0.15);
            color: var(--error);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: blink 2s infinite;
        }
        
        .status-badge.connected .status-dot { background: var(--success); }
        .status-badge.disconnected .status-dot { background: var(--error); }
        
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        
        /* Main Layout */
        .main-grid {
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 24px;
            min-height: calc(100vh - 180px);
        }
        
        @media (max-width: 900px) {
            .main-grid { grid-template-columns: 1fr; }
            .sidebar { order: 2; }
            .chat-container { order: 1; min-height: 60vh; }
            .sidebar.collapsed { display: none; }
        }
        
        /* Mobile toggle */
        .mobile-toggle {
            display: none;
            position: fixed;
            bottom: 20px;
            left: 20px;
            z-index: 100;
            padding: 14px 20px;
            border-radius: 30px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            border: none;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 10px 30px rgba(99, 102, 241, 0.4);
        }
        @media (max-width: 900px) {
            .mobile-toggle { display: flex; align-items: center; gap: 8px; }
        }
        
        /* Memory warning */
        .memory-warning {
            background: rgba(245, 158, 11, 0.15);
            border: 1px solid rgba(245, 158, 11, 0.3);
            color: var(--warning);
            padding: 10px 12px;
            border-radius: 8px;
            font-size: 0.8rem;
            margin-top: 10px;
        }
        
        .memory-critical {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: var(--error);
        }
        
        /* Sidebar */
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border-radius: 16px;
            border: 1px solid var(--border);
            padding: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }
        
        .card-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 16px;
            font-weight: 600;
            color: var(--text);
        }
        
        .card-header .icon {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
        }
        
        /* Hardware Info */
        .hw-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        
        .hw-item {
            background: var(--bg-input);
            border-radius: 10px;
            padding: 12px;
        }
        
        .hw-item label {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .hw-item .value {
            font-size: 1rem;
            font-weight: 600;
            margin-top: 4px;
        }
        
        .hw-item.full { grid-column: span 2; }
        
        /* Form Elements */
        select, input[type="text"], textarea {
            width: 100%;
            padding: 12px 16px;
            border-radius: 10px;
            border: 1px solid var(--border);
            background: var(--bg-input);
            color: var(--text);
            font-size: 0.95rem;
            font-family: inherit;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        
        select:focus, input:focus, textarea:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
        }
        
        select { cursor: pointer; }
        
        .btn {
            padding: 12px 24px;
            border-radius: 10px;
            border: none;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(99, 102, 241, 0.4);
        }
        
        .btn-primary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .btn-secondary {
            background: var(--bg-input);
            color: var(--text);
            border: 1px solid var(--border);
        }
        
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.1);
        }
        
        .btn-icon {
            width: 40px;
            height: 40px;
            padding: 0;
            border-radius: 10px;
        }
        
        .btn-full { width: 100%; }
        
        /* Slider */
        .slider-container {
            margin-bottom: 16px;
        }
        
        .slider-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 0.9rem;
        }
        
        .slider-value {
            color: var(--accent);
            font-weight: 600;
        }
        
        input[type="range"] {
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: var(--bg-input);
            appearance: none;
            cursor: pointer;
        }
        
        input[type="range"]::-webkit-slider-thumb {
            appearance: none;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            cursor: pointer;
            border: 2px solid white;
        }
        
        /* Chat Area */
        .chat-container {
            display: flex;
            flex-direction: column;
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            border: 1px solid var(--border);
            overflow: hidden;
        }
        
        .chat-header {
            padding: 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .chat-title {
            font-size: 1.1rem;
            font-weight: 600;
        }
        
        .chat-actions {
            display: flex;
            gap: 8px;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            min-height: 400px;
            max-height: calc(100vh - 400px);
        }
        
        .message {
            margin-bottom: 20px;
            display: flex;
            gap: 12px;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user { flex-direction: row-reverse; }
        
        .avatar {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            flex-shrink: 0;
        }
        
        .message.user .avatar {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
        }
        
        .message.assistant .avatar {
            background: linear-gradient(135deg, var(--accent), var(--success));
        }
        
        .message-content {
            max-width: 80%;
            padding: 14px 18px;
            border-radius: 16px;
            line-height: 1.6;
        }
        
        .message.user .message-content {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-bottom-right-radius: 4px;
        }
        
        .message.assistant .message-content {
            background: var(--bg-input);
            border-bottom-left-radius: 4px;
        }
        
        .message-stats {
            font-size: 0.75rem;
            color: var(--accent);
            margin-top: 8px;
            font-family: 'SF Mono', monospace;
        }
        
        /* Typing indicator */
        .typing-indicator {
            display: flex;
            gap: 4px;
            padding: 14px 18px;
        }
        
        .typing-indicator span {
            width: 8px;
            height: 8px;
            background: var(--text-muted);
            border-radius: 50%;
            animation: typing 1.4s infinite;
        }
        
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
        
        @keyframes typing {
            0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
            30% { transform: translateY(-6px); opacity: 1; }
        }
        
        /* Input Area */
        .chat-input {
            padding: 20px;
            border-top: 1px solid var(--border);
            display: flex;
            gap: 12px;
        }
        
        .chat-input textarea {
            flex: 1;
            resize: none;
            min-height: 50px;
            max-height: 150px;
        }
        
        /* Code blocks */
        pre {
            background: rgba(0, 0, 0, 0.3);
            padding: 12px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 8px 0;
        }
        
        code {
            font-family: 'SF Mono', 'Fira Code', monospace;
            font-size: 0.9em;
        }
        
        /* Loading spinner */
        .spinner {
            width: 20px;
            height: 20px;
            border: 2px solid transparent;
            border-top-color: currentColor;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Toast notifications */
        .toast-container {
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 1000;
        }
        
        .toast {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border-radius: 12px;
            padding: 16px 20px;
            margin-top: 12px;
            border: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 12px;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        .toast.success { border-left: 4px solid var(--success); }
        .toast.error { border-left: 4px solid var(--error); }
        .toast.info { border-left: 4px solid var(--primary); }
        
        /* Welcome screen */
        .welcome {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            text-align: center;
            padding: 40px;
        }
        
        .welcome-icon {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            margin-bottom: 24px;
        }
        
        .welcome h2 {
            font-size: 1.5rem;
            margin-bottom: 12px;
        }
        
        .welcome p {
            color: var(--text-muted);
            max-width: 400px;
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>
    
    <div class="container">
        <header>
            <div class="logo">
                <div class="logo-icon">🚀</div>
                <div>
                    <h1>LocalLLM Studio</h1>
                    <span>v1.0.0 · Cross-Platform LLM</span>
                </div>
            </div>
            <div class="header-status">
                <div class="status-badge" id="connection-status">
                    <span class="status-dot"></span>
                    <span id="status-text">No Model</span>
                </div>
            </div>
        </header>
        
        <div class="main-grid">
            <aside class="sidebar" id="sidebar">
                <!-- Hardware Info -->
                <div class="card">
                    <div class="card-header">
                        <div class="icon">💻</div>
                        Hardware
                    </div>
                    <div class="hw-grid">
                        <div class="hw-item">
                            <label>Platform</label>
                            <div class="value">{{ hardware.platform }} {{ hardware.platform_version }}</div>
                        </div>
                        <div class="hw-item">
                            <label>CPU</label>
                            <div class="value" title="{{ hardware.cpu }}">{{ hardware.cpu[:12] }}.. ({{ hardware.cpu_cores }}C)</div>
                        </div>
                        <div class="hw-item">
                            <label>RAM</label>
                            <div class="value">{{ hardware.ram_gb }} GB</div>
                        </div>
                        <div class="hw-item">
                            <label>GPU</label>
                            <div class="value" title="{{ hardware.gpu_name }}">{{ hardware.gpu_name[:10] }}.. ({{ hardware.gpu_vram }}GB)</div>
                        </div>
                        <div class="hw-item full">
                            <label>Available Memory</label>
                            <div class="value" style="color: var(--accent);" id="ram-available">{{ hardware.available_gb }} GB</div>
                        </div>
                    </div>
                     {% if hardware.available_gb < 2.0 %}
                    <div class="memory-warning {{ 'memory-critical' if hardware.available_gb < 1.0 else '' }}">
                        ⚠️ Low memory! Close other apps (Chrome/IDE) before loading large models.
                    </div>
                    {% endif %}
                </div>
                
                <!-- Model Selection -->
                <div class="card">
                    <div class="card-header">
                        <div class="icon">📦</div>
                        Model
                    </div>
                    <select id="model-select" style="margin-bottom: 12px;">
                        {% for model in models %}
                        <option value="{{ model.repo }}" {{ 'selected' if model.recommended else '' }}>
                            {{ '✅' if model.fits else '⚠️' }} {{ model.name }} ({{ model.size_gb }}GB)
                        </option>
                        {% endfor %}
                    </select>
                    <button class="btn btn-primary btn-full" id="load-btn" onclick="loadModel()">
                        <span id="load-btn-text">Load Model</span>
                    </button>
                    <div id="model-status" style="margin-top: 12px; font-size: 0.85rem; color: var(--text-muted);"></div>
                </div>
                
                <!-- Settings -->
                <div class="card">
                    <div class="card-header">
                        <div class="icon">⚙️</div>
                        Settings
                    </div>
                    <div class="slider-container">
                        <div class="slider-label">
                            <span>Temperature</span>
                            <span class="slider-value" id="temp-value">0.7</span>
                        </div>
                        <input type="range" id="temperature" min="0" max="2" step="0.1" value="0.7"
                               oninput="document.getElementById('temp-value').textContent = this.value">
                    </div>
                    <div class="slider-container">
                        <div class="slider-label">
                            <span>Max Tokens</span>
                            <span class="slider-value" id="tokens-value">2048</span>
                        </div>
                        <input type="range" id="max-tokens" min="256" max="8192" step="256" value="2048"
                               oninput="document.getElementById('tokens-value').textContent = this.value">
                    </div>
                    <select id="system-preset" style="margin-top: 8px;" onchange="updateSystemPrompt()">
                        <option value="default">Default Assistant</option>
                        <option value="coding">Coding Expert</option>
                        <option value="creative">Creative Writer</option>
                        <option value="reasoning">Analyst / Reasoning</option>
                    </select>
                </div>
            </aside>
            
            <!-- Chat Area -->
            <main class="chat-container">
                <div class="chat-header">
                    <div class="chat-title">💬 Chat</div>
                    <div class="chat-actions">
                        <button class="btn btn-secondary btn-icon" onclick="clearChat()" title="Clear">🗑️</button>
                        <button class="btn btn-secondary btn-icon" onclick="exportChat()" title="Export">📥</button>
                    </div>
                </div>
                
                <div class="chat-messages" id="chat-messages">
                    <div class="welcome">
                        <div class="welcome-icon">🚀</div>
                        <h2>Welcome to LocalLLM Studio</h2>
                        <p>Run AI models privately on your device. No internet required once downloaded.</p>
                        <div style="margin-top: 20px; display: flex; flex-direction: column; gap: 12px; align-items: center;">
                            <button class="btn btn-primary" onclick="document.getElementById('load-btn').click(); document.getElementById('load-btn').scrollIntoView({behavior:'smooth'});">
                                👆 Load a Model to Start
                            </button>
                            <span style="font-size: 0.85rem; color: var(--text-muted);">Your data never leaves your computer</span>
                        </div>
                    </div>
                </div>
                
                <div class="chat-input">
                    <textarea id="user-input" placeholder="Type your message... (Shift+Enter for new line)"
                              onkeydown="handleKeyDown(event)"></textarea>
                    <button class="btn btn-primary" id="send-btn" onclick="sendMessage()" disabled>
                        Send →
                    </button>
                </div>
            </main>
        </div>
    </div>
    
    <div class="toast-container" id="toast-container"></div>
    
    <button class="mobile-toggle" onclick="toggleSidebar()">
        ⚙️ Menu
    </button>
    
    <script>
        const SYSTEM_PROMPTS = {
            default: "You are a helpful AI assistant.",
            coding: "You are an expert programmer. Write clean, efficient code with clear explanations.",
            creative: "You are a creative writer. Be imaginative, engaging, and expressive.",
            reasoning: "You are an analytical thinker. Break down problems step by step with clear logic."
        };
        
        let systemPrompt = SYSTEM_PROMPTS.default;
        let isGenerating = false;
        let modelLoaded = false;
        
        function updateSystemPrompt() {
            const preset = document.getElementById('system-preset').value;
            systemPrompt = SYSTEM_PROMPTS[preset] || SYSTEM_PROMPTS.default;
        }
        
        async function updateHardwareStats() {
            try {
                const response = await fetch('/api/hardware');
                if (response.ok) {
                    const data = await response.json();
                    const el = document.getElementById('ram-available');
                    if (el) {
                        el.textContent = data.available_gb + ' GB';
                        if (data.available_gb < 2.0) {
                            el.style.color = 'var(--warning)';
                        } else {
                            el.style.color = 'var(--accent)';
                        }
                    }
                }
            } catch (e) {
                console.error("Failed to fetch hardware stats", e);
            }
        }
        
        // Poll every 3 seconds
        setInterval(updateHardwareStats, 3000);
        
        function showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = message;
            container.appendChild(toast);
            setTimeout(() => toast.remove(), 4000);
        }
        
        let abortController = null;
        
        async function stopLoading() {
            if (abortController) {
                abortController.abort();
                abortController = null;
            }
            
            try {
                await fetch('/api/stop_load', {method: 'POST'});
                showToast('🛑 Operation cancelled', 'info');
            } catch (e) {
                console.error(e);
            }
            
            // Reset UI
            const btn = document.getElementById('load-btn');
            const btnText = document.getElementById('load-btn-text');
            const status = document.getElementById('model-status');
            
            btn.onclick = loadModel;
            btn.classList.remove('btn-danger');
            btn.disabled = false;
            btnText.innerText = "Load Model";
            status.textContent = 'Cancelled.';
            status.style.color = 'var(--text-muted)';
        }

        async function loadModel() {
            const btn = document.getElementById('load-btn');
            const btnText = document.getElementById('load-btn-text');
            const status = document.getElementById('model-status');
            const model = document.getElementById('model-select').value;
            
            if (!model) return;
            
            // Change button to Stop
            btn.onclick = stopLoading;
            btn.classList.add('btn-danger');
            // btn.disabled = true; // Don't disable, allow clicking to stop
            
            // Retain original text but show spinner
            const originalText = btnText.innerText;
            btnText.innerHTML = '<span class="status-dot" style="background:white"></span> Stop';
            
            status.textContent = 'Initializing...';
            status.style.color = 'var(--text-muted)';
            
            abortController = new AbortController();
            
            try {
                const response = await fetch('/api/load', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({model: model}),
                    signal: abortController.signal
                });
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    const {value, done} = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.status) {
                                status.textContent = data.status;
                                if (data.status.includes('Downloading')) {
                                    status.style.color = 'var(--warning)';
                                } else {
                                    status.style.color = 'var(--text)';
                                }
                            }
                            
                            if (data.success) {
                                status.textContent = '✅ ' + data.message;
                                status.style.color = 'var(--success)';
                                document.getElementById('send-btn').disabled = false;
                                modelLoaded = true;
                                
                                // Update status badge
                                const badge = document.getElementById('connection-status');
                                badge.className = 'status-badge connected';
                                document.getElementById('status-text').textContent = 'Model Ready';
                                
                                showToast('Model loaded successfully!', 'success');
                                
                                // Reset button to Load (or maybe Unload?)
                                btn.onclick = loadModel;
                                btn.classList.remove('btn-danger');
                                btnText.innerText = "Load Model";
                                
                                // Clear welcome
                                const messages = document.getElementById('chat-messages');
                                const welcome = messages.querySelector('.welcome');
                                if (welcome) welcome.remove();
                            }
                            
                            if (data.error) {
                                if (data.error.includes('cancelled')) {
                                     status.textContent = '🛑 Cancelled';
                                     status.style.color = 'var(--warning)';
                                } else {
                                     status.textContent = '❌ ' + data.error;
                                     status.style.color = 'var(--error)';
                                     showToast(data.error, 'error');
                                }
                            }
                        }
                    }
                }
            } catch (error) {
                if (error.name === 'AbortError') {
                    // Handled in stopLoading
                } else {
                    status.textContent = '❌ Connection error';
                    console.error(error);
                }
            } finally {
                // Ensure button reset if not successful or cancelled
                if (!modelLoaded && btnText.innerText === 'Stop') {
                     btn.onclick = loadModel;
                     btn.classList.remove('btn-danger');
                     btnText.innerText = "Load Model";
                }
            }
        }
        
        function addMessage(role, content, stats = '') {
            const messages = document.getElementById('chat-messages');
            const div = document.createElement('div');
            div.className = `message ${role}`;
            
            const avatar = role === 'user' ? '👤' : '🤖';
            
            div.innerHTML = `
                <div class="avatar">${avatar}</div>
                <div class="message-content">
                    ${formatContent(content)}
                    ${stats ? `<div class="message-stats">${stats}</div>` : ''}
                </div>
            `;
            
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
            return div;
        }
        
        function formatContent(text) {
            // Basic markdown-like formatting
            return text
                .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
                .replace(/`([^`]+)`/g, '<code>$1</code>')
                .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
                .replace(/\\n/g, '<br>');
        }
        
        function handleKeyDown(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }
        
        async function sendMessage() {
            if (isGenerating) return;
            
            if (!modelLoaded) {
                showToast('⚠️ Please load a model first!', 'error');
                // Highlight load button
                const loadBtn = document.getElementById('load-btn');
                loadBtn.style.boxShadow = '0 0 0 4px rgba(239, 68, 68, 0.4)';
                setTimeout(() => loadBtn.style.boxShadow = '', 2000);
                
                // On mobile, show sidebar
                if (window.innerWidth <= 900) {
                     document.getElementById('sidebar').classList.remove('collapsed');
                }
                return;
            }
            
            const input = document.getElementById('user-input');
            const message = input.value.trim();
            if (!message) return;
            
            isGenerating = true;
            input.value = '';
            document.getElementById('send-btn').disabled = true;
            
            // Add user message
            addMessage('user', message);
            
            // Add typing indicator
            const messages = document.getElementById('chat-messages');
            const typing = document.createElement('div');
            typing.className = 'message assistant';
            typing.id = 'typing-msg';
            typing.innerHTML = `
                <div class="avatar">🤖</div>
                <div class="message-content">
                    <div class="typing-indicator">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            `;
            messages.appendChild(typing);
            messages.scrollTop = messages.scrollHeight;
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: message,
                        system_prompt: systemPrompt,
                        temperature: parseFloat(document.getElementById('temperature').value),
                        max_tokens: parseInt(document.getElementById('max-tokens').value)
                    })
                });
                
                // Remove typing indicator
                document.getElementById('typing-msg')?.remove();
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let fullText = '';
                let lastStats = '';
                let assistantDiv = null;
                
                while (true) {
                    const {value, done} = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.text) fullText += data.text;
                                if (data.stats) lastStats = data.stats;
                                if (data.error) fullText = '❌ ' + data.error;
                                
                                if (!assistantDiv) {
                                    assistantDiv = addMessage('assistant', fullText + '▌');
                                } else {
                                    const content = assistantDiv.querySelector('.message-content');
                                    content.innerHTML = formatContent(fullText) + '▌';
                                }
                            } catch(e) {}
                        }
                    }
                    messages.scrollTop = messages.scrollHeight;
                }
                
                // Final update
                if (assistantDiv) {
                    const content = assistantDiv.querySelector('.message-content');
                    content.innerHTML = formatContent(fullText);
                    if (lastStats) {
                        content.innerHTML += `<div class="message-stats">${lastStats}</div>`;
                    }
                }
                
            } catch (error) {
                document.getElementById('typing-msg')?.remove();
                addMessage('assistant', '❌ Error: ' + error.message);
            }
            
            isGenerating = false;
            document.getElementById('send-btn').disabled = false;
            input.focus();
        }
        
        function clearChat() {
            const messages = document.getElementById('chat-messages');
            messages.innerHTML = '';
            if (!modelLoaded) {
                messages.innerHTML = `
                    <div class="welcome">
                        <div class="welcome-icon">🚀</div>
                        <h2>Welcome to LocalLLM Studio</h2>
                        <p>Select and load a model from the sidebar to start chatting.</p>
                    </div>
                `;
            }
        }
        
        function exportChat() {
            const messages = document.querySelectorAll('.message');
            let text = 'LocalLLM Studio - Chat Export\\n\\n';
            messages.forEach(msg => {
                const role = msg.classList.contains('user') ? 'You' : 'Assistant';
                const content = msg.querySelector('.message-content').textContent;
                text += `${role}:\\n${content}\\n\\n`;
            });
            
            const blob = new Blob([text], {type: 'text/plain'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'chat-export.txt';
            a.click();
        }
        
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            sidebar.classList.toggle('collapsed');
        }
        
        // Auto-collapse sidebar on mobile on load
        if (window.innerWidth <= 900) {
            document.getElementById('sidebar').classList.add('collapsed');
        }
    </script>
</body>
</html>
'''


class WebUI:
    """Professional Web UI for LocalLLM Studio."""
    
    def __init__(self, backend: InferenceBackend = None):
        if Flask is None:
            raise ImportError("Flask not installed. pip install flask")
        
        self.app = Flask(__name__)
        self.backend = backend or LlamaCppBackend()
        self.hardware = detect_hardware()
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up web routes."""
        
        @self.app.route('/')
        def index():
            hw = self.hardware
            available_gb = max(hw.available_ram_gb, hw.gpu.vram_gb)
            
            models_data = []
            best = get_best_model_for_memory(available_gb)
            
            for m in GGUF_MODELS:
                # Check cache status if backend supports it
                is_cached = False
                if hasattr(self.backend, 'is_model_cached'):
                    is_cached = self.backend.is_model_cached(m.repo_id)
                    
                models_data.append({
                    "repo": m.repo_id,
                    "name": m.name + (" (💾 Local)" if is_cached else " (☁️ Download)"),
                    "size_gb": m.size_gb,
                    "fits": m.fits_memory(available_gb),
                    "recommended": m.repo_id == best.repo_id if best else False,
                    "cached": is_cached
                })
            
            hw_data = {
                "platform": hw.platform.value.capitalize(),
                "platform_version": hw.platform_version,
                "cpu": hw.cpu_brand,
                "cpu_cores": hw.cpu_cores,
                "ram_gb": hw.ram_gb,
                "available_gb": round(available_gb, 1),
                "gpu_name": hw.gpu.name,
                "gpu_vram": hw.gpu.vram_gb,
                "is_apple": hw.platform.value == "macos"
            }
            
            return render_template_string(WEB_UI_TEMPLATE, hardware=hw_data, models=models_data)
            
        @self.app.route('/api/hardware')
        def hardware_stats():
            try:
                ram, available = get_ram_info()
                return jsonify({
                    "ram_gb": ram,
                    "available_gb": available
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/load', methods=['POST'])
        def load_model():
            data = request.json
            model_repo = data.get('model')
            
            def generate():
                import queue
                import threading
                
                q = queue.Queue()
                
                def progress_callback(status, progress):
                    q.put({"status": status, "progress": progress})
                    
                def worker():
                    try:
                        if self.backend.is_loaded:
                            self.backend.unload_model()
                        
                        # Check for callback support
                        if hasattr(self.backend, 'load_model') and 'progress_callback' in self.backend.load_model.__code__.co_varnames:
                            self.backend.load_model(model_repo, n_ctx=4096, n_gpu_layers=-1, progress_callback=progress_callback)
                        else:
                            self.backend.load_model(model_repo, n_ctx=4096, n_gpu_layers=-1)
                            
                        q.put({"success": True, "message": f"Loaded {self.backend.model_info.name}"})
                    except Exception as e:
                        q.put({"error": str(e), "success": False})
                    finally:
                        q.put(None)  # Sentinel
                        
                t = threading.Thread(target=worker)
                t.start()
                
                while True:
                    item = q.get()
                    if item is None:
                        break
                    yield f"data: {json.dumps(item)}\n\n"
                    
            return Response(generate(), mimetype='text/event-stream')

        @self.app.route('/api/stop_load', methods=['POST'])
        def stop_load():
            if hasattr(self.backend, 'cancel_loading'):
                self.backend.cancel_loading()
            return jsonify({"success": True})

        @self.app.route('/api/chat', methods=['POST'])
        def chat():
            data = request.json
            message = data.get('message', '')
            system_prompt = data.get('system_prompt', 'You are a helpful assistant.')
            temperature = float(data.get('temperature', 0.7))
            max_tokens = int(data.get('max_tokens', 2048))
            
            def generate():
                if not self.backend.is_loaded:
                    yield f"data: {json.dumps({'error': 'No model loaded'})}\n\n"
                    return
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ]
                
                config = GenerationConfig(
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True,
                )
                
                start_time = time.perf_counter()
                tokens = 0
                
                try:
                    for result in self.backend.chat(messages, config):
                        tokens += 1
                        elapsed = time.perf_counter() - start_time
                        tps = tokens / elapsed if elapsed > 0 else 0
                        
                        yield f"data: {json.dumps({'text': result.text, 'stats': f'{tokens} tok · {elapsed:.1f}s · {tps:.1f} tok/s'})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return Response(generate(), mimetype='text/event-stream')
        
        @self.app.route('/api/health')
        def health():
            return jsonify({
                "status": "ok",
                "model_loaded": self.backend.is_loaded,
                "model": self.backend.model_info.name if self.backend.model_info else None   
            })
    
    def run(self, host: str = "0.0.0.0", port: int = 7860):
        """Run the web UI."""
        print(f"\n{'=' * 60}")
        print("🚀 LocalLLM Studio - Web UI")
        print(f"{'=' * 60}")
        print(f"\n🌐 Open in browser: http://localhost:{port}")
        print("   Press Ctrl+C to stop\n")
        
        self.app.run(host=host, port=port, debug=False, threaded=True)


def run_web_ui(backend: InferenceBackend = None, port: int = 7860):
    """Launch the web UI."""
    ui = WebUI(backend)
    ui.run(port=port)
