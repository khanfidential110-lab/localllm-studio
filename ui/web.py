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


# Beautiful HTML template with modern Google-style design
WEB_UI_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LocalLLM Studio</title>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Roboto:wght@400;500&display=swap" rel="stylesheet">
    <!-- Material Symbols -->
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
    <style>
        :root {
            /* Google Color Palette */
            --google-blue: #1a73e8;
            --google-blue-hover: #1557b0;
            --google-green: #1e8e3e;
            --google-yellow: #f9ab00;
            --google-red: #d93025;
            --google-gray: #5f6368;

            /* Surface Colors (Light Mode) */
            --surface: #ffffff;
            --surface-variant: #f8f9fa;
            --surface-hover: #f1f3f4;
            --on-surface: #202124;
            --on-surface-variant: #5f6368;
            --outline: #dadce0;

            /* Component Tokens */
            --radius-pill: 9999px;
            --radius-2xl: 1.5rem; /* 24px */
            --radius-xl: 1rem;    /* 16px */
            --radius-lg: 0.75rem; /* 12px */

            --shadow-card: 0 1px 2px 0 rgba(60, 64, 67, 0.3), 0 1px 3px 1px rgba(60, 64, 67, 0.15);
            --shadow-card-hover: 0 1px 3px 0 rgba(60, 64, 67, 0.3), 0 4px 8px 3px rgba(60, 64, 67, 0.15);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Google Sans', 'Roboto', sans-serif;
            background: var(--surface);
            color: var(--on-surface);
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            -webkit-font-smoothing: antialiased;
        }

        /* Material Icon Helper */
        .icon {
            font-family: 'Material Symbols Rounded';
            font-weight: normal;
            font-style: normal;
            font-size: 24px;
            line-height: 1;
            letter-spacing: normal;
            display: inline-block;
            white-space: nowrap;
            word-wrap: normal;
            direction: ltr;
        }
        .icon-filled { font-variation-settings: 'FILL' 1; }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            height: 40px;
            padding: 0 24px;
            border-radius: var(--radius-pill);
            font-family: 'Google Sans', sans-serif;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
            outline: none;
            white-space: nowrap;
        }

        .btn-primary {
            background-color: var(--google-blue);
            color: white;
            box-shadow: var(--shadow-card);
        }
        .btn-primary:hover {
            background-color: var(--google-blue-hover);
            box-shadow: var(--shadow-card-hover);
            transform: translateY(-1px);
        }
        .btn-primary:active { transform: translateY(0); box-shadow: none; }
        .btn-primary:disabled { background-color: var(--outline); cursor: not-allowed; box-shadow: none; }

        .btn-secondary {
            background-color: var(--surface);
            color: var(--google-blue);
            border: 1px solid var(--outline);
        }
        .btn-secondary:hover {
            background-color: var(--surface-hover);
            border-color: rgba(26, 115, 232, 0.3);
        }

        .btn-danger {
            background-color: #fce8e6;
            color: var(--google-red);
        }
        .btn-danger:hover { background-color: #fad2cf; }

        .btn-icon { width: 40px; padding: 0; border-radius: 50%; }

        /* Inputs */
        .input-group { margin-bottom: 16px; }
        .input-label {
            display: block;
            font-size: 12px;
            font-weight: 500;
            color: var(--on-surface-variant);
            margin-bottom: 6px;
            margin-left: 4px;
        }

        select, input, textarea {
            width: 100%;
            padding: 10px 16px;
            border-radius: 8px; /* Slightly squarer than full pills for inputs */
            border: 1px solid var(--outline);
            background: var(--surface);
            color: var(--on-surface);
            font-family: inherit;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }
        select:focus, input:focus, textarea:focus {
            border-color: var(--google-blue);
            border-width: 2px;
            padding: 9px 15px; /* Adjust for border width */
        }

        /* Layout */
        .app-container {
            display: flex;
            height: 100vh;
            width: 100vw;
            background: var(--surface-variant);
        }

        /* Sidebar */
        .sidebar {
            width: 300px;
            background: var(--surface);
            border-right: 1px solid var(--outline);
            display: flex;
            flex-direction: column;
            padding: 24px;
            overflow-y: auto;
            flex-shrink: 0;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 32px;
            padding-left: 8px;
        }
        .logo img { width: 32px; height: 32px; }
        .logo h1 { font-size: 20px; font-weight: 400; color: var(--on-surface); }

        .card {
            background: var(--surface);
            border: 1px solid var(--outline);
            border-radius: var(--radius-xl);
            padding: 20px;
            margin-bottom: 16px;
            /* No shadow on cards inside sidebar to keep it flat/clean */
        }
        .card h2 {
            font-size: 14px;
            font-weight: 500;
            color: var(--on-surface-variant);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Hardware Stats */
        .stat-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 13px;
        }
        .stat-label { color: var(--on-surface-variant); }
        .stat-value { font-weight: 500; }

        /* Main Chat Area */
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            position: relative;
            background: var(--surface);
            border-radius: var(--radius-2xl) 0 0 var(--radius-2xl); /* Rounded top-left corner */
            margin: 12px 12px 12px 0; /* Float effect */
            overflow: hidden;
            box-shadow: -2px 0 10px rgba(0,0,0,0.02);
            border: 1px solid var(--outline);
        }

        .chat-header {
            height: 64px;
            border-bottom: 1px solid var(--outline);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 24px;
            background: rgba(255,255,255,0.9);
            backdrop-filter: blur(10px);
            z-index: 10;
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 40px;
            display: flex;
            flex-direction: column;
            gap: 24px;
            scroll-behavior: smooth;
        }

        .message {
            display: flex;
            gap: 16px;
            max-width: 800px;
            margin: 0 auto;
            width: 100%;
            animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        .message.user { flex-direction: row-reverse; }

        .avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            font-size: 14px;
            font-weight: 500;
        }
        .message.user .avatar { background: var(--google-blue); color: white; }
        .message.assistant .avatar { background: var(--google-green); color: white; } /* Local AI is Green */

        .bubble {
            padding: 16px 20px;
            border-radius: 18px;
            font-size: 15px;
            line-height: 1.6;
            position: relative;
            max-width: 80%;
        }
        .message.user .bubble {
            background: #e8f0fe; /* Light Blue */
            color: #174ea6;      /* Dark Blue text */
            border-top-right-radius: 4px;
        }
        .message.assistant .bubble {
            background: var(--surface-variant);
            color: var(--on-surface);
            border-top-left-radius: 4px;
        }

        .bubble pre {
            background: #202124;
            color: #e8eaed;
            padding: 12px;
            border-radius: 12px;
            overflow-x: auto;
            margin: 10px 0;
            font-family: 'Roboto Mono', monospace;
            font-size: 13px;
        }

        /* Input Area */
        .chat-input-area {
            padding: 24px;
            background: var(--surface);
            border-top: 1px solid var(--outline);
            max-width: 900px;
            margin: 0 auto;
            width: 100%;
        }

        .input-box {
            background: var(--surface-variant);
            border-radius: 24px; /* Fully rounded input */
            padding: 8px 8px 8px 20px;
            display: flex;
            align-items: flex-end;
            transition:  box-shadow 0.2s;
            border: 1px solid transparent;
        }
        .input-box:focus-within {
            background: var(--surface);
            box-shadow: var(--shadow-card-hover);
            border-color: var(--outline);
        }

        .input-box textarea {
            background: transparent;
            border: none;
            padding: 12px 0;
            max-height: 200px;
            resize: none;
            box-shadow: none; /* Override default input focus */
        }
        .input-box textarea:focus { border: none; padding: 12px 0; }

        /* Range Sliders */
        input[type=range] {
            -webkit-appearance: none;
            width: 100%;
            background: transparent;
            border: none;
            padding: 0;
        }
        input[type=range]::-webkit-slider-thumb {
            -webkit-appearance: none;
            height: 16px;
            width: 16px;
            border-radius: 50%;
            background: var(--google-blue);
            cursor: pointer;
            margin-top: -6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        }
        input[type=range]::-webkit-slider-runnable-track {
            width: 100%;
            height: 4px;
            cursor: pointer;
            background: #d1e3f6; /* Light blue track */
            border-radius: 2px;
        }

        /* Welcome Screen */
        .welcome-screen {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            text-align: center;
            padding: 40px;
            color: var(--on-surface-variant);
        }
        .welcome-icon {
            font-size: 64px;
            margin-bottom: 24px;
            color: var(--google-blue);
        }

    </style>
