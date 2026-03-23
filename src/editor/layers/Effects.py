import multiprocessing
from concurrent.futures import ProcessPoolExecutor

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QColor, QPainter
from PySide6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem, QGraphicsBlurEffect
from PySide6.QtGui import QPixmap

from . import effects_image
from . import effects_video

# TODO: When cpu_count() <= 1, skip pool creation and fall back - for potato pc

_POOL_WORKERS = min(6, multiprocessing.cpu_count())
_fork_ctx = multiprocessing.get_context("fork")
_pool = ProcessPoolExecutor(max_workers=_POOL_WORKERS, mp_context=_fork_ctx)


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


# ---------------------------------------------------------------------------
# FUCK hue_shift & oversaturation. If you are reading this then know that I am fucking feeling physical pain over this.
# TODO: solve hue & oversaturation
# ---------------------------------------------------------------------------


def _rgb_to_hsl(r: int, g: int, b: int) -> tuple:

    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    cmax = max(rf, gf, bf)
    cmin = min(rf, gf, bf)
    delta = cmax - cmin
    l = (cmax + cmin) / 2.0

    if delta == 0.0:
        return (-1, 0, int(l * 1000))

    if l < 0.5:
        s = delta / (cmax + cmin)
    else:
        s = delta / (2.0 - cmax - cmin)

    if cmax == rf:
        h = ((gf - bf) / delta) % 6.0
    elif cmax == gf:
        h = (bf - rf) / delta + 2.0
    else:
        h = (rf - gf) / delta + 4.0
    h = h * 60.0
    if h < 0:
        h += 360.0

    return (int(h), int(s * 1000), int(l * 1000))


def _hsl_to_rgb(h: int, s: int, l: int) -> tuple:

    lf = l / 1000.0
    if h < 0 or s == 0:
        v = max(0, min(255, int(lf * 255)))
        return (v, v, v)

    sf = s / 1000.0
    if lf < 0.5:
        c2 = lf * (1.0 + sf)
    else:
        c2 = lf + sf - lf * sf
    c1 = 2.0 * lf - c2

    hf = h / 360.0

    def hue_to_rgb(p, q, t):
        if t < 0: t += 1.0
        if t > 1: t -= 1.0
        if t < 1/6: return p + (q - p) * 6.0 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6.0
        return p

    r = max(0, min(255, int(hue_to_rgb(c1, c2, hf + 1/3) * 255)))
    g = max(0, min(255, int(hue_to_rgb(c1, c2, hf) * 255)))
    b = max(0, min(255, int(hue_to_rgb(c1, c2, hf - 1/3) * 255)))
    return (r, g, b)


def _apply_grayscale(img: QImage, params: dict) -> QImage:
    strength = max(0.0, min(1.0, params.get("strength", 1.0)))
    if strength == 0.0:
        return img
    result = img.copy()
    gray = img.convertToFormat(QImage.Format.Format_Grayscale8)
    gray = gray.convertToFormat(QImage.Format.Format_ARGB32)
    painter = QPainter(result)
    painter.setOpacity(strength)
    painter.drawImage(0, 0, gray)
    painter.end()
    return result


def _apply_blur(img: QImage, params: dict) -> QImage:
    radius = max(1, min(50, int(params.get("radius", 5))))
    pixmap = QPixmap.fromImage(img)
    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(pixmap)
    blur = QGraphicsBlurEffect()
    blur.setBlurRadius(radius)
    blur.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(blur)
    scene.addItem(item)

    result = QImage(img.size(), QImage.Format.Format_ARGB32)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    scene.render(painter, QRectF(result.rect()), QRectF(pixmap.rect()))
    painter.end()
    return result


def _apply_brightness(img: QImage, params: dict) -> QImage:
    brightness = max(-1.0, min(1.0, params.get("brightness", 0.0)))
    if brightness == 0.0:
        return img
    result = img.copy()
    painter = QPainter(result)
    if brightness > 0:
        # Lighten: add white at proportional alpha
        overlay = QColor(255, 255, 255, int(brightness * 255))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
    else:
        # Darken: multiply with gray - this is closest to the plugin version
        gray_val = int((1.0 + brightness) * 255)
        overlay = QColor(gray_val, gray_val, gray_val, 255)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
    painter.fillRect(result.rect(), overlay)
    painter.end()
    return result


