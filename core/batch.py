"""
Batch generator and variation system.

BatchRenderer generates multiple variations of a config automatically:
  - Theme sweep:   same content, every theme
  - Layout sweep:  same content, every layout
  - Color sweep:   same config, accent/bg color variations
  - Ratio sweep:   16:9 and 9:16 side-by-side

HistoryBrowser shows the rendered history in a rich table.
"""

from __future__ import annotations

import concurrent.futures
import time
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table

from core.slide_config import SlideConfig
from core.slide_renderer import render_slide_and_save
from core.slide_themes import list_slide_themes
from core.layouts import LAYOUT_NAMES
from core.history_manager import history_manager
from core.preview import update_preview

console = Console()

_ACCENT_VARIATIONS = [
    "#58a6ff", "#3fb950", "#f78166", "#d2a8ff",
    "#ffa657", "#79c0ff", "#ff7b72", "#56d364",
]


def _render_one(args) -> Optional[Path]:
    """Worker fn for thread pool — args = (cfg, output_dir)."""
    cfg, output_dir = args
    try:
        return render_slide_and_save(cfg, output_dir)
    except Exception as e:
        console.print(f"  [red]✗ {e}[/]")
        return None


class BatchRenderer:
    """Generate many slides from a single base config."""

    def __init__(self, base_cfg: SlideConfig) -> None:
        self.base = base_cfg

    # ── Theme sweep ──────────────────────────────────────────────────────────

    def theme_sweep(self, output_dir: str = "output/batch_themes") -> List[Path]:
        """Render the same content in every available theme."""
        themes = list_slide_themes()
        jobs = []
        for theme in themes:
            from copy import deepcopy
            cfg = deepcopy(self.base)
            cfg.theme = theme
            cfg.filename = f"batch_{self.base.filename}_{theme}"
            jobs.append((cfg, output_dir))

        return self._run_parallel(jobs, label="Theme sweep")

    # ── Layout sweep ─────────────────────────────────────────────────────────

    def layout_sweep(self, output_dir: str = "output/batch_layouts") -> List[Path]:
        """Render the same content in every layout."""
        layouts = list(LAYOUT_NAMES.keys())
        jobs = []
        for layout in layouts:
            from copy import deepcopy
            cfg = deepcopy(self.base)
            cfg.layout_type = layout
            cfg.filename = f"batch_{self.base.filename}_{layout}"
            jobs.append((cfg, output_dir))

        return self._run_parallel(jobs, label="Layout sweep")

    # ── Accent color sweep ────────────────────────────────────────────────────

    def color_sweep(self, output_dir: str = "output/batch_colors") -> List[Path]:
        """Render the same config with 8 accent color variations."""
        jobs = []
        for i, accent in enumerate(_ACCENT_VARIATIONS):
            from copy import deepcopy
            cfg = deepcopy(self.base)
            cfg.accent_color = accent
            cfg.filename = f"batch_{self.base.filename}_color{i+1}"
            jobs.append((cfg, output_dir))

        return self._run_parallel(jobs, label="Color sweep")

    # ── Ratio sweep ───────────────────────────────────────────────────────────

    def ratio_sweep(self, output_dir: str = "output/batch_ratios") -> List[Path]:
        """Render in both 16:9 (1920×1080) and 9:16 (1080×1920)."""
        sizes = [("16:9", 1920, 1080), ("9:16", 1080, 1920), ("1:1", 1080, 1080)]
        jobs = []
        for ratio, w, h in sizes:
            from copy import deepcopy
            cfg = deepcopy(self.base)
            cfg.ratio, cfg.width, cfg.height = ratio, w, h
            cfg.filename = f"batch_{self.base.filename}_{ratio.replace(':','x')}"
            jobs.append((cfg, output_dir))

        return self._run_parallel(jobs, label="Ratio sweep")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run_parallel(self, jobs: list, label: str) -> List[Path]:
        Path(jobs[0][1]).mkdir(parents=True, exist_ok=True)
        results: List[Path] = []

        with Progress(
            SpinnerColumn(style="bold cyan"),
            TextColumn(f"[bold cyan]{label}[/] [white]{{task.description}}"),
            BarColumn(bar_width=36, style="cyan", complete_style="green"),
            TextColumn("[white]{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("rendering…", total=len(jobs))

            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                futures = {pool.submit(_render_one, job): job for job in jobs}
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        results.append(result)
                        update_preview(result)
                        progress.update(task, advance=1, description=result.name)

        return results


# ─── History browser ─────────────────────────────────────────────────────────

def show_history(n: int = 20) -> None:
    """Print the last *n* renders as a rich table."""
    records = history_manager.get_recent(n)
    if not records:
        console.print("[dim]No render history yet.[/]")
        return

    table = Table(
        show_header=True,
        header_style="bold magenta",
        border_style="dim cyan",
        box=None,
        min_width=80,
    )
    table.add_column("#",           style="bold yellow",  width=4)
    table.add_column("Timestamp",   style="dim white",    min_width=20)
    table.add_column("Title",       style="bold cyan",    min_width=24)
    table.add_column("Theme",       style="bold white",   min_width=14)
    table.add_column("Resolution",  style="dim white",    min_width=12)
    table.add_column("File",        style="dim cyan")

    for i, rec in enumerate(records, 1):
        table.add_row(
            str(i),
            rec.get("timestamp", ""),
            (rec.get("title") or "")[:30],
            rec.get("theme", ""),
            rec.get("resolution", ""),
            Path(rec.get("output_path", "")).name,
        )

    console.print()
    console.print(table)
    console.print(f"\n  [dim]Showing last {len(records)} renders. "
                  f"Total: {history_manager.count()}[/]")
