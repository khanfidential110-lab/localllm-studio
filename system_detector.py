import sys
import os
import json
import webview
from localllm_studio.utils import detect_hardware

# Google-style System Detector Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Compatibility Detector</title>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Roboto:wght@400;500&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
    <style>
        :root {
            --google-blue: #1a73e8;
            --google-green: #1e8e3e;
            --google-yellow: #f9ab00;
            --google-red: #d93025;
            --surface: #ffffff;
            --on-surface: #202124;
            --on-surface-variant: #5f6368;
            --outline: #dadce0;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Google Sans', 'Roboto', sans-serif;
            background: var(--surface);
            color: var(--on-surface);
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            padding: 20px;
        }
        
        .container {
            width: 100%;
            max-width: 500px;
            background: #fff;
            border-radius: 24px;
            border: 1px solid var(--outline);
            padding: 32px;
            box-shadow: 0 1px 2px 0 rgba(60, 64, 67, 0.3), 0 2px 6px 2px rgba(60, 64, 67, 0.15);
            text-align: center;
        }
        
        .header { margin-bottom: 32px; }
        .icon-large {
            font-family: 'Material Symbols Rounded';
            font-size: 48px;
            color: var(--google-blue);
            margin-bottom: 16px;
            display: inline-block;
        }
        
        h1 { font-size: 24px; font-weight: 400; margin-bottom: 8px; }
        p { color: var(--on-surface-variant); font-size: 14px; line-height: 1.5; }
        
        .result-card {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            text-align: left;
        }
        
        .item {
            display: flex;
            justify-content: space-between;
            margin-bottom: 12px;
            font-size: 14px;
        }
        .item:last-child { margin-bottom: 0; }
        .label { color: var(--on-surface-variant); font-weight: 500; }
        .value { font-weight: 600; text-align: right; }
        
        .status-pass { color: var(--google-green); }
        .status-warn { color: var(--google-yellow); }
        .status-fail { color: var(--google-red); }
        
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: var(--google-blue);
            color: white;
            padding: 10px 24px;
            border-radius: 9999px;
            text-decoration: none;
            font-weight: 500;
            border: none;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }
        .btn:hover { background: #1557b0; box-shadow: 0 1px 3px rgba(60,64,67,0.3); }
        
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="icon-large">analytics</span>
            <h1>System Compatibility</h1>
            <p>Checking if your device can run LocalLLM Studio</p>
        </div>
        
        <div class="result-card">
            <div class="item">
                <span class="label">Platform</span>
                <span class="value">{platform} {version}</span>
            </div>
            <div class="item">
                <span class="label">CPU</span>
                <span class="value">{cpu}</span>
            </div>
            <div class="item">
                <span class="label">RAM</span>
                <span class="value">{ram} GB ({ram_avail} GB Free)</span>
            </div>
            <div class="item">
                <span class="label">GPU</span>
                <span class="value">{gpu}</span>
            </div>
             <div class="item">
                <span class="label">VRAM</span>
                <span class="value">{vram} GB</span>
            </div>
        </div>
        
        <div style="margin-bottom: 24px;">
            <div style="font-size: 18px; font-weight: 500; margin-bottom: 8px; color: {status_color};">
                {status_text}
            </div>
            <p>{status_msg}</p>
        </div>
        
        <button class="btn" onclick="window.confirm('Visit website to download?') ? window.location.href='https://canirunai.com' : window.close()">
            {btn_text}
        </button>
    </div>
</body>
</html>
"""

def main():
    try:
        hw = detect_hardware()
        
        # Logic for status
        is_pass = hw.ram_gb >= 8 or hw.gpu.vram_gb >= 4
        status_color = "#1e8e3e" if is_pass else "#f9ab00"
        status_text = "✅ System Compatible" if is_pass else "⚠️ Marginally Compatible"
        status_msg = "You can run LocalLLM Studio models locally." if is_pass else "You may experience slow performance with larger models."
        
        if hw.ram_gb < 4:
             status_color = "#d93025"
             status_text = "❌ Incompatible"
             status_msg = "Your system does not meet the minimum requirement of 4GB RAM."

        html = HTML_TEMPLATE.format(
            platform=hw.platform.value.capitalize(),
            version=hw.platform_version,
            cpu=hw.cpu_brand,
            ram=hw.ram_gb,
            ram_avail=round(hw.available_ram_gb, 1),
            gpu=hw.gpu.name[:20] + "..." if len(hw.gpu.name) > 20 else hw.gpu.name,
            vram=hw.gpu.vram_gb,
            status_color=status_color,
            status_text=status_text,
            status_msg=status_msg,
            btn_text="Download LocalLLM Studio" if is_pass else "Close"
        )
        
        webview.create_window(
            "System Detector", 
            html=html, 
            width=550, 
            height=650, 
            resizable=False
        )
        webview.start()
        
    except Exception as e:
        webview.create_window("Error", html=f"<h1>Error</h1><p>{str(e)}</p>")
        webview.start()

if __name__ == '__main__':
    main()
