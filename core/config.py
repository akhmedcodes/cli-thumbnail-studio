"""
Thumbnail configuration dataclass.
All settings for a single thumbnail generation are stored here.
"""

from dataclasses import dataclass, field, asdict
from typing import List
import json


@dataclass
class ThumbnailConfig:
    """Holds every parameter needed to render one thumbnail."""

    # ── Content ──────────────────────────────────────────────────────────
    title: str = "YOUR TITLE HERE"
    subtitle: str = ""
    labels: List[str] = field(default_factory=list)

    # ── Output ───────────────────────────────────────────────────────────
    filename: str = "thumbnail"

    # ── Format ───────────────────────────────────────────────────────────
    ratio: str = "16:9"          # "16:9" | "9:16"
    width: int = 1920
    height: int = 1080

    # ── Background ───────────────────────────────────────────────────────
    bg_type: str = "gradient"    # "solid" | "gradient" | "image"
    bg_colors: List[str] = field(default_factory=lambda: ["#1a1a2e", "#16213e", "#0f3460"])
    bg_image_path: str = ""
    gradient_direction: str = "diagonal"  # "horizontal" | "vertical" | "diagonal" | "radial"

    # ── Colors ───────────────────────────────────────────────────────────
    text_color: str = "#ffffff"
    subtitle_color: str = "#cccccc"
    accent_color: str = "#ff6b35"
    label_bg_color: str = "#ff6b35"
    label_text_color: str = "#ffffff"

    # ── Typography ───────────────────────────────────────────────────────
    font_style: str = "bold"     # "bold" | "regular" | "impact" | "condensed"

    # ── Shadow ───────────────────────────────────────────────────────────
    shadow: bool = True
    shadow_color: str = "#00000099"
    shadow_offset_x: int = 5
    shadow_offset_y: int = 5
    shadow_blur: int = 14

    # ── Stroke ───────────────────────────────────────────────────────────
    stroke: bool = False
    stroke_color: str = "#000000"
    stroke_width: int = 3

    # ── Overlay ──────────────────────────────────────────────────────────
    overlay: bool = True
    overlay_opacity: int = 30   # 0–100

    # ── Glow ─────────────────────────────────────────────────────────────
    glow: bool = False
    glow_color: str = ""        # empty → use accent_color
    glow_radius: int = 22

    # ── Background blur ──────────────────────────────────────────────────
    blur_bg: bool = False
    blur_radius: int = 6

    # ── Layout ───────────────────────────────────────────────────────────
    positioning: str = "modern_youtube"  # "centered" | "left_aligned" | "modern_youtube" | "cinematic"
    cinematic_bars: bool = False

    # ── Theme ────────────────────────────────────────────────────────────
    theme: str = "custom"

    # ──────────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ThumbnailConfig":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ThumbnailConfig":
        return cls.from_dict(json.loads(json_str))
