from . import effects_image
from . import effects_video


# do we have modules?
_MODULES = {
    "image": effects_image,
    "video": effects_video,
}


EFFECT_SHARED_SCHEMA = [
    {"key": "name", "label": "Name", "widget": "text"},
]


def has_effects(layer_type: str) -> bool:
    return layer_type in _MODULES


def get_dialog_types(layer_type: str) -> dict:

    mod = _MODULES.get(layer_type)
    if mod is None:
        return {}
    return mod.EFFECT_TYPES


def get_built_types(layer_type: str) -> set:

    mod = _MODULES.get(layer_type)
    if mod is None:
        return set()
    return mod.BUILT_EFFECTS


def get_type_map_entry(layer_type: str, display_name: str) -> tuple:

    mod = _MODULES.get(layer_type)
    if mod is None:
        return ("unknown", {})
    return mod.EFFECT_TYPE_MAP.get(display_name, ("unknown", {}))


def get_schema(effect_type_key: str) -> list:

    for mod in _MODULES.values():
        schema = mod.EFFECT_SCHEMAS.get(effect_type_key)
        if schema is not None:
            return EFFECT_SHARED_SCHEMA + schema
    # Unknown effect – show name only
    return list(EFFECT_SHARED_SCHEMA)

# How the fuck will I add the harder effects?
