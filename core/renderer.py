"""
Main thumbnail rendering pipeline.

ThumbnailRenderer.render(config) → PIL Image → saved PNG
"""

from __future__ import annotations

import math
from pathlib import Path
from datetime import datetime
from typing import Tuple

from PIL import Image, ImageDraw, ImageFilter

from core.config import ThumbnailConfig
from core.gradient import create_gradient, hex_to_rgb
from core.font_manager import font_manager
from core.text_engine import fit_font_size, render_text, draw_badge, draw_text_highlight_box
from core.effects import (
    add_vignette,
    add_dark_overlay,
    add_grid_pattern,
    add_hex_pattern,
    add_particles,
    add_scanlines,
    add_glitch,
    add_accent_bar,
    add_cinematic_bars,
    add_noise,
)


# ─── Layout areas ─────────────────────────────────────────────────────────────
# Each entry defines (x1, y1, x2, y2) as fractions of (width, height).
# Values are relative so they work for any resolution.

_LAYOUT_FRACTIONS = {
    "centered": {
        "title":    (0.05, 0.12, 0.95, 0.62),
        "subtitle": (0.08, 0.62, 0.92, 0.82),
        "labels":   (0.08, 0.82, 0.92, 0.93),
        "align": "center",
    },
    "left_aligned": {
        "title":    (0.05, 0.10, 0.80, 0.65),
        "subtitle": (0.05, 0.65, 0.80, 0.83),
        "labels":   (0.05, 0.83, 0.80, 0.93),
        "align": "left",
    },
    "modern_youtube": {
        "title":    (0.04, 0.06, 0.96, 0.60),
        "subtitle": (0.04, 0.62, 0.96, 0.82),
        "labels":   (0.04, 0.83, 0.96, 0.93),
        "align": "left",
    },
    "cinematic": {
        # cinematic bars eat 12 % top + bottom; content in remaining 76 %
        "title":    (0.05, 0.16, 0.95, 0.68),
        "subtitle": (0.05, 0.69, 0.95, 0.82),
        "labels":   (0.05, 0.83, 0.95, 0.88),
        "align": "center",
    },
}


def _frac_to_px(frac: Tuple[float, float, float, float], w: int, h: int) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = frac
    return int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h)


