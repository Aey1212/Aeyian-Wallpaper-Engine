#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_SRC="$SCRIPT_DIR/src/runtime/plugin"
QML_SRC="$SCRIPT_DIR/src/runtime/qml"
NEEDS_RELOGIN=false

# --- Aey Bar ---
ESC=$'\e'
FILL_BG="${ESC}[48;5;6m"
FG="${ESC}[30m"
RESET="${ESC}[0m"
CLEAR_EOL="${ESC}[K"

ROWS=$(tput lines)
BAR_ROW=$((ROWS - 1))
TOTAL_STEPS=5

# Reserve bottom line
setup_bar() {
    tput csr 0 $((ROWS - 2))
    tput cup 0 0
    draw_bar 0 "$TOTAL_STEPS" "Starting..."
}

# Restore terminal to normal on exit
cleanup_bar() {
    tput csr 0 $((ROWS - 1))
    tput cup "$BAR_ROW" 0
    printf '%s' "$CLEAR_EOL"
    tput cnorm 2>/dev/null
}
trap cleanup_bar EXIT

draw_bar() {
    local step=$1
    local total=$2
    local msg=$3
    local filled=$((step * 10 / total))
    local empty=$((10 - filled))
    local bar=""
    local emptybar=""
    for ((i=0; i<filled; i++)); do bar+="AEY"; done
    for ((i=0; i<empty; i++)); do emptybar+="AEY"; done

    tput sc
    tput cup "$BAR_ROW" 0
    printf '\r%s%s%s%s [%d/%d] %s%s' \
        "$FILL_BG$FG" "$bar" "$RESET" "$emptybar" "$step" "$total" "$msg" "$CLEAR_EOL"
    tput rc
}

aey_progress() {
    draw_bar "$1" "$2" "$3"
}

# --- Begin Install ---

setup_bar

# Step 1: Check input group
aey_progress 1 "$TOTAL_STEPS" "Checking input group..."
if ! groups | grep -q '\binput\b'; then
    echo "⚠  You're not in the 'input' group (required for cursor tracking)"
    read -p "Add yourself to the input group? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo usermod -aG input "$USER"
        echo "✔ Added to input group"
        NEEDS_RELOGIN=true
    else
        echo "Skipping. Cursor tracking won't work without input group."
    fi
fi

# Step 2: Build
aey_progress 2 "$TOTAL_STEPS" "Building plugin..."
mkdir -p "$PLUGIN_SRC/build"
cd "$PLUGIN_SRC/build"
cmake .. > /dev/null
make > /dev/null

# Step 3: Install QML plugin
aey_progress 3 "$TOTAL_STEPS" "Installing QML plugin..."
sudo mkdir -p /usr/lib/qt6/qml/org/aey/wallpaperengine
sudo cp libaeyian-wallpaper-plugin.so /usr/lib/qt6/qml/org/aey/wallpaperengine/
sudo cp "$PLUGIN_SRC/qmldir" /usr/lib/qt6/qml/org/aey/wallpaperengine/

# Step 4: Install wallpaper package
aey_progress 4 "$TOTAL_STEPS" "Installing wallpaper..."
WALLPAPER_DIR="$HOME/.local/share/plasma/wallpapers/org.aey.wallpaperengine"
mkdir -p "$WALLPAPER_DIR/contents/ui"
cp "$PLUGIN_SRC/metadata.json" "$WALLPAPER_DIR/"
cp "$QML_SRC/main.qml" "$WALLPAPER_DIR/contents/ui/"
cp "$QML_SRC/config.qml" "$WALLPAPER_DIR/contents/ui/"

# Step 5: Done
aey_progress 5 "$TOTAL_STEPS" "Installation complete!"
sleep 0.3

# Cleanup bar and print final message in normal terminal
cleanup_bar
trap - EXIT

echo ""
if [ "$NEEDS_RELOGIN" = true ]; then
    echo "⚠  You were added to the input group."
    echo "  Please reboot your system."
else
    echo "  Run: plasmashell --replace &disown"
fi
