#!/bin/bash
# ============================================================================
# LocalLLM Studio - macOS Complete Setup
# Automatically installs dependencies and builds the application
# ============================================================================

set -e

APP_NAME="LocalLLM Studio"

echo "=============================================="
echo "  $APP_NAME - Complete Setup for macOS"
echo "=============================================="
echo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ============================================
# Step 1: Check for Xcode Command Line Tools
# ============================================
echo "[1/5] Checking Xcode Command Line Tools..."

if ! xcode-select -p &> /dev/null; then
    echo "Installing Xcode Command Line Tools..."
    xcode-select --install
    echo "Please complete the installation and run this script again."
    exit 0
fi
echo "Xcode tools found!"

# ============================================
# Step 2: Check Python
# ============================================
echo
echo "[2/5] Checking Python..."

if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Installing via Homebrew..."
    
    # Install Homebrew if needed
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    brew install python@3.11
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python $PYTHON_VERSION found!"

# ============================================
# Step 3: Create virtual environment
# ============================================
echo
echo "[3/5] Creating virtual environment..."

VENV_DIR="$SCRIPT_DIR/.venv"
if [ -d "$VENV_DIR" ]; then
    rm -rf "$VENV_DIR"
fi

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

pip install --upgrade pip

# ============================================
# Step 4: Install dependencies
# ============================================
echo
echo "[4/5] Installing dependencies..."

pip install flask huggingface-hub requests pywebview pyinstaller

# Install llama-cpp-python (with Metal support on Apple Silicon)
if [[ $(uname -m) == 'arm64' ]]; then
    echo "Apple Silicon detected - building with Metal support..."
    CMAKE_ARGS="-DGGML_METAL=ON" pip install llama-cpp-python --no-cache-dir
else
    pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
fi

echo "Dependencies installed!"

# ============================================
# Step 5: Build the application
# ============================================
echo
echo "[5/5] Building $APP_NAME..."

python -m PyInstaller localllm_studio.spec --noconfirm

# Create DMG
if [ -d "dist/$APP_NAME.app" ]; then
    echo
    echo "Creating DMG installer..."
    
    cd dist
    hdiutil create -volname "$APP_NAME" \
        -srcfolder "$APP_NAME.app" \
        -ov -format UDZO \
        "LocalLLM-Studio-macOS.dmg"
    cd ..
fi

echo
echo "=============================================="
echo "  BUILD COMPLETE!"
echo "=============================================="
echo
echo "  Application: dist/$APP_NAME.app"
echo "  Installer:   dist/LocalLLM-Studio-macOS.dmg"
echo
echo "  To install:"
echo "    1. Open the DMG file"
echo "    2. Drag the app to Applications"
echo
