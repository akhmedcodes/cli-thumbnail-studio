"""
Gradient generation engine.

Tries to use NumPy for speed; falls back to a pure-PIL implementation
so the tool works even when NumPy is not installed.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from PIL import Image

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


# ─── Colour utilities (used everywhere in the project) ───────────────────────

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Parse a hex colour string (#RRGGBB or #RGB) → (R, G, B)."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) >= 6:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return (128, 128, 128)


def hex_to_rgba(hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    """Parse a hex colour string → (R, G, B, A).

    Supports #RRGGBB (alpha from parameter) and #RRGGBBAA.
    """
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 8:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16))
    if len(h) == 6:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)
    return (128, 128, 128, alpha)


# ─── Colour interpolation helpers ────────────────────────────────────────────

def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _interp_stops(stops: List[Tuple[int, int, int]], t: float) -> Tuple[int, int, int]:
    """Interpolate across multiple colour stops for a scalar t ∈ [0, 1]."""
    if len(stops) == 1:
        return stops[0]
    n = len(stops) - 1
    segment = min(int(t * n), n - 1)
    local_t = t * n - segment
    c1, c2 = stops[segment], stops[segment + 1]
    return (_lerp(c1[0], c2[0], local_t),
            _lerp(c1[1], c2[1], local_t),
            _lerp(c1[2], c2[2], local_t))


# ─── NumPy path ──────────────────────────────────────────────────────────────

if _HAS_NUMPY:

    def _build_t_map(width: int, height: int, direction: str):
        import numpy as _np
        if direction == "horizontal":
            row = _np.linspace(0.0, 1.0, width, dtype=_np.float32)
            return _np.tile(row, (height, 1))
        if direction == "vertical":
            col = _np.linspace(0.0, 1.0, height, dtype=_np.float32).reshape(-1, 1)
            return _np.tile(col, (1, width))
        if direction == "diagonal":
            row = _np.linspace(0.0, 1.0, width, dtype=_np.float32)
            col = _np.linspace(0.0, 1.0, height, dtype=_np.float32).reshape(-1, 1)
            return ((row + col) / 2.0).astype(_np.float32)
        if direction == "radial":
            cx, cy = (width - 1) / 2.0, (height - 1) / 2.0
            x = (_np.arange(width,  dtype=_np.float32) - cx)
            y = (_np.arange(height, dtype=_np.float32) - cy).reshape(-1, 1)
            dist = _np.sqrt(x ** 2 + y ** 2)
            return _np.clip(dist / max(math.sqrt(cx ** 2 + cy ** 2), 1.0), 0.0, 1.0)
        # fallback
        row = _np.linspace(0.0, 1.0, width, dtype=_np.float32)
        return _np.tile(row, (height, 1))

    def _numpy_gradient(
        width: int, height: int, colors: List[str], direction: str
    ) -> Image.Image:
        import numpy as _np
        stops = _np.array([hex_to_rgb(c) for c in colors], dtype=_np.float32)
        t = _build_t_map(width, height, direction)
        n = len(stops) - 1
        result = _np.zeros((height, width, 3), dtype=_np.float32)
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            mask = (t >= t0) & (t < t1) if i < n - 1 else (t >= t0)
            local = _np.clip((t - t0) / max(t1 - t0, 1e-9), 0.0, 1.0)
            for ch in range(3):
                contrib = stops[i, ch] * (1 - local) + stops[i + 1, ch] * local
                result[:, :, ch] += _np.where(mask, contrib, 0.0)
        return Image.fromarray(_np.clip(result, 0, 255).astype(_np.uint8), "RGB")


# ─── Pure-PIL fallback ───────────────────────────────────────────────────────

def _pil_gradient(
    width: int, height: int, colors: List[str], direction: str
) -> Image.Image:
    """Pure-Python gradient — slower but dependency-free."""
    stops = [hex_to_rgb(c) for c in colors]

    if direction in ("horizontal", "diagonal"):
        # Build a 1-pixel-tall horizontal strip, then scale up
        strip = Image.new("RGB", (width, 1))
        pixels = [_interp_stops(stops, x / max(width - 1, 1)) for x in range(width)]
        strip.putdata(pixels)
        if direction == "horizontal":
            return strip.resize((width, height), Image.NEAREST)
        # Diagonal: blend horizontal + vertical strips
        v_strip = Image.new("RGB", (1, height))
        v_pixels = [_interp_stops(stops, y / max(height - 1, 1)) for y in range(height)]
        v_strip.putdata(v_pixels)
        v_full = v_strip.resize((width, height), Image.NEAREST)
        h_full = strip.resize((width, height), Image.NEAREST)
        # Average the two
        import PIL.ImageChops as chops
        return Image.blend(h_full, v_full, 0.5)

    if direction == "vertical":
        strip = Image.new("RGB", (1, height))
        pixels = [_interp_stops(stops, y / max(height - 1, 1)) for y in range(height)]
        strip.putdata(pixels)
        return strip.resize((width, height), Image.NEAREST)

    if direction == "radial":
        # Build row-by-row (acceptable speed for moderate resolutions)
        cx, cy = (width - 1) / 2.0, (height - 1) / 2.0
        max_r = math.sqrt(cx ** 2 + cy ** 2)
        img = Image.new("RGB", (width, height))
        pixels = []
        for y in range(height):
            dy = y - cy
            for x in range(width):
                dx = x - cx
                t = math.sqrt(dx * dx + dy * dy) / max(max_r, 1.0)
                pixels.append(_interp_stops(stops, min(t, 1.0)))
        img.putdata(pixels)
        return img

    # default horizontal
    strip = Image.new("RGB", (width, 1))
    pixels = [_interp_stops(stops, x / max(width - 1, 1)) for x in range(width)]
    strip.putdata(pixels)
    return strip.resize((width, height), Image.NEAREST)


# ─── Public API ──────────────────────────────────────────────────────────────

def create_gradient(
    width: int,
    height: int,
    colors: List[str],
    direction: str = "horizontal",
) -> Image.Image:
    """Create a gradient PIL Image.

    Parameters
    ----------
    width, height : image dimensions in pixels
    colors        : list of hex colour strings (at least one)
    direction     : 'horizontal' | 'vertical' | 'diagonal' | 'radial'
    """
    if not colors:
        colors = ["#000000"]

    if len(colors) == 1:
        r, g, b = hex_to_rgb(colors[0])
        img = Image.new("RGB", (width, height), (r, g, b))
        return img

    if _HAS_NUMPY:
        return _numpy_gradient(width, height, colors, direction)
    return _pil_gradient(width, height, colors, direction)
