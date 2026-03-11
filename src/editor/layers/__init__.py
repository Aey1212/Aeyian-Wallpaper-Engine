import json
from pathlib import Path

from .L_Dialog import AddLayerDialog, AddEffectDialog, LAYER_TYPES


SHARED_SCHEMA = [
    {"key": "name", "label": "Name", "widget": "text"},
    {"key": "visible", "label": "Visible", "widget": "bool"},
    {"key": "position.x", "label": "X", "widget": "int"},
    {"key": "position.y", "label": "Y", "widget": "int"},
    {"key": "size.width", "label": "Width", "widget": "int"},
    {"key": "size.height", "label": "Height", "widget": "int"},
    {"key": "speed", "label": "Speed", "widget": "float", "min": -10.0, "max": 10.0},
    {"key": "limit.x", "label": "Limit X", "widget": "float", "min": 0.0, "max": 1000.0},
    {"key": "limit.y", "label": "Limit Y", "widget": "float", "min": 0.0, "max": 1000.0},
]

TYPE_SCHEMAS = {
    "solid_color": [
        {"key": "color", "label": "Color", "widget": "color"},
    ],
    "image": [
        {"key": "image", "label": "Image", "widget": "file"},
    ],
    "video": [
        {"key": "video", "label": "Video", "widget": "file"},
    ],
    "audio_reactive": [],
}


def get_schema_for_layer(layer: dict) -> list:
    layer_type = layer.get("type", "")
    type_schema = TYPE_SCHEMAS.get(layer_type, [])
    return SHARED_SCHEMA + type_schema


def get_nested(data: dict, key: str):
    parts = key.split(".")
    for part in parts:
        if isinstance(data, dict):
            data = data.get(part)
        else:
            return None
    return data


def set_nested(data: dict, key: str, value):
    parts = key.split(".")
    for part in parts[:-1]:
        if part not in data or not isinstance(data[part], dict):
            data[part] = {}
        data = data[part]
    data[parts[-1]] = value


def toggle_layer_visibility(project_path: Path, layers: list, layer_id: int, visible: bool):
    for layer in layers:
        if layer.get("id") == layer_id:
            layer["visible"] = visible
            break

    layers_path = project_path / "layers.json"
    data = json.loads(layers_path.read_text())
    data["layers"] = layers
    layers_path.write_text(json.dumps(data, indent=2))


def resolve_hierarchy(layers: list) -> bool:
    used_hierarchy = set()
    highest_hierarchy = 0
    changed = False

    for layer in layers:
        if layer.get("type") == "canvas" or layer.get("id") == 0:
            continue

        hierarchy = layer.get("hierarchy")
        if isinstance(hierarchy, int) and hierarchy > 0 and hierarchy not in used_hierarchy:
            used_hierarchy.add(hierarchy)
            if hierarchy > highest_hierarchy:
                highest_hierarchy = hierarchy
            continue

        next_hierarchy = highest_hierarchy + 1
        while next_hierarchy in used_hierarchy:
            next_hierarchy += 1

        layer["hierarchy"] = next_hierarchy
        used_hierarchy.add(next_hierarchy)
        highest_hierarchy = next_hierarchy
        changed = True

    return changed


def swap_layer_order(layers: list, layer_id: int, direction: str) -> bool:
    ordered = sorted(
        (l for l in layers if l.get("type") != "canvas" and l.get("id") != 0),
        key=lambda l: l.get("hierarchy", 0),
    )
    target_idx = None
    for i, l in enumerate(ordered):
        if l.get("id") == layer_id:
            target_idx = i
            break
    if target_idx is None:
        return False

    if direction == "up" and target_idx < len(ordered) - 1:
        neighbor = ordered[target_idx + 1]
    elif direction == "down" and target_idx > 0:
        neighbor = ordered[target_idx - 1]
    else:
        return False

    target = ordered[target_idx]
    target["hierarchy"], neighbor["hierarchy"] = neighbor["hierarchy"], target["hierarchy"]
    return True


def delete_layer(project_path: Path, layers: list, effects: list, layer_id: int):
    layers[:] = [l for l in layers if l.get("id") != layer_id]
    effects[:] = [e for e in effects if e.get("layer_id") != layer_id]
    assets_dir = project_path / "assets"
    if assets_dir.exists():
        for f in assets_dir.iterdir():
            if f.stem == str(layer_id):
                f.unlink()