class ThumbnailRenderer:
    """Render a ThumbnailConfig into a PIL Image and save it to disk."""

    def __init__(self, cfg: ThumbnailConfig) -> None:
        self.cfg = cfg
        self.W = cfg.width
        self.H = cfg.height

    # ─── Public entry point ───────────────────────────────────────────────

    def render(self) -> Image.Image:
        canvas = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 255))

        # Step 1 – background
        canvas = self._render_background(canvas)

        # Step 2 – background filters
        canvas = self._apply_bg_filters(canvas)

        # Step 3 – theme-specific decorative layer
        canvas = self._apply_decorations(canvas)

        # Step 4 – dark overlay (after decorations so patterns stay visible)
        if self.cfg.overlay:
            canvas = add_dark_overlay(canvas, self.cfg.overlay_opacity * 255 // 100)

        # Step 5 – text (title, subtitle, labels)
        canvas = self._render_all_text(canvas)

        # Step 6 – accent bar (bottom edge)
        canvas = add_accent_bar(canvas, self.cfg.accent_color, "bottom", thickness=max(6, self.H // 135))

        # Step 7 – cinematic bars (on top of everything)
        if self.cfg.cinematic_bars:
            canvas = add_cinematic_bars(canvas, bar_ratio=0.12)

        # Step 8 – subtle vignette (skip for light-bg themes to avoid artefacts)
        if self.cfg.theme not in ("minimal",):
            canvas = add_vignette(canvas, strength=0.45)

        # Step 9 – very light noise for texture
        canvas = add_noise(canvas, intensity=0.015)

        return canvas.convert("RGB")

    # ─── Save convenience ──────────────────────────────────────────────────

    def save(self, output_dir: str = "output") -> Path:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = self.cfg.filename or "thumbnail"
        filepath = output_path / f"{stem}_{timestamp}.png"

        image = self.render()
        image.save(str(filepath), "PNG", quality=95)
        return filepath

    # ─── Background ───────────────────────────────────────────────────────

    def _render_background(self, canvas: Image.Image) -> Image.Image:
        bt = self.cfg.bg_type

        if bt == "solid":
            colors = self.cfg.bg_colors
            c = colors[0] if colors else "#000000"
            r, g, b = hex_to_rgb(c)
            bg = Image.new("RGB", (self.W, self.H), (r, g, b))

        elif bt == "gradient":
            bg = create_gradient(
                self.W, self.H,
                self.cfg.bg_colors,
                self.cfg.gradient_direction,
            )

        elif bt == "image":
            try:
                bg = Image.open(self.cfg.bg_image_path).convert("RGB")
                # Smart crop/resize to fill canvas
                bg = self._smart_fill(bg)
            except Exception:
                # Fallback to gradient on bad path
                bg = create_gradient(self.W, self.H, ["#111111", "#222222"], "vertical")

        else:
            bg = Image.new("RGB", (self.W, self.H), (20, 20, 20))

        return Image.alpha_composite(canvas, bg.convert("RGBA"))

    def _smart_fill(self, img: Image.Image) -> Image.Image:
        """Resize + centre-crop image to exactly (W, H)."""
        iw, ih = img.size
        scale = max(self.W / iw, self.H / ih)
        new_w, new_h = int(iw * scale), int(ih * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - self.W) // 2
        top = (new_h - self.H) // 2
        return img.crop((left, top, left + self.W, top + self.H))

    # ─── Background filters ───────────────────────────────────────────────

    def _apply_bg_filters(self, canvas: Image.Image) -> Image.Image:
        if self.cfg.blur_bg:
            canvas = canvas.filter(ImageFilter.GaussianBlur(radius=self.cfg.blur_radius))
        return canvas

    # ─── Theme decorations ────────────────────────────────────────────────

    def _apply_decorations(self, canvas: Image.Image) -> Image.Image:
        theme = self.cfg.theme

        if theme == "gaming":
            canvas = add_scanlines(canvas, gap=4, opacity=28)
            canvas = add_particles(canvas, color=self.cfg.accent_color, count=90, seed=3)

        elif theme == "tech":
            canvas = add_grid_pattern(canvas, color="#00d4ff", opacity=14, spacing=70)
            canvas = add_particles(canvas, color="#0066ff", count=50, seed=9)

        elif theme == "cyberpunk":
            canvas = add_glitch(canvas, seed=21)
            canvas = add_particles(canvas, color="#ff00ff", count=60, seed=5)

        elif theme == "dark":
            canvas = add_vignette(canvas, strength=0.5)

        elif theme == "ai_futuristic":
            canvas = add_hex_pattern(canvas, color=self.cfg.accent_color, opacity=22, size=45)
            canvas = add_particles(canvas, color="#b0b0ff", count=120, seed=17)

        elif theme == "finance":
            canvas = add_grid_pattern(canvas, color="#ffd700", opacity=10, spacing=80)

        elif theme == "educational":
            canvas = add_particles(canvas, color="#ffffff", count=30, seed=11)

        return canvas

    # ─── Text rendering ───────────────────────────────────────────────────

    def _render_all_text(self, canvas: Image.Image) -> Image.Image:
        layout_key = self.cfg.positioning
        if layout_key not in _LAYOUT_FRACTIONS:
            layout_key = "modern_youtube"

        fracs = _LAYOUT_FRACTIONS[layout_key]
        align = fracs["align"]

        title_area = _frac_to_px(fracs["title"], self.W, self.H)
        sub_area   = _frac_to_px(fracs["subtitle"], self.W, self.H)
        lbl_area   = _frac_to_px(fracs["labels"], self.W, self.H)

        # ── Title ──────────────────────────────────────────────────────────
        if self.cfg.title:
            canvas = self._render_title(canvas, title_area, align)

        # ── Subtitle ───────────────────────────────────────────────────────
        if self.cfg.subtitle:
            canvas = self._render_subtitle(canvas, sub_area, align)

        # ── Labels ─────────────────────────────────────────────────────────
        if self.cfg.labels:
            canvas = self._render_labels(canvas, lbl_area)

        return canvas

    def _render_title(
        self,
        canvas: Image.Image,
        area: Tuple[int, int, int, int],
        align: str,
    ) -> Image.Image:
        x1, y1, x2, y2 = area
        max_w = x2 - x1
        max_h = y2 - y1
        padding_x = int(self.W * 0.02)

        size, wrapped = fit_font_size(
            self.cfg.title,
            self.cfg.font_style,
            max_w - padding_x * 2,
            max_h,
            min_size=28,
            max_size=260,
        )
        font = font_manager.get_font(self.cfg.font_style, size)

        # Calculate position
        pos = self._calc_text_position(wrapped, font, area, align, spacing=6)

        # Optional semi-transparent highlight box behind title for readability
        if self.cfg.theme in ("educational", "minimal"):
            dummy = Image.new("RGB", (1, 1))
            draw = ImageDraw.Draw(dummy)
            bb = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=6)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            pad = 18
            hx1 = pos[0] - pad
            hy1 = pos[1] - pad
            hx2 = pos[0] + tw + pad
            hy2 = pos[1] + th + pad
            bg_col = "#0d6efd" if self.cfg.theme == "minimal" else "#1a6985"
            canvas = draw_text_highlight_box(canvas, (hx1, hy1, hx2, hy2), bg_col, opacity=55, radius=14)

        canvas = render_text(canvas, wrapped, pos, font, self.cfg.text_color, self.cfg, spacing=6, align=align)
        return canvas

    def _render_subtitle(
        self,
        canvas: Image.Image,
        area: Tuple[int, int, int, int],
        align: str,
    ) -> Image.Image:
        x1, y1, x2, y2 = area
        max_w = x2 - x1
        max_h = y2 - y1
        padding_x = int(self.W * 0.02)

        # Subtitle is ~42–48 % of title weight — use a separate smaller search range
        size, wrapped = fit_font_size(
            self.cfg.subtitle,
            "regular",
            max_w - padding_x * 2,
            max_h,
            min_size=18,
            max_size=int(self.H * 0.075),
        )
        font = font_manager.get_font("regular", size)
        pos = self._calc_text_position(wrapped, font, area, align, spacing=4)

        # Temporarily disable stroke for subtitle
        orig_stroke = self.cfg.stroke
        self.cfg.stroke = False
        canvas = render_text(canvas, wrapped, pos, font, self.cfg.subtitle_color, self.cfg, spacing=4, align=align)
        self.cfg.stroke = orig_stroke
        return canvas

    def _render_labels(
        self,
        canvas: Image.Image,
        area: Tuple[int, int, int, int],
    ) -> Image.Image:
        x1, y1, x2, y2 = area
        badge_font_size = max(22, int(self.H * 0.030))
        font = font_manager.get_font("bold", badge_font_size)

        cursor_x = x1
        cursor_y = y1

        for label in self.cfg.labels:
            canvas, badge_w = draw_badge(
                canvas,
                label.upper(),
                (cursor_x, cursor_y),
                self.cfg.label_bg_color,
                self.cfg.label_text_color,
                font,
                padding_x=max(16, int(self.W * 0.012)),
                padding_y=max(8, int(self.H * 0.009)),
                radius=max(10, int(self.H * 0.014)),
            )
            cursor_x += badge_w
            # Wrap to next row if overflowing
            if cursor_x > area[2]:
                cursor_x = x1
                cursor_y += int(self.H * 0.07)

        return canvas

    # ─── Position calculation ─────────────────────────────────────────────

    def _calc_text_position(
        self,
        text: str,
        font,
        area: Tuple[int, int, int, int],
        align: str,
        spacing: int = 6,
    ) -> Tuple[int, int]:
        """Return the top-left pixel position that places *text* according to *align* within *area*."""
        x1, y1, x2, y2 = area
        aw = x2 - x1
        ah = y2 - y1
        pad_x = int(self.W * 0.025)

        dummy = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(dummy)
        bb = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        off_x = bb[0]
        off_y = bb[1]

        if align == "center":
            px = x1 + (aw - tw) // 2 - off_x
        elif align == "right":
            px = x2 - tw - pad_x - off_x
        else:  # left
            px = x1 + pad_x - off_x

        # Vertically: align to top of area with some breathing room
        py = y1 + max(0, (ah - th) // 4) - off_y

        return px, py


# ─── Module-level convenience function ───────────────────────────────────────

def render_and_save(cfg: ThumbnailConfig, output_dir: str = "output") -> Path:
    """One-shot render + save. Returns the saved file path."""
    renderer = ThumbnailRenderer(cfg)
    return renderer.save(output_dir)
