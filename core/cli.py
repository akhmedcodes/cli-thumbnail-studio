"""
Interactive CLI for the YouTube Thumbnail Generator.

Uses *rich* for all terminal output — colours, panels, tables, progress bars.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.columns import Columns
from rich.padding import Padding
from rich import print as rprint
from rich.style import Style

from core.config import ThumbnailConfig
from core.themes import THEME_META, get_theme, list_themes
from core.renderer import render_and_save
from core.preset_manager import preset_manager
from core.history_manager import history_manager

console = Console()

# ─── ANSI colour shortcuts (used in prompt labels) ───────────────────────────
C = {
    "title":   "bold cyan",
    "dim":     "dim white",
    "accent":  "bold yellow",
    "ok":      "bold green",
    "warn":    "bold yellow",
    "err":     "bold red",
    "muted":   "grey62",
    "head":    "bold magenta",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _ask(prompt: str, default: str = "", choices: Optional[List[str]] = None) -> str:
    """Wrapper around rich Prompt.ask with KeyboardInterrupt safety."""
    try:
        answer = Prompt.ask(
            f"[{C['accent']}]➤[/] [{C['title']}]{prompt}[/]",
            default=default or None,
            choices=choices,
            console=console,
        )
        return answer.strip() if answer else default
    except KeyboardInterrupt:
        console.print("\n[bold red]Interrupted.[/]")
        sys.exit(0)


def _confirm(prompt: str, default: bool = True) -> bool:
    try:
        return Confirm.ask(
            f"[{C['accent']}]➤[/] [{C['title']}]{prompt}[/]",
            default=default,
            console=console,
        )
    except KeyboardInterrupt:
        sys.exit(0)


def _section(title: str) -> None:
    """Print a coloured section divider."""
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
    """Return color if valid hex, else prompt until it is."""
    color = color.strip()
    if color and color[0] != "#":
        color = "#" + color
    while True:
        h = color.lstrip("#")
        if len(h) in (3, 6, 8) and all(c in "0123456789abcdefABCDEF" for c in h):
            return color
        color = _ask(f"Invalid hex '{color}'. Enter a valid colour (e.g. #ff6b35)", "#ffffff")
        if not color.startswith("#"):
            color = "#" + color


# ─── Welcome banner ──────────────────────────────────────────────────────────

def _banner() -> None:
    lines = [
        " ██╗   ██╗████████╗██╗  ██╗██╗   ██╗███╗   ███╗██████╗ ",
        " ╚██╗ ██╔╝╚══██╔══╝╚██╗██╔╝██║   ██║████╗ ████║██╔══██╗",
        "  ╚████╔╝    ██║    ╚███╔╝ ██║   ██║██╔████╔██║██████╔╝",
        "   ╚██╔╝     ██║    ██╔██╗ ██║   ██║██║╚██╔╝██║██╔══██╗",
        "    ██║      ██║   ██╔╝ ██╗╚██████╔╝██║ ╚═╝ ██║██████╔╝",
        "    ╚═╝      ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═════╝ ",
    ]
    banner_text = "\n".join(lines)
    console.print(Panel(
        Text(banner_text, style="bold cyan", justify="center"),
        subtitle="[dim]YouTube Thumbnail Generator — Pro CLI Edition[/]",
        border_style="cyan",
        padding=(0, 2),
    ))
    console.print()
    total = history_manager.count()
    if total:
        console.print(f"  [{C['muted']}]Thumbnails generated so far: {total}[/]")
        console.print()


# ─── Theme picker ─────────────────────────────────────────────────────────────

def _pick_theme() -> str:
    """Display theme table and return chosen theme key (or 'custom')."""
    table = Table(
        show_header=True,
        header_style="bold magenta",
        border_style="dim cyan",
        box=None,
        show_lines=False,
    )
    table.add_column("#",  style="bold yellow", width=3)
    table.add_column("Key",  style="bold cyan",  min_width=14)
    table.add_column("Name", style="bold white", min_width=14)
    table.add_column("Description", style="dim white")

    keys = list_themes()
    for i, key in enumerate(keys, 1):
        name, desc = THEME_META.get(key, (key, ""))
        table.add_row(str(i), key, name, desc)

    # Custom option
    table.add_row(str(len(keys) + 1), "custom", "Custom", "Configure every setting manually")

    console.print(table)
    console.print()

    valid = [str(i) for i in range(1, len(keys) + 2)] + keys + ["custom"]
    answer = _ask("Select a theme (number or key)", default="1", choices=None)

    if answer.isdigit():
        idx = int(answer) - 1
        if 0 <= idx < len(keys):
            return keys[idx]
        return "custom"
    if answer in keys:
        return answer
    return "custom"


# ─── Resolution picker ────────────────────────────────────────────────────────

_RESOLUTIONS = {
    "16:9": {
        "1": (1280,  720,  "720p HD"),
        "2": (1920, 1080,  "1080p Full HD  [recommended]"),
        "3": (2560, 1440,  "1440p 2K"),
        "4": (3840, 2160,  "4K Ultra HD"),
    },
    "9:16": {
        "1": ( 720, 1280,  "720p Vertical HD"),
        "2": (1080, 1920,  "1080p Vertical Full HD  [recommended]"),
    },
}


def _pick_resolution(ratio: str) -> tuple[int, int]:
    opts = _RESOLUTIONS.get(ratio, _RESOLUTIONS["16:9"])
    table = Table(show_header=False, border_style="dim cyan", box=None)
    table.add_column("#",    style="bold yellow", width=3)
    table.add_column("Res",  style="bold cyan")
    table.add_column("Name", style="dim white")
    for k, (w, h, name) in opts.items():
        table.add_row(k, f"{w}×{h}", name)
    console.print(table)

    choice = _ask("Choose resolution", default="2", choices=list(opts.keys()))
    w, h, _ = opts.get(choice, list(opts.values())[1])
    return w, h


# ─── Colour picker ────────────────────────────────────────────────────────────

def _pick_colors_for_gradient() -> List[str]:
    _hint("Enter 2–3 hex colours for the gradient (e.g. #1a1a2e #302b63)")
    raw = _ask("Gradient colours (space-separated)", default="#1a1a2e #16213e #0f3460")
    parts = raw.split()
    validated = [_validate_hex(p) for p in parts if p]
    return validated if validated else ["#1a1a2e", "#16213e"]


# ─── Main CLI class ───────────────────────────────────────────────────────────

class ThumbnailCLI:

    def __init__(self) -> None:
        self.cfg = ThumbnailConfig()

    # ─── Entry point ──────────────────────────────────────────────────────

    def run(self) -> None:
        _banner()

        # ── Preset or fresh? ──────────────────────────────────────────────
        presets = preset_manager.list_presets()
        if presets:
            if _confirm(f"Load a saved preset? ({len(presets)} available)", default=False):
                self.cfg = self._load_preset_menu(presets) or self.cfg

        _section("STEP 1 — THEME SELECTION")
        theme_key = _pick_theme()

        if theme_key != "custom":
            # Apply theme defaults then let user override content fields
            theme_data = get_theme(theme_key)
            self.cfg = ThumbnailConfig.from_dict({**ThumbnailConfig().to_dict(), **theme_data})
            _ok(f"Theme applied: [bold]{theme_key}[/]")

        # ── Content ───────────────────────────────────────────────────────
        _section("STEP 2 — CONTENT")
        self._ask_content()

        # ── Output ────────────────────────────────────────────────────────
        _section("STEP 3 — OUTPUT & FORMAT")
        self._ask_output()

        # ── Background (skip if theme already set) ────────────────────────
        if theme_key == "custom":
            _section("STEP 4 — BACKGROUND")
            self._ask_background()

            _section("STEP 5 — COLOURS")
            self._ask_colors()

            _section("STEP 6 — TYPOGRAPHY & LAYOUT")
            self._ask_typography()

            _section("STEP 7 — EFFECTS")
            self._ask_effects()
        else:
            # Still allow overrides for background image
            if _confirm("Use a custom background image instead of the theme gradient?", default=False):
                self._ask_bg_image()

        # ── Summary ───────────────────────────────────────────────────────
        _section("READY TO GENERATE")
        self._show_summary()

        if not _confirm("Generate thumbnail now?", default=True):
            console.print("\n[dim]Cancelled. Goodbye![/]")
            return

        # ── Generate ──────────────────────────────────────────────────────
        output_path = self._generate()

        # ── Save preset? ──────────────────────────────────────────────────
        _section("SAVE PRESET")
        if _confirm("Save these settings as a preset for later?", default=False):
            name = _ask("Preset name", default=self.cfg.theme or "my_preset")
            saved = preset_manager.save(name, self.cfg)
            _ok(f"Preset saved → [cyan]{saved}[/]")

        # ── Done! ─────────────────────────────────────────────────────────
        _section("DONE")
        console.print(Panel(
            f"[bold green]✔  Thumbnail saved![/]\n\n"
            f"  [white]Path :[/]  [cyan]{output_path}[/]\n"
            f"  [white]Size :[/]  [yellow]{self.cfg.width} × {self.cfg.height} px[/]\n"
            f"  [white]Theme:[/]  [magenta]{self.cfg.theme or 'custom'}[/]",
            title="[bold green]Success[/]",
            border_style="green",
            padding=(1, 3),
        ))

    # ─── Content prompts ──────────────────────────────────────────────────

    def _ask_content(self) -> None:
        _hint("This text will be the large headline of your thumbnail.")
        self.cfg.title = _ask("Title text", default=self.cfg.title)

        _hint("Optional subtitle / description line (leave blank to skip).")
        self.cfg.subtitle = _ask("Subtitle", default=self.cfg.subtitle)

        _hint("Optional badge labels separated by commas  (e.g. NEW, FREE, #1)")
        raw = _ask("Labels (comma-separated, blank to skip)", default=", ".join(self.cfg.labels))
        if raw.strip():
            self.cfg.labels = [l.strip() for l in raw.split(",") if l.strip()]
        else:
            self.cfg.labels = []

    # ─── Output prompts ───────────────────────────────────────────────────

    def _ask_output(self) -> None:
        self.cfg.filename = _ask("Output filename (no extension)", default=self.cfg.filename or "thumbnail")

        _hint("Choose the aspect ratio for your thumbnail.")
        ratio = _ask("Ratio", default=self.cfg.ratio, choices=["16:9", "9:16"])
        self.cfg.ratio = ratio

        console.print()
        _hint("Available resolutions for this ratio:")
        w, h = _pick_resolution(ratio)
        self.cfg.width = w
        self.cfg.height = h
        _ok(f"Resolution set to {w} × {h}")

    # ─── Background prompts ───────────────────────────────────────────────

    def _ask_background(self) -> None:
        _hint("Choose how the background is created.")
        bg_type = _ask("Background type", default="gradient", choices=["solid", "gradient", "image"])
        self.cfg.bg_type = bg_type

        if bg_type == "solid":
            color = _ask("Background colour (hex)", default="#1a1a2e")
            self.cfg.bg_colors = [_validate_hex(color)]

        elif bg_type == "gradient":
            self.cfg.bg_colors = _pick_colors_for_gradient()
            direction = _ask(
                "Gradient direction",
                default="diagonal",
                choices=["horizontal", "vertical", "diagonal", "radial"],
            )
            self.cfg.gradient_direction = direction

        elif bg_type == "image":
            self._ask_bg_image()

    def _ask_bg_image(self) -> None:
        while True:
            path = _ask("Path to background image", default="")
            if not path:
                _warn("No path entered — using gradient fallback.")
                self.cfg.bg_type = "gradient"
                break
            if Path(path).exists():
                self.cfg.bg_image_path = path
                self.cfg.bg_type = "image"
                _ok(f"Image set: {path}")
                if _confirm("Apply blur to background image?", default=True):
                    self.cfg.blur_bg = True
                    self.cfg.blur_radius = int(_ask("Blur radius (1–20)", default="6"))
                break
            else:
                _warn(f"File not found: {path}. Try again.")

    # ─── Colour prompts ───────────────────────────────────────────────────

    def _ask_colors(self) -> None:
        _hint("Colour for the main title text.")
        self.cfg.text_color = _validate_hex(_ask("Title text colour", default=self.cfg.text_color))

        _hint("Colour for subtitle / description text.")
        self.cfg.subtitle_color = _validate_hex(_ask("Subtitle colour", default=self.cfg.subtitle_color))

        _hint("Accent colour used for badges, bars, and glow.")
        self.cfg.accent_color = _validate_hex(_ask("Accent colour", default=self.cfg.accent_color))

        _hint("Badge background colour.")
        self.cfg.label_bg_color = _validate_hex(_ask("Badge background colour", default=self.cfg.label_bg_color))

        _hint("Badge text colour.")
        self.cfg.label_text_color = _validate_hex(_ask("Badge text colour", default=self.cfg.label_text_color))

    # ─── Typography prompts ───────────────────────────────────────────────

    def _ask_typography(self) -> None:
        _hint("Font weight/style for the title.")
        self.cfg.font_style = _ask(
            "Font style",
            default=self.cfg.font_style,
            choices=["bold", "regular", "impact", "condensed"],
        )

        _hint("How elements are arranged on the canvas.")
        console.print(f"  [dim]centered / left_aligned / modern_youtube / cinematic[/]")
        self.cfg.positioning = _ask(
            "Positioning style",
            default=self.cfg.positioning,
            choices=["centered", "left_aligned", "modern_youtube", "cinematic"],
        )

        if self.cfg.positioning == "cinematic":
            self.cfg.cinematic_bars = True

    # ─── Effects prompts ──────────────────────────────────────────────────

    def _ask_effects(self) -> None:
        # Shadow
        self.cfg.shadow = _confirm("Enable drop shadow on text?", default=self.cfg.shadow)
        if self.cfg.shadow:
            _hint("Shadow colour as hex with optional alpha  (e.g. #00000099)")
            self.cfg.shadow_color = _validate_hex(_ask("Shadow colour", default=self.cfg.shadow_color))

        # Stroke / border
        self.cfg.stroke = _confirm("Enable text stroke / outline?", default=self.cfg.stroke)
        if self.cfg.stroke:
            self.cfg.stroke_color = _validate_hex(_ask("Stroke colour", default=self.cfg.stroke_color))
            w = _ask("Stroke width (1–8)", default=str(self.cfg.stroke_width))
            self.cfg.stroke_width = max(1, min(8, int(w) if w.isdigit() else 3))

        # Dark overlay
        self.cfg.overlay = _confirm("Enable dark overlay on background?", default=self.cfg.overlay)
        if self.cfg.overlay:
            op = _ask("Overlay opacity 0–100 (higher = darker)", default=str(self.cfg.overlay_opacity))
            self.cfg.overlay_opacity = max(0, min(100, int(op) if op.isdigit() else 30))

        # Glow
        self.cfg.glow = _confirm("Enable glow effect on text?", default=self.cfg.glow)
        if self.cfg.glow:
            _hint("Leave blank to use the accent colour as glow colour.")
            raw = _ask("Glow colour (hex, blank = accent)", default="")
            self.cfg.glow_color = _validate_hex(raw) if raw.strip() else ""
            r = _ask("Glow radius (5–50)", default=str(self.cfg.glow_radius))
            self.cfg.glow_radius = max(5, min(50, int(r) if r.isdigit() else 22))

    # ─── Summary table ────────────────────────────────────────────────────

    def _show_summary(self) -> None:
        table = Table(
            show_header=True,
            header_style="bold magenta",
            border_style="dim cyan",
            box=None,
        )
        table.add_column("Setting",  style="bold cyan",  min_width=20)
        table.add_column("Value",    style="white")

        rows = [
            ("Title",       self.cfg.title or "[dim](none)[/]"),
            ("Subtitle",    self.cfg.subtitle or "[dim](none)[/]"),
            ("Labels",      ", ".join(self.cfg.labels) or "[dim](none)[/]"),
            ("Theme",       self.cfg.theme),
            ("Resolution",  f"{self.cfg.width} × {self.cfg.height}"),
            ("Ratio",       self.cfg.ratio),
            ("Background",  self.cfg.bg_type),
            ("Positioning", self.cfg.positioning),
            ("Font style",  self.cfg.font_style),
            ("Shadow",      "[green]ON[/]" if self.cfg.shadow else "[dim]off[/]"),
            ("Stroke",      "[green]ON[/]" if self.cfg.stroke else "[dim]off[/]"),
            ("Overlay",     f"[green]ON[/] ({self.cfg.overlay_opacity}%)" if self.cfg.overlay else "[dim]off[/]"),
            ("Glow",        "[green]ON[/]" if self.cfg.glow else "[dim]off[/]"),
            ("Output file", f"output/{self.cfg.filename}_<timestamp>.png"),
        ]

        for label, val in rows:
            table.add_row(label, val)

        console.print(table)

    # ─── Render with progress bar ─────────────────────────────────────────

    def _generate(self) -> Path:
        console.print()

        steps = [
            "Initialising canvas",
            "Rendering background",
            "Applying decorations",
            "Compositing effects",
            "Rendering text layers",
            "Finalising image",
            "Saving PNG",
        ]

        output_path: Optional[Path] = None

        with Progress(
            SpinnerColumn(spinner_name="dots", style="bold cyan"),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=40, style="cyan", complete_style="bold green"),
            TextColumn("[bold white]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        ) as progress:
            task = progress.add_task("Generating thumbnail…", total=len(steps))

            for i, step in enumerate(steps):
                progress.update(task, description=f"[bold cyan]{step}…")
                time.sleep(0.12)  # brief pause so each step is visible

                if i == len(steps) - 1:
                    # Actual render happens here
                    progress.update(task, description="[bold green]Saving PNG…")
                    output_path = render_and_save(self.cfg, output_dir="output")

                progress.advance(task)

        history_manager.add(self.cfg, str(output_path))
        return output_path  # type: ignore[return-value]

    # ─── Preset menu ──────────────────────────────────────────────────────

    def _load_preset_menu(self, presets: List[str]) -> Optional[ThumbnailConfig]:
        table = Table(show_header=False, border_style="dim cyan", box=None)
        table.add_column("#",    style="bold yellow", width=4)
        table.add_column("Name", style="bold cyan")
        for i, name in enumerate(presets, 1):
            table.add_row(str(i), name)
        console.print(table)

        choice = _ask("Choose preset (number or name, blank to skip)", default="")
        if not choice:
            return None

        name = choice
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(presets):
                name = presets[idx]

        cfg = preset_manager.load(name)
        if cfg:
            _ok(f"Loaded preset: [bold]{name}[/]")
            return cfg
        _warn(f"Preset '{name}' not found.")
        return None
