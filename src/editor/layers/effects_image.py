# Effects catalog for image layers.


EFFECT_TYPES = {
    "Color": [
        "Grayscale",
        "Hue Shift",
        "Saturation",
        "Brightness",
        "Tint",
    ],
    "Blur": [
        "Gaussian Blur",
    ],
    "Distortion": [
        "Wave",
        "Cursor Distortion",
        "Ripple",
    ],
}

EFFECT_TYPE_MAP = {
    # Color
    "Grayscale":          ("grayscale",   {"strength": 1.0}),
    "Hue Shift":          ("hue_shift",   {"shift": 0.0}),
    "Saturation":         ("saturation",  {"strength": 1.0}),
    "Brightness":         ("brightness",  {"brightness": 0.0}),
    "Tint":               ("tint",        {"color": "#ffffff", "strength": 0.5}),
    # Blur
    "Gaussian Blur":      ("blur",        {"radius": 5}),
    # Distortion (placeholders – no QML renderer yet)
    "Wave":               ("wave",        {"amplitude": 10.0, "frequency": 0.5, "speed": 1.0}),
    "Cursor Distortion":  ("distortion",  {"strength": 0.5, "radius": 0.3}),
    "Ripple":             ("ripple",      {"amplitude": 8.0, "speed": 1.0, "decay": 0.95}),
}

EFFECT_SCHEMAS = {
    # --- built-in (will render in QML) ---
    "grayscale": [
        {"key": "params.strength", "label": "Strength", "widget": "float",
         "min": 0.0, "max": 1.0},
    ],
    "hue_shift": [
        {"key": "params.shift", "label": "Shift", "widget": "float",
         "min": -1.0, "max": 1.0},
    ],
    "saturation": [
        {"key": "params.strength", "label": "Strength", "widget": "float",
         "min": 0.0, "max": 2.0},
    ],
    "brightness": [
        {"key": "params.brightness", "label": "Brightness", "widget": "float",
         "min": -1.0, "max": 1.0},
    ],
    "tint": [
        {"key": "params.color", "label": "Color", "widget": "color"},
        {"key": "params.strength", "label": "Strength", "widget": "float",
         "min": 0.0, "max": 1.0},
    ],
    "blur": [
        {"key": "params.radius", "label": "Radius", "widget": "int",
         "min": 1, "max": 50},
    ],
    # --- placeholders (custom GLSL later) ---
    "wave": [
        {"key": "params.amplitude", "label": "Amplitude", "widget": "float",
         "min": 0.0, "max": 100.0},
        {"key": "params.frequency", "label": "Frequency", "widget": "float",
         "min": 0.01, "max": 5.0},
        {"key": "params.speed", "label": "Speed", "widget": "float",
         "min": 0.0, "max": 10.0},
    ],
    "distortion": [
        {"key": "params.strength", "label": "Strength", "widget": "float",
         "min": 0.0, "max": 1.0},
        {"key": "params.radius", "label": "Radius", "widget": "float",
         "min": 0.0, "max": 1.0},
    ],
    "ripple": [
        {"key": "params.amplitude", "label": "Amplitude", "widget": "float",
         "min": 0.0, "max": 50.0},
        {"key": "params.speed", "label": "Speed", "widget": "float",
         "min": 0.0, "max": 10.0},
        {"key": "params.decay", "label": "Decay", "widget": "float",
         "min": 0.0, "max": 1.0},
    ],
}
