import json
from pathlib import Path

from .L_Dialog import AddLayerDialog, LAYER_TYPES


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
