"""
Interactive CLI for the Educational / Information Slide Generator.
Uses *rich* for all terminal output — same premium feel as the thumbnail CLI.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.text import Text

from core.slide_config import SlideConfig
from core.slide_themes import SLIDE_THEMES, SLIDE_THEME_META, list_slide_themes
from core.slide_renderer import render_slide_and_save
from core.preset_manager import preset_manager
from core.history_manager import history_manager
from core.layouts import LAYOUT_NAMES, LAYOUT_HINTS

console = Console()

# ─── Shared style tokens ─────────────────────────────────────────────────────
C = {
    "title":  "bold cyan",
    "accent": "bold yellow",
    "ok":     "bold green",
    "warn":   "bold yellow",
    "err":    "bold red",
    "muted":  "grey62",
    "head":   "bold magenta",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _ask(prompt: str, default: str = "", choices: Optional[List[str]] = None) -> str:
    try:
        ans = Prompt.ask(
            f"[{C['accent']}]➤[/] [{C['title']}]{prompt}[/]",
            default=default or None,
            choices=choices,
            console=console,
        )
        return (ans or "").strip()
    except KeyboardInterrupt:
        console.print("\n[bold red]Interrupted.[/]")
        sys.exit(0)


def _confirm(prompt: str, default: bool = True) -> bool:
    try:
        return Confirm.ask(
            f"[{C['accent']}]➤[/] [{C['title']}]{prompt}[/]",
            default=default, console=console,
        )
    except KeyboardInterrupt:
        sys.exit(0)


def _section(title: str) -> None:
    console.print()
    console.rule(f"[{C['head']}] {title} [{C['head']}]", style="dim cyan")
    console.print()


def _hint(text: str) -> None:
    console.print(f"  [{C['muted']}]{text}[/]")


def _ok(text: str) -> None:
    console.print(f"  [{C['ok']}]✔  {text}[/]")


def _warn(text: str) -> None:
    console.print(f"  [{C['warn']}]⚠  {text}[/]")


def _validate_hex(color: str) -> str:
    color = color.strip()
    if color and color[0] != "#":
        color = "#" + color
    while True:
        h = color.lstrip("#")
        if len(h) in (3, 6, 8) and all(c in "0123456789abcdefABCDEF" for c in h):
            return color
        color = _ask(f"Invalid hex '{color}'. Enter a valid colour (#RRGGBB)", "#ffffff")
        if not color.startswith("#"):
            color = "#" + color


def _ask_list(prompt: str, hint: str) -> List[str]:
    """Ask for a newline or comma-separated list, return cleaned items."""
    _hint(hint)
    raw = _ask(prompt, default="")
    if not raw:
        return []
    # Support both comma and newline-separated
    sep = "\n" if "\n" in raw else ","
    return [s.strip() for s in raw.split(sep) if s.strip()]


# ─── Banner ──────────────────────────────────────────────────────────────────

def _slide_banner() -> None:
    lines = [
        " ███████╗██╗     ██╗██████╗ ███████╗",
        " ██╔════╝██║     ██║██╔══██╗██╔════╝",
        " ███████╗██║     ██║██║  ██║█████╗  ",
        " ╚════██║██║     ██║██║  ██║██╔══╝  ",
        " ███████║███████╗██║██████╔╝███████╗",
        " ╚══════╝╚══════╝╚═╝╚═════╝ ╚══════╝",
    ]
    console.print(Panel(
        Text("\n".join(lines), style="bold magenta", justify="center"),
        subtitle="[dim]Educational / Information Slide Generator[/]",
        border_style="magenta",
        padding=(0, 2),
    ))
    console.print()


# ─── Layout picker ────────────────────────────────────────────────────────────

def _pick_layout() -> str:
    table = Table(show_header=True, header_style="bold magenta",
                  border_style="dim cyan", box=None)
    table.add_column("#",    style="bold yellow", width=3)
    table.add_column("Key",  style="bold cyan",   min_width=16)
    table.add_column("Name", style="bold white",  min_width=18)
    table.add_column("Fill fields",  style="dim white")

    keys = list(LAYOUT_NAMES.keys())
    for i, key in enumerate(keys, 1):
        table.add_row(str(i), key, LAYOUT_NAMES[key], LAYOUT_HINTS.get(key, ""))

    console.print(table)
    console.print()
    ans = _ask("Choose layout (number or key)", default="1")

    if ans.isdigit():
        idx = int(ans) - 1
        return keys[idx] if 0 <= idx < len(keys) else "standard"
    return ans if ans in LAYOUT_NAMES else "standard"


# ─── Theme picker ─────────────────────────────────────────────────────────────

def _pick_slide_theme() -> str:
    table = Table(show_header=True, header_style="bold magenta",
                  border_style="dim cyan", box=None)
    table.add_column("#",    style="bold yellow", width=3)
    table.add_column("Key",  style="bold cyan",   min_width=18)
    table.add_column("Name", style="bold white",  min_width=18)
    table.add_column("Description", style="dim white")

    keys = list_slide_themes()
    for i, key in enumerate(keys, 1):
        name, desc = SLIDE_THEME_META.get(key, (key, ""))
        table.add_row(str(i), key, name, desc)

    console.print(table)
    console.print()
    ans = _ask("Choose theme (number or key)", default="1")

    if ans.isdigit():
        idx = int(ans) - 1
        return keys[idx] if 0 <= idx < len(keys) else "dark_modern"
    return ans if ans in SLIDE_THEMES else "dark_modern"


# ─── Resolution picker ────────────────────────────────────────────────────────

_RESOLUTIONS = {
    "16:9": [
        (1280,  720, "720p HD"),
        (1920, 1080, "1080p Full HD  [recommended]"),
        (2560, 1440, "1440p 2K"),
    ],
    "9:16": [
        ( 720, 1280, "720p Vertical"),
        (1080, 1920, "1080p Vertical  [recommended]"),
    ],
    "1:1": [
        (1080, 1080, "1080×1080"),
        (1440, 1440, "1440×1440"),
    ],
}


def _pick_resolution(ratio: str) -> tuple:
    opts = _RESOLUTIONS.get(ratio, _RESOLUTIONS["16:9"])
    table = Table(show_header=False, border_style="dim cyan", box=None)
    table.add_column("#",    style="bold yellow", width=3)
    table.add_column("Res",  style="bold cyan")
    table.add_column("Name", style="dim white")
    for i, (w, h, name) in enumerate(opts, 1):
        table.add_row(str(i), f"{w}×{h}", name)
    console.print(table)

    idx_str = _ask("Choose resolution", default="2",
                   choices=[str(i) for i in range(1, len(opts) + 1)])
    idx = int(idx_str) - 1
    w, h, _ = opts[max(0, min(idx, len(opts) - 1))]
    return w, h


# ─── Main CLI class ───────────────────────────────────────────────────────────

class SlideCLI:

    def __init__(self) -> None:
        self.cfg = SlideConfig()

    def run(self) -> None:
        _slide_banner()

        # Load preset?
        presets = [p for p in preset_manager.list_presets() if "slide_" in p]
        if presets and _confirm(f"Load a saved slide preset? ({len(presets)} available)", False):
            self._load_preset(presets)

        # ── Step 1: Layout ────────────────────────────────────────────────────
        _section("STEP 1 — LAYOUT TYPE")
        _hint("Choose the visual structure of your slide.")
        self.cfg.layout_type = _pick_layout()
        _ok(f"Layout: [bold]{LAYOUT_NAMES[self.cfg.layout_type]}[/]")

        # ── Step 2: Theme ─────────────────────────────────────────────────────
        _section("STEP 2 — VISUAL THEME")
        self.cfg.theme = _pick_slide_theme()
        _ok(f"Theme: [bold]{self.cfg.theme}[/]")

        # ── Step 3: Format ────────────────────────────────────────────────────
        _section("STEP 3 — CANVAS FORMAT")
        ratio = _ask("Aspect ratio", default="16:9", choices=["16:9", "9:16", "1:1"])
        self.cfg.ratio = ratio
        console.print()
        _hint("Available resolutions:")
        w, h = _pick_resolution(ratio)
        self.cfg.width, self.cfg.height = w, h
        _ok(f"Canvas: {w}×{h}")

        # ── Step 4: Content (guided by layout) ────────────────────────────────
        _section("STEP 4 — CONTENT")
        self._ask_content_for_layout()

        # ── Step 5: Output ────────────────────────────────────────────────────
        _section("STEP 5 — OUTPUT")
        self.cfg.filename = _ask("Output filename (no extension)", default="slide")

        # ── Step 6: Optional overrides ────────────────────────────────────────
        if _confirm("Customise colours / effects?", default=False):
            _section("STEP 6 — COLOUR OVERRIDES")
            self._ask_overrides()

        # ── Summary ───────────────────────────────────────────────────────────
        _section("READY TO GENERATE")
        self._show_summary()
        if not _confirm("Generate slide now?", default=True):
            console.print("\n[dim]Cancelled.[/]")
            return

        # ── Generate ──────────────────────────────────────────────────────────
        output_path = self._generate()

        # ── Save preset? ──────────────────────────────────────────────────────
        if _confirm("Save settings as a preset?", default=False):
            name = _ask("Preset name", default=f"slide_{self.cfg.theme}")
            saved = preset_manager.save(name, self.cfg)   # type: ignore[arg-type]
            _ok(f"Preset saved → [cyan]{saved}[/]")

        _section("DONE")
        console.print(Panel(
            f"[bold green]✔  Slide saved![/]\n\n"
            f"  [white]Path  :[/]  [cyan]{output_path}[/]\n"
            f"  [white]Size  :[/]  [yellow]{self.cfg.width} × {self.cfg.height} px[/]\n"
            f"  [white]Layout:[/]  [magenta]{LAYOUT_NAMES[self.cfg.layout_type]}[/]\n"
            f"  [white]Theme :[/]  [magenta]{self.cfg.theme}[/]",
            title="[bold green]Success[/]",
            border_style="green",
            padding=(1, 3),
        ))

    # ─── Content prompts (per layout) ─────────────────────────────────────────

    def _ask_content_for_layout(self) -> None:
        lt = self.cfg.layout_type

        # Fields used by every layout
        _hint("Main headline text for this slide.")
        self.cfg.title = _ask("Title", default="")

        _hint("Secondary line below the title (blank to skip).")
        self.cfg.subtitle = _ask("Subtitle / tagline", default="")

        # Layout-specific
        if lt == "standard":
            self._ask_body()
            self._ask_bullets_or_steps()
            self._ask_code()
            self._ask_terminal()
            self._ask_extras()

        elif lt == "code_focus":
            self._ask_code(required=True)
            self._ask_extras()

        elif lt == "two_column":
            _hint("Left column: body text + bullets.  Right column: code/steps/terminal.")
            self._ask_body()
            self._ask_bullets()
            self._ask_code()
            self._ask_steps()
            self._ask_terminal()
            self._ask_extras()

        elif lt == "numbered_steps":
            self._ask_steps(required=True)
            self._ask_extras()

        elif lt == "quote":
            if not self.cfg.title:
                self.cfg.title = _ask("Quote text", default="")
            _hint("Quote author (leave blank to skip).")
            self.cfg.quote_author = _ask("Author", default="")
            self._ask_extras()

        elif lt == "checklist":
            self._ask_checklist(required=True)
            _hint("How many items are already DONE? (0 if none)")
            done = _ask("Completed count", default="0")
            self.cfg.progress_current = int(done) if done.isdigit() else 0
            self._ask_extras()

        elif lt == "comparison":
            self.cfg.comparison_left_title  = _ask("Left column title",  default="Option A")
            self.cfg.comparison_right_title = _ask("Right column title", default="Option B")
            self.cfg.comparison_left_items  = _ask_list(
                "Left items (comma-separated)", "Items for left column")
            self.cfg.comparison_right_items = _ask_list(
                "Right items (comma-separated)", "Items for right column")
            self._ask_extras()

        elif lt == "statistic":
            _hint("The big number/percentage shown prominently.")
            self.cfg.stat_number = _ask("Statistic value (e.g. 97%)", default="")
            self.cfg.stat_label  = _ask("Stat label (e.g. of users prefer…)", default="")
            self._ask_body()
            self._ask_extras()

        elif lt == "terminal":
            self._ask_terminal(required=True)
            self._ask_body()
            self._ask_extras()

        elif lt == "tip_card":
            _hint("card_type auto-detected from title keywords: warn/error/success/tip/info")
            self._ask_body()
            self._ask_extras()

        elif lt == "top_n":
            self._ask_steps(required=True, label="Top-N items (comma-separated)")
            self._ask_extras()

        elif lt == "centered":
            self._ask_body()
            self._ask_tags()
            self._ask_extras()

        elif lt == "timeline":
            self.cfg.timeline_items = _ask_list(
                "Timeline events (comma-separated)",
                "Each item is one point on the timeline")
            self._ask_extras()

    # ─── Field helpers ────────────────────────────────────────────────────────

    def _ask_body(self) -> None:
        _hint("Paragraph text (blank to skip).")
        self.cfg.body_text = _ask("Body / description", default="")

    def _ask_bullets(self) -> None:
        self.cfg.bullet_points = _ask_list(
            "Bullet points (comma-separated, blank to skip)",
            "Each item becomes one bullet.")

    def _ask_steps(self, required: bool = False, label: str = "") -> None:
        label = label or "Numbered steps (comma-separated)"
        hint  = "Each item gets an auto-numbered circle."
        if required:
            while not self.cfg.numbered_steps:
                self.cfg.numbered_steps = _ask_list(label, hint)
                if not self.cfg.numbered_steps:
                    _warn("At least one step is required for this layout.")
        else:
            self.cfg.numbered_steps = _ask_list(label, hint)

    def _ask_bullets_or_steps(self) -> None:
        choice = _ask("Add list content?", default="none",
                      choices=["none", "bullets", "steps"])
        if choice == "bullets":
            self._ask_bullets()
        elif choice == "steps":
            self._ask_steps()

    def _ask_checklist(self, required: bool = False) -> None:
        self.cfg.checklist_items = _ask_list(
            "Checklist items (comma-separated)",
            "Each item becomes a checkbox entry.")
        if required and not self.cfg.checklist_items:
            _warn("At least one checklist item required.")

    def _ask_code(self, required: bool = False) -> None:
        _hint("Paste code snippet (blank to skip — enter END on a new line to finish).")
        first = _ask("Code snippet (press Enter twice / type END to finish)", default="")
        if not first:
            if required:
                _warn("Code snippet is recommended for this layout.")
            return
        if first.upper() == "END":
            return
        lines = [first]
        while True:
            line = _ask("", default="END")
            if line.upper() == "END" or line == "":
                break
            lines.append(line)
        self.cfg.code_snippet = "\n".join(lines)
        self.cfg.code_language = _ask(
            "Language", default="python",
            choices=["python", "js", "ts", "bash", "html", "css", "generic"])

    def _ask_terminal(self, required: bool = False) -> None:
        _hint("Terminal commands — prefix with $, #, or > (blank to skip).")
        raw = _ask("Terminal commands (comma-separated)", default="")
        if raw:
            self.cfg.terminal_commands = [c.strip() for c in raw.split(",") if c.strip()]
        elif required:
            _warn("Terminal commands are recommended for this layout.")

    def _ask_tags(self) -> None:
        raw = _ask("Tags/badges (comma-separated, blank to skip)", default="")
        if raw:
            self.cfg.tags = [t.strip() for t in raw.split(",") if t.strip()]

    def _ask_extras(self) -> None:
        """Common supplementary fields."""
        _hint("Footer text shown at the bottom of the slide (blank to skip).")
        self.cfg.footer_text = _ask("Footer text", default="")

        _hint("Watermark text shown in a corner (blank to skip).")
        self.cfg.watermark = _ask("Watermark", default="")

        self._ask_tags()

        _hint("Show step-progress indicator? (e.g. Step 2 of 5)")
        if _confirm("Add step progress indicator?", default=False):
            self.cfg.show_progress = True
            total = _ask("Total steps", default="5")
            current = _ask("Current step", default="1")
            self.cfg.progress_total   = int(total)   if total.isdigit()   else 5
            self.cfg.progress_current = int(current) if current.isdigit() else 1

    def _ask_overrides(self) -> None:
        _hint("Leave blank to use the theme's default colour.")
        raw = _ask("Title colour override (hex, blank=theme)", default="")
        if raw:
            self.cfg.title_color = _validate_hex(raw)

        raw = _ask("Accent colour override (hex, blank=theme)", default="")
        if raw:
            self.cfg.accent_color = _validate_hex(raw)

        raw = _ask("Body colour override (hex, blank=theme)", default="")
        if raw:
            self.cfg.body_color = _validate_hex(raw)

    # ─── Summary ──────────────────────────────────────────────────────────────

    def _show_summary(self) -> None:
        table = Table(show_header=True, header_style="bold magenta",
                      border_style="dim cyan", box=None)
        table.add_column("Setting",  style="bold cyan",  min_width=20)
        table.add_column("Value",    style="white")

        def yn(v): return "[green]YES[/]" if v else "[dim]no[/]"

        rows = [
            ("Layout",        LAYOUT_NAMES.get(self.cfg.layout_type, self.cfg.layout_type)),
            ("Theme",         self.cfg.theme),
            ("Canvas",        f"{self.cfg.width}×{self.cfg.height}  ({self.cfg.ratio})"),
            ("Title",         self.cfg.title or "[dim](none)[/]"),
            ("Subtitle",      self.cfg.subtitle or "[dim](none)[/]"),
            ("Body text",     ("yes, " + str(len(self.cfg.body_text)) + " chars") if self.cfg.body_text else "[dim]no[/]"),
            ("Bullet points", str(len(self.cfg.bullet_points)) if self.cfg.bullet_points else "[dim]no[/]"),
            ("Steps",         str(len(self.cfg.numbered_steps)) if self.cfg.numbered_steps else "[dim]no[/]"),
            ("Code snippet",  yn(self.cfg.code_snippet)),
            ("Terminal cmds", str(len(self.cfg.terminal_commands)) if self.cfg.terminal_commands else "[dim]no[/]"),
            ("Tags",          ", ".join(self.cfg.tags) if self.cfg.tags else "[dim]no[/]"),
            ("Footer",        self.cfg.footer_text or "[dim]no[/]"),
            ("Watermark",     self.cfg.watermark or "[dim]no[/]"),
            ("Step progress", f"Step {self.cfg.progress_current}/{self.cfg.progress_total}" if self.cfg.show_progress else "[dim]no[/]"),
            ("Output file",   f"output/{self.cfg.filename}_<timestamp>.png"),
        ]
        for label, val in rows:
            table.add_row(label, val)
        console.print(table)

    # ─── Render with progress bar ─────────────────────────────────────────────

    def _generate(self) -> Path:
        console.print()
        steps = ["Setting up canvas", "Rendering background",
                 "Applying theme effects", "Compositing components",
                 "Rendering typography", "Applying post-effects", "Saving PNG"]

        output_path: Optional[Path] = None
        with Progress(
            SpinnerColumn(spinner_name="dots", style="bold magenta"),
            TextColumn("[bold magenta]{task.description}"),
            BarColumn(bar_width=40, style="magenta", complete_style="bold green"),
            TextColumn("[bold white]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Generating slide…", total=len(steps))
            for i, step in enumerate(steps):
                progress.update(task, description=f"[bold magenta]{step}…")
                time.sleep(0.10)
                if i == len(steps) - 1:
                    output_path = render_slide_and_save(self.cfg, output_dir="output")
                progress.advance(task)

        history_manager.add(self.cfg, str(output_path))  # type: ignore[arg-type]
        return output_path  # type: ignore[return-value]

    # ─── Preset ───────────────────────────────────────────────────────────────

    def _load_preset(self, presets: List[str]) -> None:
        table = Table(show_header=False, border_style="dim cyan", box=None)
        table.add_column("#",    style="bold yellow", width=4)
        table.add_column("Name", style="bold cyan")
        for i, name in enumerate(presets, 1):
            table.add_row(str(i), name)
        console.print(table)

        choice = _ask("Choose preset (blank to skip)", default="")
        if not choice:
            return
        name = presets[int(choice) - 1] if choice.isdigit() else choice
        loaded = preset_manager.load(name)
        if loaded:
            # preset_manager stores ThumbnailConfig — convert fields that match
            for k, v in loaded.to_dict().items():
                if hasattr(self.cfg, k):
                    setattr(self.cfg, k, v)
            _ok(f"Preset loaded: [bold]{name}[/]")
