"""
Stand-alone visual effects applied to PIL images.

All functions accept and return RGBA PIL Images so they can be freely
composed in the rendering pipeline.
"""

from __future__ import annotations

import math
import random
from typing import Tuple

from PIL import Image, ImageDraw, ImageFilter

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    import array as _array
    _HAS_NUMPY = False

from core.gradient import hex_to_rgb, hex_to_rgba


# ─── Vignette ────────────────────────────────────────────────────────────────

def add_vignette(image: Image.Image, strength: float = 0.6) -> Image.Image:
    """Darken the edges of *image* with a radial vignette."""
    img = image.convert("RGBA")
    w, h = img.size
    cx, cy = w / 2, h / 2
    max_r = math.sqrt(cx ** 2 + cy ** 2)

    if _HAS_NUMPY:
        x = np.linspace(0, w - 1, w) - cx
        y = (np.linspace(0, h - 1, h) - cy).reshape(-1, 1)
        dist = np.sqrt(x ** 2 + y ** 2) / max_r
        darkness = np.clip(dist * strength, 0, 1)
        alpha = (darkness * 200).astype(np.uint8)
        zeros = np.zeros_like(alpha)
        vignette_layer = Image.fromarray(
            np.stack([zeros, zeros, zeros, alpha], axis=-1), "RGBA"
        )
    else:
        # Pure-PIL fast path: render a tiny vignette then resize — smooth and fast.
        # 120×68 is 120× fewer pixels than 1280×720 yet resizes smooth.
        SMALL_W, SMALL_H = 120, 68
        cx_s, cy_s = SMALL_W / 2.0, SMALL_H / 2.0
        diag = math.sqrt(2.0)   # normalise to [0, 1]
        pixels = []
        for sy in range(SMALL_H):
            dy = (sy - cy_s) / cy_s
            for sx in range(SMALL_W):
                dx = (sx - cx_s) / cx_s
                r = math.sqrt(dx * dx + dy * dy) / diag
                a = int(min(r * strength, 1.0) * 195)
                pixels.append((0, 0, 0, a))
        small = Image.new("RGBA", (SMALL_W, SMALL_H), (0, 0, 0, 0))
        small.putdata(pixels)
        vignette_layer = small.resize((w, h), Image.BILINEAR)

    return Image.alpha_composite(img, vignette_layer)


# ─── Film grain / noise ───────────────────────────────────────────────────────

def add_noise(image: Image.Image, intensity: float = 0.04) -> Image.Image:
    """Add subtle film-grain noise to *image*."""
    img = image.convert("RGBA")

    if _HAS_NUMPY:
        arr = np.array(img, dtype=np.int16)
        noise = np.random.randint(
            int(-255 * intensity),
            int(255 * intensity) + 1,
            (arr.shape[0], arr.shape[1], 3),
            dtype=np.int16,
        )
        arr[:, :, :3] = np.clip(arr[:, :, :3] + noise, 0, 255)
        return Image.fromarray(arr.astype(np.uint8), "RGBA")
    else:
        # Skip noise when numpy is absent — minor cosmetic difference only
        return img


# ─── Scanlines ────────────────────────────────────────────────────────────────

def add_scanlines(image: Image.Image, gap: int = 4, opacity: int = 35) -> Image.Image:
    """Overlay horizontal scanlines (gaming aesthetic)."""
    img = image.convert("RGBA")
    w, h = img.size
    lines = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(lines)
    for y in range(0, h, gap):
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, opacity))
    return Image.alpha_composite(img, lines)


# ─── Glitch lines ─────────────────────────────────────────────────────────────

def add_glitch(image: Image.Image, seed: int = 42) -> Image.Image:
    """Add a handful of horizontal RGB-offset glitch stripes (cyberpunk)."""
    img = image.convert("RGBA")
    w, h = img.size
    rng = random.Random(seed)

    for _ in range(rng.randint(4, 10)):
        y = rng.randint(0, h - 1)
        stripe_h = rng.randint(1, 6)
        shift = rng.randint(-30, 30)
        region = img.crop((0, y, w, min(y + stripe_h, h)))

        # shift red channel slightly
        r_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        r_layer.paste(region, (shift, y))
        img = Image.alpha_composite(img, r_layer)

    return img


# ─── Dark overlay ─────────────────────────────────────────────────────────────

def add_dark_overlay(image: Image.Image, opacity: int = 40) -> Image.Image:
    """Paint a semi-transparent black rectangle over the whole image."""
    img = image.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([(0, 0), img.size], fill=(0, 0, 0, opacity))
    return Image.alpha_composite(img, overlay)


# ─── Grid / circuit pattern ───────────────────────────────────────────────────

