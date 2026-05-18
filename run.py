#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║   Professional Content Creator — CLI Edition                 ║
║                                                              ║
║   Tool 1 │ YouTube Thumbnail Generator                       ║
║   Tool 2 │ Educational / Information Slide Generator         ║
║                                                              ║
║   Usage:  python3 run.py                                     ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─── Dependency check ────────────────────────────────────────────────────────

def _check_dependencies() -> bool:
    required = {
        "PIL":  "Pillow>=10.0.0",
        "rich": "rich>=13.7.0",
    }
    optional = {
        "numpy": "numpy>=1.24.0  (optional — speeds up gradients significantly)",
    }
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if missing:
        print()
        print("═" * 58)
        print("  MISSING REQUIRED PACKAGES — cannot start")
        print("═" * 58)
        for pkg in missing:
            print(f"  ✗  {pkg}")
        print()
        print("  Install with:  pip install -r requirements.txt")
        print("═" * 58)
        return False

    for module, package in optional.items():
        try:
            __import__(module)
        except ImportError:
            print(f"  ℹ  Optional package missing: {package}")
            print("     Gradients will use the pure-PIL fallback (slightly slower).")
            print()

    return True


# ─── Project directories ─────────────────────────────────────────────────────

def _create_dirs() -> None:
    for folder in ("core", "assets/fonts", "assets/icons", "assets/backgrounds",
                   "presets", "history", "output"):
        Path(folder).mkdir(parents=True, exist_ok=True)


# ─── Main menu ───────────────────────────────────────────────────────────────

def _main_menu() -> str:
    """Show the top-level tool-selection menu using rich."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.prompt import Prompt

    console = Console()

    # ASCII banner
    lines = [
        "  ██████╗██████╗ ███████╗ █████╗ ████████╗ ██████╗ ██████╗ ",
        " ██╔════╝██╔══██╗██╔════╝██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗",
        " ██║     ██████╔╝█████╗  ███████║   ██║   ██║   ██║██████╔╝",
        " ██║     ██╔══██╗██╔══╝  ██╔══██║   ██║   ██║   ██║██╔══██╗",
        " ╚██████╗██║  ██║███████╗██║  ██║   ██║   ╚██████╔╝██║  ██║",
        "  ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝",
    ]
    console.print(Panel(
        Text("\n".join(lines), style="bold cyan", justify="center"),
        subtitle="[dim]Professional Image Creator — Terminal Edition[/]",
        border_style="cyan",
        padding=(0, 1),
    ))
    console.print()

    table = Table(show_header=True, header_style="bold magenta",
                  border_style="dim cyan", box=None, min_width=70)
    table.add_column("#",    style="bold yellow",  width=4)
    table.add_column("Tool", style="bold cyan",    min_width=28)
    table.add_column("What it generates",          style="dim white")

    table.add_row(
        "1",
        "YouTube Thumbnail Generator",
        "Eye-catching YouTube thumbnails — 8 themes, 4 layouts",
    )
    table.add_row(
        "2",
        "Educational Slide Generator",
        "Tutorial steps, code slides, quote cards, timelines…",
    )
    table.add_row(
        "3",
        "Exit",
        "",
    )

    console.print(table)
    console.print()

    try:
        choice = Prompt.ask(
            "[bold yellow]➤[/] [bold cyan]Select a tool[/]",
            choices=["1", "2", "3"],
            default="1",
            console=console,
        )
    except KeyboardInterrupt:
        console.print("\n\n  [dim]Goodbye![/]")
        sys.exit(0)

    return choice


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    if not _check_dependencies():
        sys.exit(1)

    _create_dirs()

    choice = _main_menu()

    try:
        if choice == "1":
            from core.cli import ThumbnailCLI
            ThumbnailCLI().run()

        elif choice == "2":
            from core.slide_cli import SlideCLI
            SlideCLI().run()

        elif choice == "3":
            print("\n  Goodbye!\n")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n  Interrupted — goodbye!\n")
        sys.exit(0)
    except Exception as exc:
        print(f"\n  [ERROR] {exc}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
