#!/bin/bash
# ============================================================================
# LocalLLM Studio - Linux Build Script
# Creates a self-contained AppImage that works on any Linux distro
# ============================================================================

set -e

APP_NAME="LocalLLM Studio"
APP_ID="localllm-studio"
VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DIST_DIR="$PROJECT_DIR/dist"
BUILD_DIR="$PROJECT_DIR/build"
APPDIR="$BUILD_DIR/AppDir"

echo "=============================================="
echo "  Building $APP_NAME v$VERSION for Linux"
echo "=============================================="

cd "$PROJECT_DIR"

# Step 1: Check for Python
echo ""
echo "[1/6] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required to build"
    exit 1
fi
python3 --version

# Step 2: Create virtual environment
echo ""
echo "[2/6] Setting up build environment..."
if [ ! -d "build_venv" ]; then
    python3 -m venv build_venv
fi
source build_venv/bin/activate

# Step 3: Install dependencies
echo ""
echo "[3/6] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# Step 4: Clean previous builds
echo ""
echo "[4/6] Cleaning previous builds..."
rm -rf "$DIST_DIR" "$BUILD_DIR"
mkdir -p "$DIST_DIR" "$APPDIR"

# Step 5: Build with PyInstaller
echo ""
echo "[5/6] Building application..."
pyinstaller localllm_studio.spec --noconfirm

# Step 6: Create AppImage structure
echo ""
echo "[6/6] Creating AppImage..."

# Move executable to AppDir
cp "$DIST_DIR/$APP_ID" "$APPDIR/"

# Create desktop entry
cat > "$APPDIR/$APP_ID.desktop" << EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Exec=$APP_ID
Icon=$APP_ID
Categories=Utility;Development;
Comment=Run AI models privately on your device
Terminal=false
EOF

# Create AppRun
cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
exec "$HERE/localllm-studio" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# Download appimagetool if not present
if [ ! -f "appimagetool" ]; then
    echo "Downloading appimagetool..."
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" -O appimagetool
    chmod +x appimagetool
fi

# Create AppImage
./appimagetool "$APPDIR" "$DIST_DIR/LocalLLM-Studio-$VERSION-x86_64.AppImage"

echo ""
echo "=============================================="
echo "  ✅ BUILD SUCCESSFUL!"
echo "=============================================="
echo ""
echo "  Output: $DIST_DIR/LocalLLM-Studio-$VERSION-x86_64.AppImage"
echo ""
echo "  To run on any Linux:"
echo "    chmod +x LocalLLM-Studio-*.AppImage"
echo "    ./LocalLLM-Studio-*.AppImage"
echo ""

deactivate
