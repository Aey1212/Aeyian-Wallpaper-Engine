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