</head>
<body>
    <div class="app-container">
        <!-- Sidebar -->
        <aside class="sidebar">
            <div class="logo">
                <span class="icon icon-filled" style="color: var(--google-blue); font-size: 32px;">smart_toy</span>
                <h1>LocalLLM Studio</h1>
            </div>

            <!-- System Info Card -->
            <div class="card">
                <h2><span class="icon">memory</span> System</h2>
                <div class="stat-row">
                    <span class="stat-label">RAM Usage</span>
                    <span class="stat-value" id="ram-stats">{{ hardware.ram_used_gb }} / {{ hardware.ram_gb }} GB</span>
                </div>
                 <!-- Progress Bar -->
                <div style="height: 4px; background: #e0e0e0; border-radius: 2px; margin-bottom: 12px; overflow: hidden;">
                    <div style="height: 100%; width: {{ (hardware.ram_used_gb / hardware.ram_gb) * 100 }}%; background: var(--google-blue);"></div>
                </div>

                <div class="stat-row">
                    <span class="stat-label">GPU</span>
                    <span class="stat-value" title="{{ hardware.gpu_name }}">{{ hardware.gpu_name[:12] }}...</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">VRAM</span>
                    <span class="stat-value">{{ hardware.gpu_vram }} GB</span>
                </div>
            </div>

            <!-- Model Selector -->
            <div class="card">
                <h2><span class="icon">model_training</span> Load Model</h2>
                <div class="input-group">
                    <label class="input-label">Select Model</label>
                    <select id="model-select">
                        {% for model in models %}
                        <option value="{{ model.repo }}" {{ 'selected' if model.recommended else '' }}>
                            {{ '[OK]' if model.fits else '[WARN]' }} {{ model.name }} ({{ model.size_gb }}GB)
                        </option>
                        {% endfor %}
                    </select>
                </div>
                <div style="display: flex; gap: 8px;">
                    <button class="btn btn-primary" style="flex: 1;" id="load-btn" onclick="loadModel()">
                        <span class="icon">downloading</span>
                        <span id="load-btn-text">Load to VRAM</span>
                    </button>
                    <button class="btn" style="background: var(--error); color: white; display: none;" id="unload-btn" onclick="unloadModel()">
                        <span class="icon">memory</span>
                        Free RAM
                    </button>
                </div>
                <div id="model-status" style="margin-top: 12px; font-size: 13px; color: var(--on-surface-variant); text-align: center;"></div>
            </div>

            <!-- Generation Settings -->
            <div class="card">
                <h2><span class="icon">tune</span> Parameters</h2>
                <div class="input-group">
                    <div class="stat-row">
                        <span class="stat-label">Temperature</span>
                        <span class="stat-value" id="temp-value">0.7</span>
                    </div>
                    <input type="range" id="temperature" min="0" max="1.5" step="0.1" value="0.7" 
                           oninput="document.getElementById('temp-value').innerText = this.value">
                </div>
                <div class="input-group">
                    <div class="stat-row">
                        <span class="stat-label">Max Tokens</span>
                        <span class="stat-value" id="tokens-value">2048</span>
                    </div>
                    <input type="range" id="max-tokens" min="256" max="4096" step="256" value="2048"
                           oninput="document.getElementById('tokens-value').innerText = this.value">
                </div>
            </div>
            
            <div style="margin-top: auto; font-size: 12px; color: var(--on-surface-variant); text-align: center;">
                v1.0.2 • Offline Mode
            </div>
        </aside>

        <!-- Main Chat content -->
        <main class="main-content">
            <header class="chat-header">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="icon icon-filled" style="color: var(--google-blue);">chat_bubble</span>
                    <span style="font-weight: 500;">Chat Session</span>
                </div>
                <div>
                     <button class="btn btn-secondary btn-icon" onclick="clearChat()" title="Reset Chat">
                        <span class="icon">restart_alt</span>
                    </button>
                    <button class="btn btn-secondary btn-icon" onclick="exportChat()" title="Save Conversation">
                        <span class="icon">save_alt</span>
                    </button>
                </div>
            </header>

            <div class="chat-messages" id="chat-messages">
                <div class="welcome-screen">
                    <span class="icon welcome-icon icon-filled">smart_toy</span>
                    <h2 style="font-size: 24px; font-weight: 400; margin-bottom: 8px;">Hi, I'm your Local AI</h2>
                    <p style="max-width: 400px; line-height: 1.6;">
                        I run entirely on your hardware. No data leaves this computer. Load a model from the sidebar to start chatting.
                    </p>
                </div>
            </div>

            <div class="chat-input-area">
                <div class="input-box">
                    <textarea id="user-input" rows="1" placeholder="Type a message..." 
                        oninput="this.style.height = ''; this.style.height = Math.min(this.scrollHeight, 150) + 'px'"
                        onkeydown="handleKeyDown(event)"></textarea>
                    <button class="btn btn-primary btn-icon" id="send-btn" onclick="sendMessage()" disabled style="width: 36px; height: 36px; margin-left: 8px; flex-shrink: 0; display: flex; align-items: center; justify-content: center;">
                        <span class="icon">send</span>
                    </button>
                    <button class="btn btn-icon" id="stop-gen-btn" onclick="stopGeneration()" style="width: 36px; height: 36px; margin-left: 8px; flex-shrink: 0; display: none; align-items: center; justify-content: center; background: var(--error); color: white;">
                        <span class="icon">stop</span>
                    </button>
                </div>
                <div style="text-align: center; margin-top: 12px; font-size: 11px; color: var(--on-surface-variant);">
                    AI may produce inaccurate information.
                </div>
            </div>
        </main>
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
                    const el = document.getElementById('ram-stats');
                    if (el) {
                        const used = (data.ram_gb - data.available_gb).toFixed(1);
                        el.textContent = `${used} / ${data.ram_gb} GB`;
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
        let chatAbortController = null;
        
        function stopGeneration() {
            if (chatAbortController) {
                chatAbortController.abort();
                chatAbortController = null;
                
                // Also tell backend to stop
                fetch('/api/stop_chat', {method: 'POST'})
                    .catch(console.error);
                
                console.log('🛑 Stopping generation...');
            }
        }
        
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

        async function unloadModel() {
            const btn = document.getElementById('load-btn');
            const unloadBtn = document.getElementById('unload-btn');
            const status = document.getElementById('model-status');
            
            unloadBtn.disabled = true;
            unloadBtn.innerHTML = '<span class="icon">hourglass_empty</span> Freeing...';
            
            try {
                const response = await fetch('/api/unload', {method: 'POST'});
                const data = await response.json();
                
                if (data.success) {
                    modelLoaded = false;
                    
                    // Hide unload button, enable load button
                    unloadBtn.style.display = 'none';
                    btn.disabled = false;
                    
                    // Reset status
                    status.textContent = '[OK] ' + data.message;
                    status.style.color = 'var(--success)';
                    
                    // Update connection badge
                    const badge = document.getElementById('connection-status');
                    badge.className = 'status-badge';
                    document.getElementById('status-text').textContent = 'Ready';
                    
                    // Disable send button
                    document.getElementById('send-btn').disabled = true;
                    
                    showToast('🧹 Model unloaded, RAM freed!', 'success');
                } else {
                    status.textContent = '[ERROR] ' + (data.error || 'Failed to unload');
                    status.style.color = 'var(--error)';
                    showToast(data.error || 'Failed to unload', 'error');
                }
            } catch (e) {
                console.error(e);
                status.textContent = '[ERROR] Error unloading model';
                status.style.color = 'var(--error)';
                showToast('Error unloading model', 'error');
            } finally {
                unloadBtn.disabled = false;
                unloadBtn.innerHTML = '<span class="icon">memory</span> Free RAM';
            }
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
                                console.log('[OK] Model loaded successfully, showing Free RAM button');
                                status.textContent = '[OK] ' + data.message;
                                status.style.color = 'var(--success)';
                                status.classList.remove('error-text');
                                document.getElementById('send-btn').disabled = false;
                                modelLoaded = true;
                                
                                // Update status badge
                                const badge = document.getElementById('connection-status');
                                badge.className = 'status-badge connected';
                                document.getElementById('status-text').textContent = 'Model Ready';
                                
                                showToast('Model loaded successfully!', 'success');
                                
                                // Reset load button and show unload button
                                const loadBtn = document.getElementById('load-btn');
                                const loadBtnText = document.getElementById('load-btn-text');
                                const unloadBtn = document.getElementById('unload-btn');
                                
                                loadBtn.onclick = loadModel;
                                loadBtn.classList.remove('btn-danger');
                                loadBtnText.innerText = "Load Model";
                                
                                // Show the Free RAM button
                                console.log('Setting unload-btn display to flex');
                                unloadBtn.style.display = 'flex';
                                unloadBtn.style.alignItems = 'center';
                                unloadBtn.style.gap = '4px';
                                
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
                                     status.textContent = '[ERROR] ' + data.error;
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
                } else if (!modelLoaded) {
                    // Only show connection error if model wasn't loaded
                    status.textContent = '[ERROR] Connection error';
                    status.style.color = 'var(--error)';
                    console.error(error);
                }
            } finally {
                // Ensure button reset if not successful or cancelled
                if (!modelLoaded && btnText.innerText.includes('Stop')) {
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
                showToast('[WARN] Please load a model first!', 'error');
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
            
            // Create abort controller for this chat request
            chatAbortController = new AbortController();
            
            // Show stop generation button, hide send button
            document.getElementById('send-btn').style.display = 'none';
            document.getElementById('stop-gen-btn').style.display = 'flex';
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: message,
                        system_prompt: systemPrompt,
                        temperature: parseFloat(document.getElementById('temperature').value),
                        max_tokens: parseInt(document.getElementById('max-tokens').value)
                    }),
                    signal: chatAbortController.signal
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
                                if (data.error) fullText = '[ERROR] ' + data.error;
                                
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
                if (error.name === 'AbortError') {
                    showToast('🛑 Generation stopped', 'info');
                } else {
                    addMessage('assistant', '[ERROR] Error: ' + error.message);
                }
            }
            
            // Reset state
            chatAbortController = null;
            isGenerating = false;
            document.getElementById('send-btn').style.display = 'flex';
            document.getElementById('stop-gen-btn').style.display = 'none';
            input.focus();
        }
        
        function clearChat() {
            const messages = document.getElementById('chat-messages');
            messages.innerHTML = '';
            if (!modelLoaded) {
                messages.innerHTML = `
                    <div class="welcome">
                        <div class="welcome-icon">[START]</div>
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
        self._chat_cancelled = False  # Flag to cancel ongoing chat generation
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
                "ram_used_gb": round(hw.ram_gb - hw.available_ram_gb, 1),
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

        @self.app.route('/api/unload', methods=['POST'])
        def unload_model():
            """Unload the current model and free RAM."""
            try:
                if self.backend.is_loaded:
                    self.backend.unload_model()
                    return jsonify({"success": True, "message": "Model unloaded. RAM freed."})
                else:
                    return jsonify({"success": True, "message": "No model was loaded."})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route('/api/stop_chat', methods=['POST'])
        def stop_chat():
            """Stop ongoing chat generation."""
            self._chat_cancelled = True
            if hasattr(self.backend, 'stop_generation'):
                 self.backend.stop_generation()
            return jsonify({"success": True})

        @self.app.route('/api/chat', methods=['POST'])
        def chat():
            data = request.json
            message = data.get('message', '')
            system_prompt = data.get('system_prompt', 'You are a helpful assistant.')
            temperature = float(data.get('temperature', 0.7))
            max_tokens = int(data.get('max_tokens', 2048))
            
            # Reset cancellation flag
            self._chat_cancelled = False
            
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
                        # Check for cancellation
                        if self._chat_cancelled:
                            yield f"data: {json.dumps({'error': 'Generation cancelled'})}\n\n"
                            break
                            
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
        print("[START] LocalLLM Studio - Web UI")
        print(f"{'=' * 60}")
        print(f"\n🌐 Open in browser: http://localhost:{port}")
        print("   Press Ctrl+C to stop\n")
        
        self.app.run(host=host, port=port, debug=False, threaded=True)


def run_web_ui(backend: InferenceBackend = None, port: int = 7860):
    """Launch the web UI."""
    ui = WebUI(backend)
    ui.run(port=port)