def _hue_shift_chunk(args):

    data, shift_deg = args
    buf = bytearray(data)
    pixels = memoryview(buf).cast('I')
    _int = int

    for idx in range(len(pixels)):
        px = pixels[idx]
        r = (px >> 16) & 0xFF
        g = (px >> 8) & 0xFF
        b = px & 0xFF

        # --- inlined RGB to HSL ---
        rf = r / 255.0
        gf = g / 255.0
        bf = b / 255.0
        if rf > gf:
            cmax = rf; cmin = gf
        else:
            cmax = gf; cmin = rf
        if bf > cmax:
            cmax = bf
        elif bf < cmin:
            cmin = bf
        delta = cmax - cmin

        if delta == 0.0:
            continue  # achromatic

        l = (cmax + cmin) * 0.5
        if l < 0.5:
            s = delta / (cmax + cmin)
        else:
            s = delta / (2.0 - cmax - cmin)

        if cmax == rf:
            h = ((gf - bf) / delta) % 6.0
        elif cmax == gf:
            h = (bf - rf) / delta + 2.0
        else:
            h = (rf - gf) / delta + 4.0
        h = h * 60.0
        if h < 0.0:
            h += 360.0

        h = (_int(h) + shift_deg) % 360
        s = _int(s * 1000.0)
        l = _int(l * 1000.0)

        # --- inlined HSL to RGB ---
        lf = l * 0.001
        sf = s * 0.001
        if lf < 0.5:
            c2 = lf * (1.0 + sf)
        else:
            c2 = lf + sf - lf * sf
        c1 = 2.0 * lf - c2
        hf = h / 360.0

        # R channel
        t = hf + 0.3333333333333333
        if t > 1.0:
            t -= 1.0
        if t < 0.16666666666666666:
            rn = c1 + (c2 - c1) * 6.0 * t
        elif t < 0.5:
            rn = c2
        elif t < 0.6666666666666666:
            rn = c1 + (c2 - c1) * (0.6666666666666666 - t) * 6.0
        else:
            rn = c1

        # G channel
        t = hf
        if t < 0.16666666666666666:
            gn = c1 + (c2 - c1) * 6.0 * t
        elif t < 0.5:
            gn = c2
        elif t < 0.6666666666666666:
            gn = c1 + (c2 - c1) * (0.6666666666666666 - t) * 6.0
        else:
            gn = c1

        # B channel
        t = hf - 0.3333333333333333
        if t < 0.0:
            t += 1.0
        if t < 0.16666666666666666:
            bn = c1 + (c2 - c1) * 6.0 * t
        elif t < 0.5:
            bn = c2
        elif t < 0.6666666666666666:
            bn = c1 + (c2 - c1) * (0.6666666666666666 - t) * 6.0
        else:
            bn = c1

        rn = _int(rn * 255.0)
        gn = _int(gn * 255.0)
        bn = _int(bn * 255.0)
        pixels[idx] = (px & 0xFF000000) | \
            ((0 if rn < 0 else 255 if rn > 255 else rn) << 16) | \
            ((0 if gn < 0 else 255 if gn > 255 else gn) << 8) | \
            (0 if bn < 0 else 255 if bn > 255 else bn)

    return bytes(buf)


