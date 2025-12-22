#!/usr/bin/env python3
"""
LocalLLM Studio - Desktop Application
Production-grade entry point with comprehensive error handling.

Author: LocalLLM Studio Team
Version: 1.0.0
"""

import sys
import os
import socket
import threading
import time
import logging
import traceback
from contextlib import contextmanager

# Configure logging before any imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger('LocalLLM')

# Add the project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================================
# Configuration
# ============================================================================

APP_NAME = "LocalLLM Studio"
APP_VERSION = "1.0.0"
DEFAULT_WIDTH = 1400
DEFAULT_HEIGHT = 900
MIN_WIDTH = 800
MIN_HEIGHT = 600
SERVER_STARTUP_TIMEOUT = 10  # seconds
HEALTH_CHECK_INTERVAL = 0.2  # seconds


# ============================================================================
# HTML Templates for Loading/Error States
# ============================================================================

LOADING_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Loading LocalLLM Studio...</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
            color: #fff;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
        }}
        .container {{
            text-align: center;
            padding: 40px;
        }}
        .logo {{
            font-size: 64px;
            margin-bottom: 24px;
            animation: float 3s ease-in-out infinite;
        }}
        @keyframes float {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-10px); }}
        }}
        h1 {{
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 16px;
            background: linear-gradient(135deg, #6366f1, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .spinner {{
            width: 48px;
            height: 48px;
            border: 4px solid rgba(99, 102, 241, 0.2);
            border-top-color: #6366f1;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 24px auto;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        .status {{
            color: rgba(255, 255, 255, 0.6);
            font-size: 14px;
        }}
        .version {{
            position: fixed;
            bottom: 20px;
            color: rgba(255, 255, 255, 0.3);
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🚀</div>
        <h1>LocalLLM Studio</h1>
        <div class="spinner"></div>
        <p class="status">Initializing AI engine...</p>
    </div>
    <div class="version">v{version}</div>
</body>
</html>
""".format(version=APP_VERSION)


ERROR_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Error - LocalLLM Studio</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a0a0a 0%, #2d1515 50%, #1a0f0f 100%);
            color: #fff;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            text-align: center;
            padding: 40px;
            max-width: 600px;
        }}
        .icon {{ font-size: 64px; margin-bottom: 24px; }}
        h1 {{
            font-size: 24px;
            color: #ef4444;
            margin-bottom: 16px;
        }}
        .message {{
            color: rgba(255, 255, 255, 0.7);
            margin-bottom: 24px;
            line-height: 1.6;
        }}
        .details {{
            background: rgba(0, 0, 0, 0.3);
            border-radius: 12px;
            padding: 16px;
            font-family: monospace;
            font-size: 12px;
            text-align: left;
            color: rgba(255, 255, 255, 0.5);
            max-height: 200px;
            overflow: auto;
            margin-bottom: 24px;
        }}
        .btn {{
            background: linear-gradient(135deg, #6366f1, #a855f7);
            color: white;
            border: none;
            padding: 12px 32px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            margin: 8px;
        }}
        .btn:hover {{ opacity: 0.9; }}
        .btn-secondary {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">⚠️</div>
        <h1>{title}</h1>
        <p class="message">{message}</p>
        {details_section}
        <button class="btn" onclick="window.location.reload()">Retry</button>
        <button class="btn btn-secondary" onclick="window.close()">Close</button>
    </div>
</body>
</html>
"""


# ============================================================================
# Utilities
# ============================================================================

def find_free_port(start_port=7860, max_attempts=100):
    """
    Find an available port on localhost.
    
    Args:
        start_port: Port to start searching from
        max_attempts: Maximum number of ports to try
        
    Returns:
        Available port number
        
    Raises:
        RuntimeError: If no free port is found
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    
    raise RuntimeError(f"No free port found in range {start_port}-{start_port + max_attempts}")


def wait_for_server(url, timeout=SERVER_STARTUP_TIMEOUT):
    """
    Wait for the Flask server to become available.
    
    Args:
        url: Server URL to check
        timeout: Maximum time to wait in seconds
        
    Returns:
        True if server is ready, False otherwise
    """
    import urllib.request
    import urllib.error
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = urllib.request.urlopen(url, timeout=1)
            if response.status == 200:
                return True
        except (urllib.error.URLError, ConnectionRefusedError, TimeoutError):
            pass
        time.sleep(HEALTH_CHECK_INTERVAL)
    
    return False


def generate_error_html(title, message, details=None):
    """Generate error page HTML."""
    details_section = ""
    if details:
        details_section = f'<div class="details"><pre>{details}</pre></div>'
    
    return ERROR_HTML_TEMPLATE.format(
        title=title,
        message=message,
        details_section=details_section
    )


# ============================================================================
# Server Management
# ============================================================================

class ServerManager:
    """Manages the Flask server lifecycle."""
    
    def __init__(self):
        self.server_thread = None
        self.port = None
        self.error = None
        self.is_running = False
        
    def start(self, port):
        """Start the Flask server in a background thread."""
        self.port = port
        self.server_thread = threading.Thread(
            target=self._run_server,
            daemon=True,
            name="FlaskServer"
        )
        self.server_thread.start()
        
    def _run_server(self):
        """Internal method to run the Flask server."""
        try:
            # Import here to catch import errors
            from ui.web import WebUI
            from backends import LlamaCppBackend
            
            logger.info("Initializing LlamaCpp backend...")
            backend = LlamaCppBackend()
            
            logger.info("Creating Web UI...")
            web_ui = WebUI(backend=backend)
            
            self.is_running = True
            logger.info(f"Starting Flask server on port {self.port}")
            
            # Suppress Flask's default logging for cleaner output
            import logging as flask_logging
            flask_logging.getLogger('werkzeug').setLevel(flask_logging.WARNING)
            
            web_ui.app.run(
                host='127.0.0.1',
                port=self.port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
            
        except ImportError as e:
            self.error = f"Missing dependency: {e}"
            logger.error(f"Import error: {e}")
            
        except Exception as e:
            self.error = str(e)
            logger.error(f"Server error: {e}")
            traceback.print_exc()
    
    @property
    def url(self):
        """Get the server URL."""
        return f'http://127.0.0.1:{self.port}'


# ============================================================================
# Main Application
# ============================================================================

def check_dependencies():
    """Verify all required dependencies are installed."""
    missing = []
    
    # Check pywebview
    try:
        import webview
    except ImportError:
        missing.append("pywebview")
    
    # Check Flask
    try:
        import flask
    except ImportError:
        missing.append("flask")
    
    # Check llama-cpp-python
    try:
        import llama_cpp
    except ImportError:
        missing.append("llama-cpp-python")
    
    # Check huggingface-hub
    try:
        import huggingface_hub
    except ImportError:
        missing.append("huggingface-hub")
    
    if missing:
        print("=" * 60)
        print("ERROR: Missing required dependencies!")
        print("-" * 60)
        print("Please install the following packages:")
        print()
        for pkg in missing:
            print(f"  pip install {pkg}")
        print()
        print("Or install all requirements:")
        print("  pip install -r requirements.txt")
        print("=" * 60)
        sys.exit(1)


def main():
    """Main entry point for the desktop application."""
    
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    
    # Check dependencies first
    check_dependencies()
    
    import webview
    
    # Find available port
    try:
        port = find_free_port()
        logger.info(f"Found available port: {port}")
    except RuntimeError as e:
        logger.error(f"Port allocation failed: {e}")
        sys.exit(1)
    
    # Start server
    server = ServerManager()
    server.start(port)
    
    # Create window with loading screen first
    window = webview.create_window(
        title=APP_NAME,
        html=LOADING_HTML,
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        confirm_close=True,
        text_select=True,
    )
    
    def on_loaded():
        """Called when webview is ready."""
        # Wait for Flask server to be ready
        logger.info("Waiting for server...")
        
        if wait_for_server(server.url):
            logger.info("Server ready! Loading UI...")
            window.load_url(server.url)
        else:
            # Server failed to start
            error_msg = server.error or "Server failed to start within timeout"
            logger.error(f"Server startup failed: {error_msg}")
            
            error_html = generate_error_html(
                title="Server Startup Failed",
                message="The AI engine could not be initialized. This might be due to missing dependencies or insufficient memory.",
                details=error_msg
            )
            window.load_html(error_html)
    
    # Start webview with callback
    webview.start(
        on_loaded,
        private_mode=False,
        storage_path=os.path.expanduser('~/.localllm_studio'),
    )
    
    logger.info("Application closed. Goodbye!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