def add_grid_pattern(
    image: Image.Image,
    color: str = "#ffffff",
    opacity: int = 18,
    spacing: int = 60,
) -> Image.Image:
    """Subtle technical grid overlay (tech / finance theme)."""
    img = image.convert("RGBA")
    w, h = img.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    r, g, b = hex_to_rgb(color)
    line_color = (r, g, b, opacity)

    for x in range(0, w, spacing):
        draw.line([(x, 0), (x, h)], fill=line_color, width=1)
    for y in range(0, h, spacing):
        draw.line([(0, y), (w, y)], fill=line_color, width=1)

    return Image.alpha_composite(img, layer)


# ─── Hex grid ────────────────────────────────────────────────────────────────

def add_hex_pattern(
    image: Image.Image,
    color: str = "#7c4dff",
    opacity: int = 20,
    size: int = 50,
) -> Image.Image:
    """Hexagonal grid overlay (AI / futuristic theme)."""
    img = image.convert("RGBA")
    w, h = img.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    r, g, b = hex_to_rgb(color)
    lc = (r, g, b, opacity)

    dx = size * 2
    dy = int(size * math.sqrt(3))

    row = 0
    y = 0
    while y < h + size:
        x_offset = size if row % 2 else 0
        x = -size + x_offset
        while x < w + size:
            cx_h, cy_h = x, y
            pts = [
                (cx_h + size * math.cos(math.radians(60 * i)),
                 cy_h + size * math.sin(math.radians(60 * i)))
                for i in range(6)
            ]
            draw.polygon(pts, outline=lc)
            x += dx
        y += dy
        row += 1

    return Image.alpha_composite(img, layer)


# ─── Particle dots ────────────────────────────────────────────────────────────

def add_particles(
    image: Image.Image,
    color: str = "#ffffff",
    count: int = 80,
    seed: int = 7,
) -> Image.Image:
    """Scatter glowing particle dots (gaming / AI theme)."""
    img = image.convert("RGBA")
    w, h = img.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    rng = random.Random(seed)
    r, g, b = hex_to_rgb(color)

    for _ in range(count):
        px = rng.randint(0, w)
        py = rng.randint(0, h)
        radius = rng.randint(1, 4)
        alpha = rng.randint(60, 200)
        draw.ellipse(
            [(px - radius, py - radius), (px + radius, py + radius)],
            fill=(r, g, b, alpha),
        )

    return Image.alpha_composite(img, layer)


# ─── Accent bar ──────────────────────────────────────────────────────────────

def add_accent_bar(
    image: Image.Image,
    color: str,
    position: str = "bottom",
    thickness: int = 8,
) -> Image.Image:
    """Draw a solid accent stripe along an edge."""
    img = image.convert("RGBA")
    w, h = img.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    r, g, b = hex_to_rgb(color)
    fill = (r, g, b, 255)

    if position == "bottom":
        draw.rectangle([(0, h - thickness), (w, h)], fill=fill)
    elif position == "top":
        draw.rectangle([(0, 0), (w, thickness)], fill=fill)
    elif position == "left":
        draw.rectangle([(0, 0), (thickness, h)], fill=fill)

    return Image.alpha_composite(img, layer)


# ─── Cinematic letterbox bars ─────────────────────────────────────────────────

def add_cinematic_bars(image: Image.Image, bar_ratio: float = 0.12) -> Image.Image:
    """Add black letterbox bars top and bottom."""
    img = image.convert("RGBA")
    w, h = img.size
    bar_h = int(h * bar_ratio)

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rectangle([(0, 0), (w, bar_h)], fill=(0, 0, 0, 245))
    draw.rectangle([(0, h - bar_h), (w, h)], fill=(0, 0, 0, 245))

    return Image.alpha_composite(img, layer)


# ─── Text glow helper (used by text_engine) ───────────────────────────────────

def create_glow_layer(
    size: Tuple[int, int],
    text: str,
    position: Tuple[int, int],
    font,
    glow_color: str,
    radius: int,
    spacing: int = 6,
) -> Image.Image:
    """Return a blurred RGBA glow layer for a block of text."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    r, g, b = hex_to_rgb(glow_color)
    draw.multiline_text(position, text, font=font, fill=(r, g, b, 190), spacing=spacing)
    return layer.filter(ImageFilter.GaussianBlur(radius=radius))


def create_shadow_layer(
    size: Tuple[int, int],
    text: str,
    position: Tuple[int, int],
    font,
    shadow_color: str,
    offset: Tuple[int, int],
    blur: int,
    spacing: int = 6,
) -> Image.Image:
    """Return a blurred RGBA shadow layer for a block of text."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    r, g, b, a = hex_to_rgba(shadow_color)
    sx, sy = position[0] + offset[0], position[1] + offset[1]
    draw.multiline_text((sx, sy), text, font=font, fill=(r, g, b, a), spacing=spacing)
    return layer.filter(ImageFilter.GaussianBlur(radius=blur))
