"""
Font discovery and loading.

Search order:
  1. assets/fonts/  (project-local fonts)
  2. Common system paths (Linux / macOS / Windows)
  3. PIL built-in scalable default (Pillow ≥ 10.1)
  4. PIL tiny bitmap default (last resort)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from functools import lru_cache
from typing import Optional

from PIL import ImageFont

# ─── Font name candidates per style ──────────────────────────────────────────

_FONT_CANDIDATES = {
    # ── Monospace — used for code blocks and terminal ─────────────────────────
    "mono": [
        "DejaVuSansMono.ttf",
        "DejaVuSansMono-Bold.ttf",
        "UbuntuMono-Regular.ttf",
        "UbuntuMono-Bold.ttf",
        "FreeMonoBold.ttf",
        "FreeMono.ttf",
        "CourierNew.ttf",
        "Courier New.ttf",
        "cour.ttf",
        "LiberationMono-Regular.ttf",
        "NotoMono-Regular.ttf",
        "DejaVuSans-Bold.ttf",      # graceful non-mono fallback
    ],
    "bold": [
        "DejaVuSans-Bold.ttf",
        "Ubuntu-Bold.ttf",
        "Roboto-Bold.ttf",
        "FreeSansBold.ttf",
        "Arial Bold.ttf",
        "arialbd.ttf",
        "Helvetica Bold.ttf",
        "LiberationSans-Bold.ttf",
        "NotoSans-Bold.ttf",
    ],
    "regular": [
        "DejaVuSans.ttf",
        "Ubuntu-Regular.ttf",
        "Roboto-Regular.ttf",
        "FreeSans.ttf",
        "arial.ttf",
        "Arial.ttf",
        "LiberationSans-Regular.ttf",
        "NotoSans-Regular.ttf",
    ],
    "impact": [
        "Impact.ttf",
        "impact.ttf",
        "DejaVuSans-Bold.ttf",       # fallback to bold
        "Ubuntu-Bold.ttf",
        "FreeSansBold.ttf",
        "LiberationSans-Bold.ttf",
    ],
    "condensed": [
        "DejaVuSansCondensed-Bold.ttf",
        "Roboto-Condensed.ttf",
        "ArialNarrow.ttf",
        "DejaVuSans-Bold.ttf",
        "Ubuntu-Bold.ttf",
    ],
}

# ─── System search paths ─────────────────────────────────────────────────────

def _system_font_dirs() -> list[Path]:
    dirs: list[Path] = []

    # Project-local first
    dirs.append(Path(__file__).resolve().parent.parent / "assets" / "fonts")

    platform = sys.platform
    if platform.startswith("linux"):
        dirs += [
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            Path.home() / ".fonts",
            Path.home() / ".local/share/fonts",
        ]
    elif platform == "darwin":
        dirs += [
            Path("/Library/Fonts"),
            Path("/System/Library/Fonts"),
            Path.home() / "Library/Fonts",
        ]
    elif platform.startswith("win"):
        dirs += [
            Path("C:/Windows/Fonts"),
            Path(os.environ.get("LOCALAPPDATA", "C:/Users")) / "Microsoft/Windows/Fonts",
        ]

    return dirs


def _walk_find_font(filename: str, search_dirs: list[Path]) -> Optional[Path]:
    """Recursively search *search_dirs* for *filename* (case-insensitive)."""
    fname_lower = filename.lower()
    for base in search_dirs:
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.name.lower() == fname_lower:
                return path
    return None


# ─── Public API ──────────────────────────────────────────────────────────────

class FontManager:
    """Locate and cache TrueType fonts."""

    def __init__(self) -> None:
        self._search_dirs = _system_font_dirs()
        self._cache: dict[tuple, ImageFont.FreeTypeFont] = {}

    @lru_cache(maxsize=None)
    def find_font_path(self, style: str) -> Optional[Path]:
        """Return the first usable TTF path for *style*, or None."""
        candidates = _FONT_CANDIDATES.get(style, _FONT_CANDIDATES["bold"])
        for name in candidates:
            path = _walk_find_font(name, self._search_dirs)
            if path is not None:
                return path
        return None

    def get_font(self, style: str = "bold", size: int = 80) -> ImageFont.FreeTypeFont:
        """Return a loaded font.  Falls back gracefully if no TTF is found."""
        cache_key = (style, size)
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self.find_font_path(style)
        font: ImageFont.FreeTypeFont

        if path is not None:
            try:
                font = ImageFont.truetype(str(path), size)
                self._cache[cache_key] = font
                return font
            except Exception:
                pass

        # Pillow ≥ 10.1 supports size= on the built-in scalable font
        try:
            font = ImageFont.load_default(size=size)  # type: ignore[call-arg]
            self._cache[cache_key] = font
            return font
        except TypeError:
            pass

        # Absolute last resort — tiny bitmap, no size control
        return ImageFont.load_default()


# Module-level singleton so callers can just do `from core.font_manager import font_manager`
font_manager = FontManager()
