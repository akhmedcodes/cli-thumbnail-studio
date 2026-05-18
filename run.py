#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║   CLI Thumbnail Studio — Professional Terminal Edition           ║
║                                                                  ║
║   1 │ YouTube Thumbnail Generator                                ║
║   2 │ Educational / Information Slide Generator                  ║
║   3 │ Batch Variation Generator                                  ║
║   4 │ Render History Browser                                     ║
║   5 │ Browser Preview Server                                     ║
║   6 │ Quick Demo (all themes + layouts)                          ║
╚══════════════════════════════════════════════════════════════════╝

Usage:  python3 run.py
        python3 run.py --tool 1          # jump straight to thumbnail
        python3 run.py --tool 2          # jump straight to slide
        python3 run.py --batch-themes    # batch-render all themes
        python3 run.py --demo            # generate demo gallery
        python3 run.py --history         # show render history
        python3 run.py --preview         # start browser preview server
        python3 run.py --verbose         # enable debug output
        python3 run.py --help            # show this help
"""

import sys
import os
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# ─── Argument parsing ────────────────────────────────────────────────────────

def _parse_args():
    p = argparse.ArgumentParser(
        prog="python3 run.py",
        description="CLI Thumbnail Studio — Professional Image Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--tool",         type=int, choices=[1, 2], help="Jump to tool 1 or 2")
    p.add_argument("--batch-themes", action="store_true",      help="Batch render all themes")
    p.add_argument("--demo",         action="store_true",      help="Generate full demo gallery")
    p.add_argument("--history",      action="store_true",      help="Show render history")
    p.add_argument("--preview",      action="store_true",      help="Start browser preview server")
    p.add_argument("--verbose",      action="store_true",      help="Enable verbose/debug output")
    p.add_argument("--silent",       action="store_true",      help="Suppress all non-error output")
    p.add_argument("--port",         type=int, default=7771,   help="Preview server port (default 7771)")
    return p.parse_args()


# ─── Dependency check ────────────────────────────────────────────────────────

def _check_dependencies() -> bool:
    required = {"PIL": "Pillow>=10.0.0", "rich": "rich>=13.7.0"}
    optional = {"numpy": "numpy>=1.24.0  (speeds up gradients)"}
    missing = [pkg for mod, pkg in required.items() if not _can_import(mod)]

    if missing:
        print("\n" + "═" * 58)
        print("  MISSING REQUIRED PACKAGES")
        print("═" * 58)
        for pkg in missing:
            print(f"  ✗  {pkg}")
        print("\n  Fix:  pip install -r requirements.txt")
        print("═" * 58 + "\n")
        return False

    for mod, pkg in optional.items():
        if not _can_import(mod):
            print(f"  ℹ  Optional: {pkg}")

    return True


def _can_import(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False


# ─── Directory bootstrap ─────────────────────────────────────────────────────

def _create_dirs() -> None:
    for d in ("core", "assets/fonts", "assets/icons", "assets/backgrounds",
              "presets", "history", "output",
              "output/batch_themes", "output/batch_layouts",
              "output/batch_colors", "output/batch_ratios", "output/demo"):
        Path(d).mkdir(parents=True, exist_ok=True)


# ─── Main menu ───────────────────────────────────────────────────────────────

def _main_menu() -> str:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.prompt import Prompt
    from core.history_manager import history_manager

    console = Console()

    banner = [
        " ██████╗██╗     ██╗    ███████╗████████╗██╗   ██╗██████╗ ██╗ ██████╗ ",
        "██╔════╝██║     ██║    ██╔════╝╚══██╔══╝██║   ██║██╔══██╗██║██╔═══██╗",
        "██║     ██║     ██║    ███████╗   ██║   ██║   ██║██║  ██║██║██║   ██║",
        "██║     ██║     ██║    ╚════██║   ██║   ██║   ██║██║  ██║██║██║   ██║",
        "╚██████╗███████╗██║    ███████║   ██║   ╚██████╔╝██████╔╝██║╚██████╔╝",
        " ╚═════╝╚══════╝╚═╝    ╚══════╝   ╚═╝    ╚═════╝ ╚═════╝ ╚═╝ ╚═════╝ ",
    ]
    console.print(Panel(
        Text("\n".join(banner), style="bold cyan", justify="center"),
        subtitle="[dim]Professional Image Creator — Terminal Edition[/]",
        border_style="cyan",
        padding=(0, 1),
    ))

    total = history_manager.count()
    if total:
        console.print(f"  [dim]📊 {total} images rendered so far[/]\n")

    table = Table(show_header=True, header_style="bold magenta",
                  border_style="dim cyan", box=None, min_width=72)
    table.add_column("#", style="bold yellow", width=4)
    table.add_column("Tool", style="bold cyan", min_width=30)
    table.add_column("Description", style="dim white")

    rows = [
        ("1", "YouTube Thumbnail Generator",        "8 themes · 4 layouts · 720p→4K"),
        ("2", "Educational Slide Generator",         "13 layouts · 11 themes · code/steps/timelines"),
        ("3", "Batch Variation Generator",           "All themes or layouts at once (parallel)"),
        ("4", "Render History Browser",              "Browse all past renders"),
        ("5", "Browser Preview Server",              "Live preview at localhost:7771"),
        ("6", "Quick Demo — full gallery",           "Generate all themes & layouts as demo"),
        ("7", "Exit",                                ""),
    ]
    for r in rows:
        table.add_row(*r)

    console.print(table)
    console.print()
    console.print("  [dim]Tip: python3 run.py --help  for command-line shortcuts[/]")
    console.print()

    try:
        return Prompt.ask(
            "[bold yellow]➤[/] [bold cyan]Select[/]",
            choices=[str(i) for i in range(1, 8)],
            default="1",
            console=console,
        )
    except KeyboardInterrupt:
        console.print("\n  [dim]Goodbye![/]")
        sys.exit(0)


# ─── Demo gallery ────────────────────────────────────────────────────────────

def _run_demo() -> None:
    from rich.console import Console
    from core.slide_config import SlideConfig
    from core.slide_renderer import render_slide_and_save
    from core.slide_themes import list_slide_themes
    from core.preview import update_preview, show_terminal_preview

    console = Console()
    console.print("\n[bold cyan]Generating demo gallery…[/]\n")

    DEMOS = [
        ("code_focus",     "coding_tutorial", "FastAPI Route Handler",       "async def with type hints",
         dict(code_snippet="from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/hello')\nasync def hello():\n    return {'message': 'Hello World'}", code_language="python")),
        ("numbered_steps", "educational",     "Django Deployment Guide",     "6 steps to production",
         dict(numbered_steps=["Install dependencies","Set DEBUG=False","Run collectstatic","Configure PostgreSQL","Setup Gunicorn + Nginx","Enable SSL with Certbot"])),
        ("comparison",     "dark_modern",     "REST vs GraphQL",             "",
         dict(comparison_left_title="REST", comparison_right_title="GraphQL",
              comparison_left_items=["Fixed endpoints","Over-fetching possible","Easy caching"],
              comparison_right_items=["Single endpoint","Exact data","Complex caching"])),
        ("statistic",      "finance",         "97.4%",                       "Fortune 500 companies use Python",
         dict(stat_number="97.4%", stat_label="of Fortune 500 use Python", body_text="Stack Overflow Survey 2024")),
        ("quote",          "netflix_doc",     "First, solve the problem.", "", dict(quote_author="John Johnson")),
        ("timeline",       "futuristic_ai",   "History of Python",           "",
         dict(timeline_items=["1989 — Guido begins work","1991 — Python 0.9 released","2000 — Python 2.0","2008 — Python 3.0","2025 — Python 3.13"])),
        ("terminal",       "cyberpunk",       "Quick Start",                 "Ubuntu setup",
         dict(terminal_commands=["$ sudo apt update -y","$ pip install django fastapi","$ python3 manage.py runserver"])),
        ("checklist",      "minimal",         "Launch Checklist",            "",
         dict(checklist_items=["Unit tests pass","Migrations applied","SSL enabled","Monitoring on"], progress_current=2)),
        ("centered",       "apple_style",     "Welcome to the Course",       "Python Zero to Hero",
         dict(body_text="32 lessons · 8 projects", tags=["Free","2025","Certificate"])),
        ("tip_card",       "glassmorphism",   "Tip: Virtual Environments",   "",
         dict(body_text="Always use python -m venv to isolate your project dependencies.")),
    ]

    paths = []
    for layout, theme, title, subtitle, extras in DEMOS:
        cfg = SlideConfig(layout_type=layout, theme=theme, title=title,
                          subtitle=subtitle, filename=f"demo_{layout}_{theme}",
                          width=1920, height=1080, **extras)
        try:
            p = render_slide_and_save(cfg, "output/demo")
            paths.append(p)
            update_preview(p)
            console.print(f"  [green]✔[/]  {layout:18s}  {theme:18s}  [dim]{p.name}[/]")
        except Exception as e:
            console.print(f"  [red]✗[/]  {layout:18s}  {e}")

    console.print(f"\n  [bold green]Demo complete — {len(paths)} images in output/demo/[/]")
    if paths:
        show_terminal_preview(paths[-1], width=72)


# ─── Batch menu ──────────────────────────────────────────────────────────────

def _run_batch() -> None:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from core.slide_config import SlideConfig
    from core.batch import BatchRenderer

    console = Console()
    console.print("\n[bold cyan]Batch Variation Generator[/]\n")
    console.print("  This renders your content across multiple themes/layouts in parallel.\n")

    title    = Prompt.ask("[bold yellow]➤[/] [cyan]Title[/]", default="Python Tutorial")
    subtitle = Prompt.ask("[bold yellow]➤[/] [cyan]Subtitle[/]", default="Complete Guide")
    body     = Prompt.ask("[bold yellow]➤[/] [cyan]Body text[/]", default="")
    mode     = Prompt.ask("[bold yellow]➤[/] [cyan]Mode[/]",
                          choices=["themes", "layouts", "colors", "ratios"], default="themes")

    cfg = SlideConfig(title=title, subtitle=subtitle, body_text=body,
                      filename="batch", width=1920, height=1080)
    br = BatchRenderer(cfg)

    paths = {
        "themes":  lambda: br.theme_sweep(),
        "layouts": lambda: br.layout_sweep(),
        "colors":  lambda: br.color_sweep(),
        "ratios":  lambda: br.ratio_sweep(),
    }[mode]()

    console.print(f"\n  [bold green]✔  {len(paths)} images generated[/]")


# ─── Preview server ───────────────────────────────────────────────────────────

def _run_preview_server(port: int = 7771) -> None:
    import time
    from rich.console import Console
    from rich.panel import Panel
    from core.preview import start_preview_server, _SERVER_PORT

    console = Console()
    import core.preview as _pv
    _pv._SERVER_PORT = port

    url = start_preview_server(auto_open=True)
    console.print(Panel(
        f"[bold green]Preview server running![/]\n\n"
        f"  URL:    [bold cyan]{url}[/]\n"
        f"  Auto-refreshes every 2 seconds after each render.\n\n"
        f"  [dim]Press Ctrl+C to stop[/]",
        title="[bold cyan]Browser Preview[/]",
        border_style="cyan",
        padding=(1, 3),
    ))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n  [dim]Preview server stopped.[/]")


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()

    if not _check_dependencies():
        sys.exit(1)

    _create_dirs()

    # CLI flag shortcuts (non-interactive)
    if args.history:
        from core.batch import show_history
        show_history()
        return

    if args.preview:
        from core.preview import start_preview_server
        import core.preview as _pv
        _pv._SERVER_PORT = args.port
        _run_preview_server(args.port)
        return

    if args.demo:
        _run_demo()
        return

    if args.batch_themes:
        from core.slide_config import SlideConfig
        from core.batch import BatchRenderer
        cfg = SlideConfig(title="Demo Slide", subtitle="All Themes Preview",
                          body_text="Generated by CLI Thumbnail Studio",
                          filename="batch_demo", width=1920, height=1080)
        BatchRenderer(cfg).theme_sweep()
        return

    if args.tool == 1:
        from core.cli import ThumbnailCLI
        ThumbnailCLI().run()
        return

    if args.tool == 2:
        from core.slide_cli import SlideCLI
        SlideCLI().run()
        return

    # Interactive menu
    try:
        while True:
            choice = _main_menu()

            if choice == "1":
                from core.cli import ThumbnailCLI
                ThumbnailCLI().run()

            elif choice == "2":
                from core.slide_cli import SlideCLI
                SlideCLI().run()

            elif choice == "3":
                _run_batch()

            elif choice == "4":
                from core.batch import show_history
                show_history()
                input("\n  Press Enter to return to menu…")

            elif choice == "5":
                import threading
                from core.preview import start_preview_server
                url = start_preview_server(auto_open=True)
                from rich.console import Console
                Console().print(f"\n  [bold green]Preview server started → [cyan]{url}[/][/]")
                Console().print("  [dim]It keeps running in the background while you use the app.[/]\n")

            elif choice == "6":
                _run_demo()
                input("\n  Press Enter to return to menu…")

            elif choice == "7":
                print("\n  Goodbye!\n")
                sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n  Interrupted — goodbye!\n")
        sys.exit(0)
    except Exception as exc:
        print(f"\n  [ERROR] {exc}\n")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
