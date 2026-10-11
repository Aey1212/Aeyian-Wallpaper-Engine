#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_SRC="$SCRIPT_DIR/src/runtime/plugin"
QML_SRC="$SCRIPT_DIR/src/runtime/qml"

# --- Aey Bar ---
ESC=$'\e'
FILL_BG="${ESC}[48;5;6m"
FG="${ESC}[30m"
RESET="${ESC}[0m"
CLEAR_EOL="${ESC}[K"

ROWS=$(tput lines)
BAR_ROW=$((ROWS - 1))
TOTAL_STEPS=4

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

# Step 1: Build
aey_progress 1 "$TOTAL_STEPS" "Building plugin..."
mkdir -p "$PLUGIN_SRC/build"
cd "$PLUGIN_SRC/build"
cmake .. -DCMAKE_BUILD_TYPE=Release > /dev/null
make > /dev/null

# Step 2: Install QML plugin
aey_progress 2 "$TOTAL_STEPS" "Installing QML plugin..."
WALLPAPER_DIR="$HOME/.local/share/plasma/wallpapers/org.aey.wallpaperengine"
mkdir -p "$WALLPAPER_DIR/contents/ui/aeyian"
cp --remove-destination libaeyian-wallpaper-plugin.so "$WALLPAPER_DIR/contents/ui/aeyian/"
cp "$PLUGIN_SRC/qmldir" "$WALLPAPER_DIR/contents/ui/aeyian/"

# Step 3: Install wallpaper package
aey_progress 3 "$TOTAL_STEPS" "Installing wallpaper..."
mkdir -p "$WALLPAPER_DIR/contents/ui"
mkdir -p "$WALLPAPER_DIR/contents/config"
mkdir -p "$WALLPAPER_DIR/contents/kwin/v1"
cp "$PLUGIN_SRC/metadata.json" "$WALLPAPER_DIR/"
cp "$QML_SRC/main.qml" "$WALLPAPER_DIR/contents/ui/"
cp "$QML_SRC/Scene.qml" "$WALLPAPER_DIR/contents/ui/"
cp "$QML_SRC/config.qml" "$WALLPAPER_DIR/contents/ui/"
cp "$SCRIPT_DIR/src/runtime/config/main.xml" "$WALLPAPER_DIR/contents/config/"
cp "$SCRIPT_DIR/src/runtime/kwin/aeyian_cursor_v1.qml" "$WALLPAPER_DIR/contents/kwin/v1/"

# Step 4: Done
aey_progress 4 "$TOTAL_STEPS" "Installation complete!"
sleep 0.3

# Cleanup bar and print final message in normal terminal
cleanup_bar
trap - EXIT

echo ""
echo "  Run: plasmashell --replace &disown"
