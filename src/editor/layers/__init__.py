import json
from pathlib import Path

from .L_Dialog import AddLayerDialog, LAYER_TYPES


SHARED_SCHEMA = [
    {"key": "name", "label": "Name", "widget": "text"},
    {"key": "visible", "label": "Visible", "widget": "bool"},
    {"key": "position.x", "label": "X", "widget": "int"},
    {"key": "position.y", "label": "Y", "widget": "int"},
    {"key": "size.width", "label": "Width", "widget": "int"},
    {"key": "size.height", "label": "Height", "widget": "int"},
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
