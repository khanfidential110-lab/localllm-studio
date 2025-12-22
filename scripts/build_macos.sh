#!/bin/bash
# ============================================================================
# LocalLLM Studio - macOS Build Script
# Creates a self-contained .app bundle that works on any Mac
# ============================================================================

set -e  # Exit on error

APP_NAME="LocalLLM Studio"
VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DIST_DIR="$PROJECT_DIR/dist"
BUILD_DIR="$PROJECT_DIR/build"

echo "=============================================="
echo "  Building $APP_NAME v$VERSION for macOS"
echo "=============================================="

cd "$PROJECT_DIR"

# Step 1: Check for Python
echo ""
echo "[1/5] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required to build"
    exit 1
fi
python3 --version

# Step 2: Create/activate virtual environment for clean build
echo ""
echo "[2/5] Setting up build environment..."
if [ ! -d "build_venv" ]; then
    python3 -m venv build_venv
fi
source build_venv/bin/activate

# Step 3: Install dependencies
echo ""
echo "[3/5] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# Step 4: Clean previous builds
echo ""
echo "[4/5] Cleaning previous builds..."
rm -rf "$DIST_DIR" "$BUILD_DIR"
mkdir -p "$DIST_DIR"

# Step 5: Build with PyInstaller
echo ""
echo "[5/5] Building application..."
pyinstaller localllm_studio.spec --noconfirm

# Verify build
if [ -d "$DIST_DIR/$APP_NAME.app" ]; then
    echo ""
    echo "=============================================="
    echo "  ✅ BUILD SUCCESSFUL!"
    echo "=============================================="
    echo ""
    echo "  Output: $DIST_DIR/$APP_NAME.app"
    echo ""
    echo "  To install:"
    echo "    1. Drag '$APP_NAME.app' to Applications"
    echo "    2. Double-click to run"
    echo ""
    echo "  To create DMG installer, run:"
    echo "    ./scripts/create_dmg.sh"
    echo ""
    
    # Get app size
    APP_SIZE=$(du -sh "$DIST_DIR/$APP_NAME.app" | cut -f1)
    echo "  App size: $APP_SIZE"
else
    echo ""
    echo "=============================================="
    echo "  ❌ BUILD FAILED"
    echo "=============================================="
    exit 1
fi

deactivate
