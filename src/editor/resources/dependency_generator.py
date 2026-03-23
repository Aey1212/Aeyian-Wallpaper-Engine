#!/usr/bin/env python3


import json
import math
from pathlib import Path


OUTPUT_DIR = Path.home() / ".config" / "aeyian-wallpaper-engine"
BLUR_FILE = OUTPUT_DIR / "blur_transliteration.json"
MAX_RADIUS = 50


_LOD_CENTERS = [0.1, 0.3, 0.5, 0.7, 0.9, 1.1]

_MIP_EFFECTIVE_BLUR = [1.5, 3.0, 6.0, 12.0, 24.0, 48.0]


def _fastblur_lod(radius: float) -> float:
    return math.sqrt(radius / 64.0) * 1.2 - 0.2


def _fastblur_weight(v: float) -> float:
    if v <= 0.0:
        return 1.0
    if v >= 0.5:
        return 0.0
    return 1.0 - v * 2.0


def _fastblur_effective_blur(radius: float) -> float:
    lod = _fastblur_lod(radius)
    weights = [_fastblur_weight(abs(lod - c)) for c in _LOD_CENTERS]
    wsum = sum(weights)
    if wsum == 0.0:
        return 0.0
    return sum(w * b for w, b in zip(weights, _MIP_EFFECTIVE_BLUR)) / wsum


def _find_fastblur_radius(gaussian_radius: float) -> float:
    target = float(gaussian_radius)
    lo, hi = 0.0, 100.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        if _fastblur_effective_blur(mid) < target:
            lo = mid
        else:
            hi = mid
    return min(100.0, round((lo + hi) / 2.0, 1))


def generate_blur_transliteration() -> list:
    mapping = [0.0]  # radius 0 to 0? IDK this works acc. to overflow

    for g in range(1, MAX_RADIUS + 1):
        f = _find_fastblur_radius(g)
        eff = _fastblur_effective_blur(f)
        mapping.append(f)
        print(f"  Gaussian {g:2d} -> FastBlur {f:6.1f}  (effective={eff:.1f})")

    return mapping


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating blur_transliteration.json ...")
    mapping = generate_blur_transliteration()
    data = {"gaussian_to_fastblur": mapping}
    BLUR_FILE.write_text(json.dumps(data, indent=2))
    print(f"\nWritten to {BLUR_FILE}")
    print(f"Mapping has {len(mapping)} entries (radius 0-{MAX_RADIUS})")


if __name__ == "__main__":
    main()
