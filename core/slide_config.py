"""
SlideConfig dataclass — holds every parameter for a single slide render.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class SlideConfig:
    # ── Layout type ──────────────────────────────────────────────────────────
    layout_type: str = "standard"
    # choices: standard | code_focus | two_column | numbered_steps | quote
    #          checklist | comparison | statistic | terminal | tip_card
    #          top_n | centered | timeline

    # ── Primary content ──────────────────────────────────────────────────────
    title: str = ""
    subtitle: str = ""
    body_text: str = ""

    # ── List content ─────────────────────────────────────────────────────────
    bullet_points: List[str] = field(default_factory=list)
    numbered_steps: List[str] = field(default_factory=list)
    checklist_items: List[str] = field(default_factory=list)  # ✓/○ items

    # ── Code / terminal ──────────────────────────────────────────────────────
    code_snippet: str = ""
    code_language: str = "python"         # python | js | bash | html | generic
    terminal_commands: List[str] = field(default_factory=list)

    # ── Quote / statistic / comparison ───────────────────────────────────────
    quote_author: str = ""
    stat_number: str = ""                 # e.g. "97%"
    stat_label: str = ""                  # e.g. "of developers use Git"
    comparison_left_title: str = ""
    comparison_right_title: str = ""
    comparison_left_items: List[str] = field(default_factory=list)
    comparison_right_items: List[str] = field(default_factory=list)
    timeline_items: List[str] = field(default_factory=list)   # for timeline layout

    # ── Supplementary ────────────────────────────────────────────────────────
    footer_text: str = ""
    watermark: str = ""
    tags: List[str] = field(default_factory=list)
    image_path: str = ""                  # optional background/icon image

    # ── Step progress ────────────────────────────────────────────────────────
    show_step_number: bool = False
    step_number: int = 1
    show_progress: bool = False
    progress_total: int = 5
    progress_current: int = 1

    # ── Format ───────────────────────────────────────────────────────────────
    ratio: str = "16:9"                   # 16:9 | 9:16 | 1:1
    width: int = 1920
    height: int = 1080

    # ── Theme ────────────────────────────────────────────────────────────────
    theme: str = "dark_modern"

    # ── Output ───────────────────────────────────────────────────────────────
    filename: str = "slide"

    # ── Optional overrides (empty = use theme default) ────────────────────────
    bg_type: str = ""
    bg_colors: List[str] = field(default_factory=list)
    gradient_direction: str = ""
    title_color: str = ""
    subtitle_color: str = ""
    body_color: str = ""
    accent_color: str = ""

    # ─────────────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SlideConfig":
        valid = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in valid})

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, s: str) -> "SlideConfig":
        return cls.from_dict(json.loads(s))