def _apply_hue_shift(img: QImage, params: dict) -> QImage:
    shift = params.get("shift", 0.0)
    if shift == 0.0:
        return img
    shift_deg = int(shift * 360.0)
    result = img.convertToFormat(QImage.Format.Format_ARGB32)
    result = result.copy()

    raw = bytes(memoryview(result.bits()).cast('B'))
    n_bytes = len(raw)
    chunk_size = ((n_bytes // _POOL_WORKERS) // 4) * 4  # 4 align
    if chunk_size == 0:
        chunk_size = n_bytes

    tasks = []
    for i in range(0, n_bytes, chunk_size):
        tasks.append((raw[i:i + chunk_size], shift_deg))

    parts = list(_pool.map(_hue_shift_chunk, tasks))

    dest = memoryview(result.bits()).cast('B')
    offset = 0
    for part in parts:
        dest[offset:offset + len(part)] = part
        offset += len(part)

    return result


def _oversaturate_chunk(args):

    data, strength = args
    buf = bytearray(data)
    pixels = memoryview(buf).cast('I')
    _int = int

    for idx in range(len(pixels)):
        px = pixels[idx]
        r = (px >> 16) & 0xFF
        g = (px >> 8) & 0xFF
        b = px & 0xFF

        # --- inlined RGB to HSL ---
        rf = r / 255.0
        gf = g / 255.0
        bf = b / 255.0
        if rf > gf:
            cmax = rf; cmin = gf
        else:
            cmax = gf; cmin = rf
        if bf > cmax:
            cmax = bf
        elif bf < cmin:
            cmin = bf
        delta = cmax - cmin

        if delta == 0.0:
            continue  # achromatic

        l = (cmax + cmin) * 0.5
        if l < 0.5:
            s = delta / (cmax + cmin)
        else:
            s = delta / (2.0 - cmax - cmin)

        if cmax == rf:
            h = ((gf - bf) / delta) % 6.0
        elif cmax == gf:
            h = (bf - rf) / delta + 2.0
        else:
            h = (rf - gf) / delta + 4.0
        h = h * 60.0
        if h < 0.0:
            h += 360.0

        h = _int(h)
        s_boosted = _int(s * 1000.0 * strength)
        if s_boosted > 1000:
            s_boosted = 1000
        l = _int(l * 1000.0)

        # --- inlined HSL to RGB ---
        lf = l * 0.001
        sf = s_boosted * 0.001
        if lf < 0.5:
            c2 = lf * (1.0 + sf)
        else:
            c2 = lf + sf - lf * sf
        c1 = 2.0 * lf - c2
        hf = h / 360.0

        # R channel
        t = hf + 0.3333333333333333
        if t > 1.0:
            t -= 1.0
        if t < 0.16666666666666666:
            rn = c1 + (c2 - c1) * 6.0 * t
        elif t < 0.5:
            rn = c2
        elif t < 0.6666666666666666:
            rn = c1 + (c2 - c1) * (0.6666666666666666 - t) * 6.0
        else:
            rn = c1

        # G channel
        t = hf
        if t < 0.16666666666666666:
            gn = c1 + (c2 - c1) * 6.0 * t
        elif t < 0.5:
            gn = c2
        elif t < 0.6666666666666666:
            gn = c1 + (c2 - c1) * (0.6666666666666666 - t) * 6.0
        else:
            gn = c1

        # B chanel
        t = hf - 0.3333333333333333
        if t < 0.0:
            t += 1.0
        if t < 0.16666666666666666:
            bn = c1 + (c2 - c1) * 6.0 * t
        elif t < 0.5:
            bn = c2
        elif t < 0.6666666666666666:
            bn = c1 + (c2 - c1) * (0.6666666666666666 - t) * 6.0
        else:
            bn = c1

        rn = _int(rn * 255.0)
        gn = _int(gn * 255.0)
        bn = _int(bn * 255.0)
        pixels[idx] = (px & 0xFF000000) | \
            ((0 if rn < 0 else 255 if rn > 255 else rn) << 16) | \
            ((0 if gn < 0 else 255 if gn > 255 else gn) << 8) | \
            (0 if bn < 0 else 255 if bn > 255 else bn)

    return bytes(buf)


def _apply_saturation(img: QImage, params: dict) -> QImage:
    strength = max(0.0, min(2.0, params.get("strength", 1.0)))
    if strength == 1.0:
        return img
    if strength <= 1.0:
        # Desaturate
        gray = img.convertToFormat(QImage.Format.Format_Grayscale8)
        result = gray.convertToFormat(QImage.Format.Format_ARGB32)
        painter = QPainter(result)
        painter.setOpacity(strength)
        painter.drawImage(0, 0, img)
        painter.end()
        return result
    else:
        # Oversaturate
        result = img.convertToFormat(QImage.Format.Format_ARGB32)
        result = result.copy()

        raw = bytes(memoryview(result.bits()).cast('B'))
        n_bytes = len(raw)
        chunk_size = ((n_bytes // _POOL_WORKERS) // 4) * 4
        if chunk_size == 0:
            chunk_size = n_bytes

        tasks = []
        for i in range(0, n_bytes, chunk_size):
            tasks.append((raw[i:i + chunk_size], strength))

        parts = list(_pool.map(_oversaturate_chunk, tasks))

        dest = memoryview(result.bits()).cast('B')
        offset = 0
        for part in parts:
            dest[offset:offset + len(part)] = part
            offset += len(part)

        return result


def _apply_tint(img: QImage, params: dict) -> QImage:
    color_str = params.get("color", "#ffffff")
    strength = max(0.0, min(1.0, params.get("strength", 0.5)))
    if strength == 0.0:
        return img
    overlay_color = QColor(color_str)
    overlay_color.setAlphaF(strength)
    result = img.copy()
    painter = QPainter(result)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
    painter.fillRect(result.rect(), overlay_color)
    painter.end()
    return result


_EFFECT_PROCESSORS = {
    "grayscale":  _apply_grayscale,
    "blur":       _apply_blur,
    "brightness": _apply_brightness,
    "hue_shift":  _apply_hue_shift,
    "saturation": _apply_saturation,
    "tint":       _apply_tint,
}


def apply_effects_to_image(effects_list: list, img: QImage) -> QImage:

    result = img
    for fx in effects_list:
        fx_type = fx.get("type", "")
        processor = _EFFECT_PROCESSORS.get(fx_type)
        if processor is None:
            continue
        params = fx.get("params", {})
        result = processor(result, params)
    return result

# How the fuck will I add the harder effects?
