#!/bin/bash
# ============================================================================
# LocalLLM Studio - Create macOS DMG Installer
# Creates a distributable .dmg file that users can double-click to install
# ============================================================================

set -e

APP_NAME="LocalLLM Studio"
VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DIST_DIR="$PROJECT_DIR/dist"
DMG_NAME="LocalLLM-Studio-${VERSION}-macOS"

echo "Creating DMG installer..."

cd "$DIST_DIR"

# Check if app exists
if [ ! -d "$APP_NAME.app" ]; then
    echo "ERROR: $APP_NAME.app not found. Run build_macos.sh first."
    exit 1
fi

# Create DMG
echo "Creating $DMG_NAME.dmg..."

# Create temporary directory for DMG contents
mkdir -p dmg_temp
cp -r "$APP_NAME.app" dmg_temp/
ln -sf /Applications dmg_temp/Applications

# Create DMG
hdiutil create -volname "$APP_NAME" \
    -srcfolder dmg_temp \
    -ov \
    -format UDZO \
    "$DMG_NAME.dmg"

# Cleanup
rm -rf dmg_temp

echo ""
echo "=============================================="
echo "  ✅ DMG CREATED!"
echo "=============================================="
echo ""
echo "  Installer: $DIST_DIR/$DMG_NAME.dmg"
echo ""
echo "  To install on any Mac:"
echo "    1. Double-click the .dmg file"
echo "    2. Drag the app to Applications"
echo "    3. Eject the disk image"
echo ""

# Get DMG size
DMG_SIZE=$(du -h "$DMG_NAME.dmg" | cut -f1)
echo "  Size: $DMG_SIZE"
