#!/bin/bash
# ============================================================================
# LocalLLM Studio - Linux Complete Setup
# Automatically installs Python, dependencies, and builds the application
# Supports: Ubuntu, Debian, RedHat, CentOS, Fedora, Arch
# ============================================================================

set -e

APP_NAME="LocalLLM Studio"
PYTHON_MIN_VERSION="3.9"

echo "=============================================="
echo "  $APP_NAME - Complete Setup for Linux"
echo "=============================================="
echo

# Detect package manager
detect_package_manager() {
    if command -v apt-get &> /dev/null; then
        PKG_MANAGER="apt"
        PKG_INSTALL="sudo apt-get install -y"
        PKG_UPDATE="sudo apt-get update"
    elif command -v dnf &> /dev/null; then
        PKG_MANAGER="dnf"
        PKG_INSTALL="sudo dnf install -y"
        PKG_UPDATE="sudo dnf check-update || true"
    elif command -v yum &> /dev/null; then
        PKG_MANAGER="yum"
        PKG_INSTALL="sudo yum install -y"
        PKG_UPDATE="sudo yum check-update || true"
    elif command -v pacman &> /dev/null; then
        PKG_MANAGER="pacman"
        PKG_INSTALL="sudo pacman -S --noconfirm"
        PKG_UPDATE="sudo pacman -Sy"
    else
        echo "[ERROR] Unsupported package manager."
        echo "Please install Python 3.9+ manually."
        exit 1
    fi
    echo "Detected package manager: $PKG_MANAGER"
}

# ============================================
# Step 1: Install system dependencies
# ============================================
echo
echo "[1/6] Installing system dependencies..."

detect_package_manager
$PKG_UPDATE

case $PKG_MANAGER in
    apt)
        $PKG_INSTALL python3 python3-pip python3-venv python3-dev \
            build-essential cmake libwebkit2gtk-4.0-dev
        ;;
    dnf|yum)
        $PKG_INSTALL python3 python3-pip python3-devel \
            gcc gcc-c++ cmake webkit2gtk3-devel
        ;;
    pacman)
        $PKG_INSTALL python python-pip base-devel cmake webkit2gtk
        ;;
esac

echo "System dependencies installed!"

# ============================================
# Step 2: Check Python version
# ============================================
echo
echo "[2/6] Checking Python version..."

PYTHON_CMD=""
for cmd in python3 python; do
    if command -v $cmd &> /dev/null; then
        version=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if [ "$(echo "$version >= $PYTHON_MIN_VERSION" | bc)" -eq 1 ]; then
            PYTHON_CMD=$cmd
            echo "Found $cmd version $version"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "[ERROR] Python $PYTHON_MIN_VERSION+ not found."
    exit 1
fi

# ============================================
# Step 3: Create virtual environment
# ============================================
echo
echo "[3/6] Creating virtual environment..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ -d "$VENV_DIR" ]; then
    echo "Removing old virtual environment..."
    rm -rf "$VENV_DIR"
fi

$PYTHON_CMD -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "Virtual environment created!"

# ============================================
# Step 4: Upgrade pip and install dependencies
# ============================================
echo
echo "[4/6] Installing Python dependencies..."

pip install --upgrade pip

# Install core dependencies
pip install flask huggingface-hub requests pywebview

# Try pre-built wheel for llama-cpp-python first
echo "Installing llama-cpp-python..."
if ! pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu 2>/dev/null; then
    echo "Pre-built wheel not available, building from source..."
    
    # Set compiler flags to avoid Anaconda conflicts
    unset CONDA_PREFIX 2>/dev/null || true
    export PATH=$(echo $PATH | sed 's|[^:]*anaconda[^:]*:||g' | sed 's|[^:]*miniconda[^:]*:||g')
    
    CMAKE_ARGS="-DGGML_NATIVE=OFF" pip install llama-cpp-python --no-cache-dir
fi

# Install PyInstaller
pip install pyinstaller

echo "Dependencies installed successfully!"

# ============================================
# Step 5: Build the application
# ============================================
echo
echo "[5/6] Building $APP_NAME..."

cd "$SCRIPT_DIR"
python -m PyInstaller localllm_studio.spec --noconfirm

# ============================================
# Step 6: Create launcher script
# ============================================
echo
echo "[6/6] Creating launcher..."

cat > "$SCRIPT_DIR/localllm-studio" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/dist/LocalLLM Studio" "$@"
EOF
chmod +x "$SCRIPT_DIR/localllm-studio"

# Create desktop entry
DESKTOP_FILE="$HOME/.local/share/applications/localllm-studio.desktop"
mkdir -p "$(dirname "$DESKTOP_FILE")"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=LocalLLM Studio
Comment=Run AI models privately on your device
Exec=$SCRIPT_DIR/dist/LocalLLM Studio
Terminal=false
Categories=Utility;Development;
EOF

echo
echo "=============================================="
echo "  BUILD COMPLETE!"
echo "=============================================="
echo
echo "  To run: ./localllm-studio"
echo "  Or find 'LocalLLM Studio' in your applications menu"
echo
echo "  Application: $SCRIPT_DIR/dist/LocalLLM Studio"
echo
