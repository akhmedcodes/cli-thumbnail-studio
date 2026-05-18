"""
Shared drawing utilities used by both the thumbnail and slide renderers.

All functions operate on RGBA PIL Images and return RGBA PIL Images
so they compose freely in any pipeline.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter

from core.gradient import hex_to_rgb, hex_to_rgba


# ─── Scaling ─────────────────────────────────────────────────────────────────

def sv(value: int, dimension: int, base: int = 1080) -> int:
    """Scale *value* proportionally from *base* to *dimension*."""
    return max(int(value * dimension / base), max(4, int(value * 0.35)))


# ─── Rounded-rectangle card ──────────────────────────────────────────────────

def draw_card(
    canvas: Image.Image,
    x1: int, y1: int, x2: int, y2: int,
    radius: int,
    fill: str,
    fill_alpha: int = 255,
    border: Optional[str] = None,
    border_width: int = 2,
    shadow: bool = True,
    shadow_color: str = "#00000077",
    shadow_blur: int = 18,
    shadow_offset: int = 6,
) -> Image.Image:
    """Draw a solid-filled rounded card, optionally with a drop shadow."""
    canvas = canvas.convert("RGBA")
    W, H = canvas.size

    if shadow:
        sh_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sh_draw = ImageDraw.Draw(sh_layer)
        sr, sg, sb, sa = hex_to_rgba(shadow_color)
        sh_draw.rounded_rectangle(
            [(x1 + shadow_offset, y1 + shadow_offset),
             (x2 + shadow_offset, y2 + shadow_offset)],
            radius=radius, fill=(sr, sg, sb, sa),
        )
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
        canvas = Image.alpha_composite(canvas, sh_layer)

    card_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_layer)
    cr, cg, cb = hex_to_rgb(fill)
    card_draw.rounded_rectangle(
        [(x1, y1), (x2, y2)],
        radius=radius,
        fill=(cr, cg, cb, fill_alpha),
        outline=None,
    )
    if border:
        br, bg, bb = hex_to_rgb(border)
        card_draw.rounded_rectangle(
            [(x1, y1), (x2, y2)],
            radius=radius, fill=None,
            outline=(br, bg, bb, 255), width=border_width,
        )

    return Image.alpha_composite(canvas, card_layer)


# ─── Glassmorphism card ───────────────────────────────────────────────────────

def draw_glass_card(
    canvas: Image.Image,
    x1: int, y1: int, x2: int, y2: int,
    radius: int = 16,
    blur_radius: int = 18,
    tint: str = "#ffffff",
    tint_alpha: int = 28,
    border: str = "#ffffff",
    border_alpha: int = 70,
) -> Image.Image:
    """Draw a frosted-glass card: blurs whatever is behind it."""
    canvas = canvas.convert("RGBA")
    W, H = canvas.size

    # Clamp to canvas bounds
    cx1, cy1 = max(0, x1), max(0, y1)
    cx2, cy2 = min(W, x2), min(H, y2)
    if cx2 <= cx1 or cy2 <= cy1:
        return canvas

    region = canvas.crop((cx1, cy1, cx2, cy2))
    blurred = region.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    mask = Image.new("L", (cx2 - cx1, cy2 - cy1), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [(0, 0), (cx2 - cx1, cy2 - cy1)], radius=radius, fill=255
    )
    blurred_rgba = blurred.convert("RGBA")
    blurred_rgba.putalpha(mask)
    canvas.paste(blurred_rgba, (cx1, cy1), mask)

    # Tinted overlay
    ovl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    r, g, b = hex_to_rgb(tint)
    ImageDraw.Draw(ovl).rounded_rectangle(
        [(x1, y1), (x2, y2)], radius=radius, fill=(r, g, b, tint_alpha)
    )
    canvas = Image.alpha_composite(canvas, ovl)

    # Border
    brd = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    br, bg, bb = hex_to_rgb(border)
    ImageDraw.Draw(brd).rounded_rectangle(
        [(x1, y1), (x2, y2)], radius=radius,
        fill=None, outline=(br, bg, bb, border_alpha), width=2,
    )
    return Image.alpha_composite(canvas, brd)


# ─── Glow elements ────────────────────────────────────────────────────────────

def draw_glow_rect(
    canvas: Image.Image,
    x1: int, y1: int, x2: int, y2: int,
    color: str,
    radius: int = 8,
    glow_radius: int = 20,
    alpha: int = 160,
) -> Image.Image:
    """Draw a glowing rounded rectangle border (no fill)."""
    canvas = canvas.convert("RGBA")
    W, H = canvas.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    r, g, b = hex_to_rgb(color)
    ImageDraw.Draw(layer).rounded_rectangle(
        [(x1, y1), (x2, y2)], radius=radius,
        fill=None, outline=(r, g, b, alpha), width=3,
    )
    blurred = layer.filter(ImageFilter.GaussianBlur(radius=glow_radius))
    canvas = Image.alpha_composite(canvas, blurred)
    canvas = Image.alpha_composite(canvas, layer)
    return canvas


def draw_glow_text(
    canvas: Image.Image,
    text: str,
    position: Tuple[int, int],
    font,
    color: str,
    glow_radius: int = 16,
    spacing: int = 6,
) -> Image.Image:
    """Draw text with a matching colour glow behind it."""
    canvas = canvas.convert("RGBA")
    W, H = canvas.size
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    r, g, b = hex_to_rgb(color)
    ImageDraw.Draw(glow_layer).multiline_text(
        position, text, font=font, fill=(r, g, b, 180), spacing=spacing
    )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=glow_radius))
    canvas = Image.alpha_composite(canvas, glow_layer)

    text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(text_layer).multiline_text(
        position, text, font=font, fill=(r, g, b, 255), spacing=spacing
    )
    return Image.alpha_composite(canvas, text_layer)


# ─── Accent left-border card ─────────────────────────────────────────────────

def draw_accent_card(
    canvas: Image.Image,
    x1: int, y1: int, x2: int, y2: int,
    fill: str,
    accent_color: str,
    radius: int = 10,
    bar_width: int = 6,
) -> Image.Image:
    """Card with a solid accent stripe on the left edge."""
    canvas = draw_card(canvas, x1, y1, x2, y2, radius, fill, shadow=True)
    canvas = canvas.convert("RGBA")
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    r, g, b = hex_to_rgb(accent_color)
    # Left accent bar (only top-left rounded)
    ImageDraw.Draw(layer).rounded_rectangle(
        [(x1, y1), (x1 + bar_width, y2)],
        radius=min(radius, bar_width // 2),
        fill=(r, g, b, 255),
    )
    return Image.alpha_composite(canvas, layer)


# ─── Divider line ─────────────────────────────────────────────────────────────

def draw_divider(
    canvas: Image.Image,
    x1: int, y: int, x2: int,
    color: str,
    thickness: int = 2,
    opacity: int = 120,
) -> Image.Image:
    canvas = canvas.convert("RGBA")
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    r, g, b = hex_to_rgb(color)
    ImageDraw.Draw(layer).line([(x1, y), (x2, y)], fill=(r, g, b, opacity), width=thickness)
    return Image.alpha_composite(canvas, layer)


# ─── Pill badge ──────────────────────────────────────────────────────────────

def draw_pill(
    canvas: Image.Image,
    text: str,
    x: int, y: int,
    bg: str,
    fg: str,
    font,
    pad_x: int = 18,
    pad_y: int = 8,
    radius: int = 100,
) -> Tuple[Image.Image, int]:
    """Draw a pill badge. Returns (canvas, badge_width)."""
    bb = font.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    bw = tw + pad_x * 2
    bh = th + pad_y * 2

    canvas = canvas.convert("RGBA")
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    r, g, b = hex_to_rgb(bg)
    ImageDraw.Draw(layer).rounded_rectangle(
        [(x, y), (x + bw, y + bh)], radius=radius, fill=(r, g, b, 240)
    )
    canvas = Image.alpha_composite(canvas, layer)

    text_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    tr, tg, tb = hex_to_rgb(fg)
    text_x = x + pad_x - bb[0]
    text_y = y + pad_y - bb[1]
    ImageDraw.Draw(text_layer).text((text_x, text_y), text, font=font, fill=(tr, tg, tb, 255))
    canvas = Image.alpha_composite(canvas, text_layer)

    return canvas, bw


# ─── Circle (for step numbers, timeline) ─────────────────────────────────────

def draw_circle(
    canvas: Image.Image,
    cx: int, cy: int, radius: int,
    fill: str,
    border: Optional[str] = None,
    border_width: int = 3,
    fill_alpha: int = 255,
) -> Image.Image:
    canvas = canvas.convert("RGBA")
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    r, g, b = hex_to_rgb(fill)
    ImageDraw.Draw(layer).ellipse(
        [(cx - radius, cy - radius), (cx + radius, cy + radius)],
        fill=(r, g, b, fill_alpha),
        outline=hex_to_rgb(border) + (255,) if border else None,
        width=border_width,
    )
    return Image.alpha_composite(canvas, layer)


# ─── Filled progress bar ──────────────────────────────────────────────────────

def draw_progress_bar(
    canvas: Image.Image,
    x: int, y: int, width: int, height: int,
    percent: float,           # 0.0 – 1.0
    track_color: str,
    fill_color: str,
    radius: int = 100,
) -> Image.Image:
    canvas = canvas.convert("RGBA")
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    tr, tg, tb = hex_to_rgb(track_color)
    fr, fg, fb = hex_to_rgb(fill_color)
    # Track
    draw.rounded_rectangle([(x, y), (x + width, y + height)], radius=radius, fill=(tr, tg, tb, 80))
    # Fill
    fill_w = max(height, int(width * min(percent, 1.0)))
    draw.rounded_rectangle([(x, y), (x + fill_w, y + height)], radius=radius, fill=(fr, fg, fb, 255))
    return Image.alpha_composite(canvas, layer)


# ─── Text measurement ─────────────────────────────────────────────────────────

def measure_text(text: str, font, spacing: int = 6) -> Tuple[int, int]:
    """Return (width, height) of a (possibly multiline) text block."""
    dummy = Image.new("RGB", (1, 1))
    bb = ImageDraw.Draw(dummy).multiline_textbbox((0, 0), text, font=font, spacing=spacing)
    return bb[2] - bb[0], bb[3] - bb[1]


def draw_multiline(
    canvas: Image.Image,
    text: str,
    pos: Tuple[int, int],
    font,
    color: str,
    spacing: int = 6,
    align: str = "left",
    alpha: int = 255,
) -> Image.Image:
    """Render multiline text onto canvas."""
    canvas = canvas.convert("RGBA")
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    r, g, b = hex_to_rgb(color)
    ImageDraw.Draw(layer).multiline_text(
        pos, text, font=font, fill=(r, g, b, alpha),
        spacing=spacing, align=align,
    )
    return Image.alpha_composite(canvas, layer)
