"""
History tracking.
Every successful render appends an entry to history/history.json.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from core.config import ThumbnailConfig

_HISTORY_FILE = Path("history") / "history.json"


class HistoryManager:

    def __init__(self, history_file: str = "history/history.json") -> None:
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    # ─── Add entry ────────────────────────────────────────────────────────

    def add(self, cfg: ThumbnailConfig, output_path: str) -> None:
        records = self._load_all()
        records.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "output_path": str(output_path),
            "title": cfg.title,
            "theme": cfg.theme,
            "resolution": f"{cfg.width}x{cfg.height}",
            "config": cfg.to_dict(),
        })
        self._save_all(records)

    # ─── Read ─────────────────────────────────────────────────────────────

    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        records = self._load_all()
        return records[-n:][::-1]  # newest first

    def count(self) -> int:
        return len(self._load_all())

    # ─── Internal ─────────────────────────────────────────────────────────

    def _load_all(self) -> List[Dict[str, Any]]:
        if not self.history_file.exists():
            return []
        try:
            return json.loads(self.history_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_all(self, records: List[Dict[str, Any]]) -> None:
        self.history_file.write_text(
            json.dumps(records, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# Module-level singleton
history_manager = HistoryManager()
