import json
from pathlib import Path

from .L_Dialog import AddLayerDialog, LAYER_TYPES


def toggle_layer_visibility(project_path: Path, layers: list, layer_id: int, visible: bool):
    for layer in layers:
        if layer.get("id") == layer_id:
            layer["visible"] = visible
            break

    manifest_path = project_path / "project.json"
    data = json.loads(manifest_path.read_text())
    data["layers"] = layers
    manifest_path.write_text(json.dumps(data, indent=2))
