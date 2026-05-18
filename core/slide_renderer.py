"""
Slide rendering pipeline.

SlideRenderer.render(config) -> PIL Image
SlideRenderer.save(config, output_dir) -> Path
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict

from PIL import Image, ImageFilter

from core.slide_config import SlideConfig
from core.slide_themes import get_slide_theme
from core.gradient import create_gradient, hex_to_rgb
from core.effects import (
    add_vignette, add_dark_overlay, add_accent_bar,
    add_scanlines, add_particles, add_grid_pattern, add_hex_pattern,
)
from core.layouts import dispatch, _theme_overlay


class SlideRenderer:
    """Full rendering pipeline for information slides."""

    def __init__(self, cfg: SlideConfig) -> None:
        self.cfg = cfg
        self.W = cfg.width
        self.H = cfg.height

    # ── Public API ────────────────────────────────────────────────────────────

    def render(self) -> Image.Image:
        # Merge user overrides on top of theme
        theme = self._build_theme()

        canvas = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 255))

        # 1 – Background
        canvas = self._render_background(canvas, theme)

        # 2 – Background image overlay
        if self.cfg.image_path:
            canvas = self._overlay_image(canvas)

        # 3 – Theme decorative overlays (scanlines, particles, grid…)
        canvas = _theme_overlay(canvas, theme, self.cfg)

        # 4 – Dark overlay (if theme requests it)
        if theme.get("bg_overlay_opacity", 0) > 0:
            canvas = add_dark_overlay(canvas, theme["bg_overlay_opacity"])

        # 5 – Content via layout engine
        canvas = dispatch(self.cfg.layout_type, canvas, self.cfg, theme)

        # 6 – Bottom accent bar
        if theme.get("accent_bar_bottom"):
            thickness = max(5, self.H // 120)
            canvas = add_accent_bar(canvas, theme["accent_color"], "bottom", thickness)

        # 7 – Vignette (dark themes only)
        light_themes = {"minimal", "apple_style"}
        if theme.get("_theme_name") not in light_themes:
            canvas = add_vignette(canvas, strength=0.38)

        return canvas.convert("RGB")

    def save(self, output_dir: str = "output") -> Path:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = self.cfg.filename or "slide"
        path = out / f"{name}_{ts}.png"
        self.render().save(str(path), "PNG")
        return path

    # ── Internals ─────────────────────────────────────────────────────────────

    def _build_theme(self) -> Dict:
        """Start from the preset theme, apply user colour overrides."""
        base = get_slide_theme(self.cfg.theme).copy()
        base["_theme_name"] = self.cfg.theme

        # Per-field user overrides
        overrides = {
            "bg_type":            self.cfg.bg_type,
            "bg_colors":          self.cfg.bg_colors,
            "gradient_direction": self.cfg.gradient_direction,
            "title_color":        self.cfg.title_color,
            "subtitle_color":     self.cfg.subtitle_color,
            "body_color":         self.cfg.body_color,
            "accent_color":       self.cfg.accent_color,
        }
        for key, val in overrides.items():
            if val:  # only override when user explicitly set something
                base[key] = val

        return base

    def _render_background(self, canvas: Image.Image, theme: Dict) -> Image.Image:
        bg_type = theme.get("bg_type", "gradient")
        colors  = theme.get("bg_colors", ["#0d1117", "#161b22"])
        direction = theme.get("gradient_direction", "vertical")

        if bg_type == "solid":
            r, g, b = hex_to_rgb(colors[0] if colors else "#0d1117")
            bg = Image.new("RGB", (self.W, self.H), (r, g, b))
        elif bg_type == "gradient":
            bg = create_gradient(self.W, self.H, colors, direction)
        else:
            bg = Image.new("RGB", (self.W, self.H), (13, 17, 23))

        return Image.alpha_composite(canvas, bg.convert("RGBA"))

    def _overlay_image(self, canvas: Image.Image) -> Image.Image:
        try:
            img = Image.open(self.cfg.image_path).convert("RGBA")
            # Smart fill
            scale = max(self.W / img.width, self.H / img.height)
            nw, nh = int(img.width * scale), int(img.height * scale)
            img = img.resize((nw, nh), Image.LANCZOS)
            left = (nw - self.W) // 2
            top  = (nh - self.H) // 2
            img  = img.crop((left, top, left + self.W, top + self.H))

            # Dim the background image so text remains readable
            from PIL import ImageEnhance
            img_rgb = img.convert("RGB")
            img_rgb = ImageEnhance.Brightness(img_rgb).enhance(0.45)

            # Blur for depth
            img_rgb = img_rgb.filter(ImageFilter.GaussianBlur(radius=8))
            canvas = Image.alpha_composite(canvas, img_rgb.convert("RGBA"))
        except Exception:
            pass
        return canvas


# ── Convenience ───────────────────────────────────────────────────────────────

def render_slide_and_save(cfg: SlideConfig, output_dir: str = "output") -> Path:
    return SlideRenderer(cfg).save(output_dir)
