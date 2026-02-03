#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_SRC="$SCRIPT_DIR/src/runtime/plugin"
QML_SRC="$SCRIPT_DIR/src/runtime/qml"
NEEDS_RELOGIN=false

# Check input group
if ! groups | grep -q '\binput\b'; then
    echo "⚠ You're not in the 'input' group (required for cursor tracking)"
    read -p "Add yourself to the input group? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo usermod -aG input "$USER"
        echo "✓ Added to input group"
        NEEDS_RELOGIN=true
    else
        echo "Skipping. Cursor tracking won't work without input group."
    fi
fi

# Build
echo "Building plugin..."
mkdir -p "$PLUGIN_SRC/build"
cd "$PLUGIN_SRC/build"
cmake ..
make

# Install QML plugin (requires sudo)
echo "Installing QML plugin..."
sudo mkdir -p /usr/lib/qt6/qml/org/aey/wallpaperengine
sudo cp libaeyian-wallpaper-plugin.so /usr/lib/qt6/qml/org/aey/wallpaperengine/
sudo cp "$PLUGIN_SRC/qmldir" /usr/lib/qt6/qml/org/aey/wallpaperengine/

# Install wallpaper package
echo "Installing wallpaper..."
WALLPAPER_DIR="$HOME/.local/share/plasma/wallpapers/org.aey.wallpaperengine"
mkdir -p "$WALLPAPER_DIR/contents/ui"
cp "$PLUGIN_SRC/metadata.json" "$WALLPAPER_DIR/"
cp "$QML_SRC/main.qml" "$WALLPAPER_DIR/contents/ui/"

echo ""
echo "✓ Installation complete!"

if [ "$NEEDS_RELOGIN" = true ]; then
    echo ""
    echo "⚠ You were added to the input group."
    echo "  Please reboot your system."
else
    echo "  Run: plasmashell --replace &disown"
fi
