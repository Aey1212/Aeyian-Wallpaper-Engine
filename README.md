# Aeyian Wallpaper Engine

![License](https://img.shields.io/badge/License-Apache--2.0-blue) ![Version](https://img.shields.io/badge/Version-0.0.1-lightgreen)

A native KDE Plasma 6 interactive wallpaper engine with a visual editor.

## Vision

Bring Wallpaper Engine-like functionality to Linux natively:

- Fully interactive wallpapers responding to mouse input
- Visual editor for creating wallpapers without coding
- User-customizable properties from Plasma settings
- Audio reactivity via PipeWire
- Lua scripting for advanced interactivity

## Status

**Early Development**: Tracks simulated cursor and calibrates periodically to fix drift.

## Target Platform

- Arch Linux
- KDE Plasma 6
- Wayland

## Installation

```bash
git clone https://github.com/Aey1212/Aeyian-Wallpaper-Engine.git

cd Aeyian-Wallpaper-Engine

./install.sh 
```

The installer will: 

- Build the plugin 

- Ask to add you to the `input` group (required for cursor tracking) 

- Install to your local Plasma wallpapers
  
  

Then: Right-click desktop → Configure Desktop → Wallpaper Type → **Aeyian Wallpaper Engine**



**NOTE:** you might need to reboot for it to work in some cases. The installer will tell you if you need to.

## Known Bugs

- The engine currently disrespects the preference of a disabled trackpad, or other cursor-moving tools.

## License

Apache-2.0