def create_layer(layers: list, layer_type: str, canvas_w: int, canvas_h: int) -> dict:
    max_id = 0
    max_hierarchy = 0

    for layer in layers:
        layer_id = layer.get("id")
        if isinstance(layer_id, int) and layer_id > max_id:
            max_id = layer_id

        if layer.get("type") == "canvas" or layer.get("id") == 0:
            continue

        hierarchy = layer.get("hierarchy")
        if isinstance(hierarchy, int) and hierarchy > max_hierarchy:
            max_hierarchy = hierarchy

    new_id = max_id + 1
    new_hierarchy = max_hierarchy + 1

    base_layer = {
        "id": new_id,
        "hierarchy": new_hierarchy,
        "visible": True,
        "position": {"x": 0, "y": 0},
        "size": {"width": canvas_w, "height": canvas_h},
        "speed": 0,
        "limit": {"x": 0, "y": 0},
    }

    if layer_type == "Color Layer":
        return {
            **base_layer,
            "name": f"Color Layer {new_id}",
            "type": "solid_color",
            "color": "#ffffff",
        }

    if layer_type == "Image Layer":
        return {
            **base_layer,
            "name": f"Image Layer {new_id}",
            "type": "image",
            "image": "",
        }

    if layer_type == "Video Layer":
        return {
            **base_layer,
            "name": f"Video Layer {new_id}",
            "type": "video",
            "video": "",
        }

    if layer_type == "Audio Reactive Layer":
        return {
            **base_layer,
            "name": f"Audio Reactive Layer {new_id}",
            "type": "audio_reactive",
        }

    return {
        **base_layer,
        "name": f"Layer {new_id}",
        "type": "solid_color",
        "color": "#ffffff",
    }


# --- Effects ---

EFFECT_TYPES = {
    "Visual": [
        "Grayscale",
        "Gaussian Blur",
        "Cursor Distortion",
    ],
}

EFFECT_SCHEMAS = {
    "grayscale": [
        {"key": "params.strength", "label": "Strength", "widget": "float", "min": 0.0, "max": 1.0},
    ],
    "blur": [
        {"key": "params.radius", "label": "Radius", "widget": "int", "min": 1, "max": 50},
    ],
    "distortion": [
        {"key": "params.strength", "label": "Strength", "widget": "float", "min": 0.0, "max": 1.0},
        {"key": "params.radius", "label": "Radius", "widget": "float", "min": 0.0, "max": 1.0},
    ],
}

EFFECT_SHARED_SCHEMA = [
    {"key": "name", "label": "Name", "widget": "text"},
]

EFFECT_TYPE_MAP = {
    "Grayscale": ("grayscale", {"strength": 1.0}),
    "Gaussian Blur": ("blur", {"radius": 5}),
    "Cursor Distortion": ("distortion", {"strength": 0.5, "radius": 0.3}),
}


def create_effect(effects: list, layer_id: int, effect_type_name: str) -> dict:
    max_id = 0
    max_hierarchy = 0

    for effect in effects:
        eid = effect.get("id")
        if isinstance(eid, int) and eid > max_id:
            max_id = eid

        if effect.get("layer_id") == layer_id:
            hierarchy = effect.get("hierarchy")
            if isinstance(hierarchy, int) and hierarchy > max_hierarchy:
                max_hierarchy = hierarchy

    new_id = max_id + 1
    new_hierarchy = max_hierarchy + 1

    type_key, default_params = EFFECT_TYPE_MAP.get(effect_type_name, ("grayscale", {"strength": 1.0}))

    return {
        "id": new_id,
        "layer_id": layer_id,
        "hierarchy": new_hierarchy,
        "name": effect_type_name,
        "type": type_key,
        "params": dict(default_params),
    }


def resolve_effect_hierarchy(effects: list, layer_id: int) -> bool:
    used = set()
    highest = 0
    changed = False

    for effect in effects:
        if effect.get("layer_id") != layer_id:
            continue

        hierarchy = effect.get("hierarchy")
        if isinstance(hierarchy, int) and hierarchy > 0 and hierarchy not in used:
            used.add(hierarchy)
            if hierarchy > highest:
                highest = hierarchy
            continue

        next_h = highest + 1
        while next_h in used:
            next_h += 1

        effect["hierarchy"] = next_h
        used.add(next_h)
        highest = next_h
        changed = True

    return changed


def get_schema_for_effect(effect: dict) -> list:
    effect_type = effect.get("type", "")
    type_schema = EFFECT_SCHEMAS.get(effect_type, [])
    return EFFECT_SHARED_SCHEMA + type_schema
