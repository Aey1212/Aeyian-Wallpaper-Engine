# Effects catalog for video layers.


EFFECT_TYPES = {
    "Playback": [
        "Speed",
        "Chroma Key",
    ],
}

EFFECT_TYPE_MAP = {
    "Speed":      ("speed",      {"rate": 1.0}),
    "Chroma Key": ("chroma_key", {"color": "#00ff00", "tolerance": 0.3, "softness": 0.1}),
}

EFFECT_SCHEMAS = {
    "speed": [
        {"key": "params.rate", "label": "Rate", "widget": "float",
         "min": 0.1, "max": 4.0},
    ],
    "chroma_key": [
        {"key": "params.color", "label": "Key Color", "widget": "color"},
        {"key": "params.tolerance", "label": "Tolerance", "widget": "float",
         "min": 0.0, "max": 1.0},
        {"key": "params.softness", "label": "Softness", "widget": "float",
         "min": 0.0, "max": 1.0},
    ],
}
