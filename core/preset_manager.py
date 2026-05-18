"""
Preset save / load system.
Presets are stored as JSON files in the *presets/* folder.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from core.config import ThumbnailConfig

_PRESET_DIR = Path("presets")


class PresetManager:

    def __init__(self, preset_dir: str = "presets") -> None:
        self.preset_dir = Path(preset_dir)
        self.preset_dir.mkdir(parents=True, exist_ok=True)

    # ─── Save ─────────────────────────────────────────────────────────────

    def save(self, name: str, cfg: ThumbnailConfig) -> Path:
        """Serialise *cfg* to presets/<name>.json and return the path."""
        name = self._sanitise(name)
        path = self.preset_dir / f"{name}.json"
        path.write_text(cfg.to_json(), encoding="utf-8")
        return path

    # ─── Load ─────────────────────────────────────────────────────────────

    def load(self, name: str) -> Optional[ThumbnailConfig]:
        """Load and return a ThumbnailConfig, or None if not found."""
        name = self._sanitise(name)
        path = self.preset_dir / f"{name}.json"
        if not path.exists():
            return None
        try:
            return ThumbnailConfig.from_json(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    # ─── List ─────────────────────────────────────────────────────────────

    def list_presets(self) -> List[str]:
        """Return sorted list of available preset names (without .json)."""
        return sorted(p.stem for p in self.preset_dir.glob("*.json"))

    def exists(self, name: str) -> bool:
        name = self._sanitise(name)
        return (self.preset_dir / f"{name}.json").exists()

    def delete(self, name: str) -> bool:
        name = self._sanitise(name)
        path = self.preset_dir / f"{name}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    # ─── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _sanitise(name: str) -> str:
        """Remove characters unsafe for filenames."""
        return "".join(c for c in name if c.isalnum() or c in "-_ ").strip().replace(" ", "_")


# Module-level singleton
preset_manager = PresetManager()
