"""
Text rendering engine.

Responsibilities:
  • Word-wrap text to fit a target width
  • Binary-search for the largest font size that fits a bounding area
  • Render multi-line text with shadow, glow, and stroke effects
  • Draw badge/label pills with rounded corners
"""

from __future__ import annotations

from typing import Tuple, Optional

from PIL import Image, ImageDraw, ImageFilter

from core.gradient import hex_to_rgb, hex_to_rgba
from core.font_manager import font_manager
from core.effects import create_shadow_layer, create_glow_layer
from core.config import ThumbnailConfig


# ─── Word-wrap ────────────────────────────────────────────────────────────────

def wrap_text(text: str, font, max_width: int) -> str:
    """Break *text* into lines whose rendered width ≤ *max_width*."""
    if not text.strip():
        return text

    words = text.split()
    lines: list[str] = []
    current: list[str] = []

    for word in words:
        trial = " ".join(current + [word])
        bbox = font.getbbox(trial)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
                current = [word]
            else:
                # Single word wider than allowed — force it through
                lines.append(word)
    if current:
        lines.append(" ".join(current))

    return "\n".join(lines) if lines else text


def _text_block_size(text: str, font, spacing: int = 6) -> Tuple[int, int]:
    """Return (width, height) of a potentially multi-line text block."""
    dummy = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


# ─── Auto-size ────────────────────────────────────────────────────────────────

def fit_font_size(
    text: str,
    style: str,
    max_width: int,
    max_height: int,
    min_size: int = 18,
    max_size: int = 260,
    spacing: int = 6,
) -> Tuple[int, str]:
    """Binary-search the largest font size where *text* (wrapped) fits the area.

    Returns (optimal_size, wrapped_text).
    """
    lo, hi = min_size, max_size
    best_size = min_size
    best_wrapped = text

    while lo <= hi:
        mid = (lo + hi) // 2
        font = font_manager.get_font(style, mid)
        wrapped = wrap_text(text, font, max_width)
        tw, th = _text_block_size(wrapped, font, spacing)

        if tw <= max_width and th <= max_height:
            best_size = mid
            best_wrapped = wrapped
            lo = mid + 1
        else:
            hi = mid - 1

    return best_size, best_wrapped


# ─── Core render call ─────────────────────────────────────────────────────────

def render_text(
    canvas: Image.Image,
    text: str,
    position: Tuple[int, int],
    font,
    color: str,
    cfg: ThumbnailConfig,
    spacing: int = 6,
    align: str = "left",
) -> Image.Image:
    """Composite one text element (with shadow / glow / stroke) onto *canvas*.

    *position* is the top-left corner of the text block.
    """
    if not text.strip():
        return canvas

    canvas = canvas.convert("RGBA")
    size = canvas.size

    # ── Shadow ─────────────────────────────────────────────────────────────
    if cfg.shadow:
        shadow = create_shadow_layer(
            size, text, position, font,
            shadow_color=cfg.shadow_color,
            offset=(cfg.shadow_offset_x, cfg.shadow_offset_y),
            blur=cfg.shadow_blur,
            spacing=spacing,
        )
        canvas = Image.alpha_composite(canvas, shadow)

    # ── Glow ───────────────────────────────────────────────────────────────
    if cfg.glow:
        glow_col = cfg.glow_color if cfg.glow_color else cfg.accent_color
        glow = create_glow_layer(
            size, text, position, font,
            glow_color=glow_col,
            radius=cfg.glow_radius,
            spacing=spacing,
        )
        canvas = Image.alpha_composite(canvas, glow)

    # ── Main text layer ────────────────────────────────────────────────────
    text_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    r, g, b = hex_to_rgb(color)

    stroke_fill = None
    stroke_w = 0
    if cfg.stroke:
        sr, sg, sb = hex_to_rgb(cfg.stroke_color)
        stroke_fill = (sr, sg, sb, 255)
        stroke_w = cfg.stroke_width

    draw.multiline_text(
        position,
        text,
        font=font,
        fill=(r, g, b, 255),
        spacing=spacing,
        stroke_width=stroke_w,
        stroke_fill=stroke_fill,
        align=align,
    )

    canvas = Image.alpha_composite(canvas, text_layer)
    return canvas


# ─── Badge / label pill ───────────────────────────────────────────────────────

def draw_badge(
    canvas: Image.Image,
    label: str,
    position: Tuple[int, int],
    bg_color: str,
    text_color: str,
    font,
    padding_x: int = 22,
    padding_y: int = 10,
    radius: int = 14,
) -> Tuple[Image.Image, int]:
    """Draw a rounded-rectangle badge at *position* and return (canvas, badge_width)."""
    canvas = canvas.convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    bbox = font.getbbox(label)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    badge_w = tw + padding_x * 2
    badge_h = th + padding_y * 2

    x, y = position
    br, bg, bb = hex_to_rgb(bg_color)
    draw.rounded_rectangle(
        [(x, y), (x + badge_w, y + badge_h)],
        radius=radius,
        fill=(br, bg, bb, 245),
    )

    tr, tg, tb = hex_to_rgb(text_color)
    text_x = x + padding_x
    text_y = y + padding_y - bbox[1]  # compensate for ascender offset
    draw.text((text_x, text_y), label, font=font, fill=(tr, tg, tb, 255))

    return canvas, badge_w + 12  # 12px gap between badges


# ─── Highlight box behind text ────────────────────────────────────────────────

def draw_text_highlight_box(
    canvas: Image.Image,
    area: Tuple[int, int, int, int],   # x1, y1, x2, y2
    color: str,
    opacity: int = 60,
    radius: int = 16,
) -> Image.Image:
    """Draw a semi-transparent rounded rectangle behind a text area."""
    canvas = canvas.convert("RGBA")
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    r, g, b = hex_to_rgb(color)
    x1, y1, x2, y2 = area
    draw.rounded_rectangle([(x1, y1), (x2, y2)], radius=radius, fill=(r, g, b, opacity))

    return Image.alpha_composite(canvas, layer)
