"""
Live preview system — two modes:

1. Terminal ASCII preview  (always available, uses rich)
2. Browser preview server  (localhost:7771, opens automatically)

The browser mode serves a page that auto-refreshes whenever a new PNG
is written to output/ — no WebSocket library needed, just HTTP polling.
"""

from __future__ import annotations

import base64
import os
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

from PIL import Image

# ─── Shared state ────────────────────────────────────────────────────────────

_CURRENT_IMAGE_PATH: Optional[Path] = None
_CURRENT_IMAGE_B64:  Optional[str]  = None
_SERVER_THREAD: Optional[threading.Thread] = None
_SERVER_PORT = 7771


# ─── ASCII / Rich terminal preview ───────────────────────────────────────────

def show_terminal_preview(image_path: Path, width: int = 60) -> None:
    """Print a tiny ASCII-art representation of the image in the terminal."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        console = Console()
        img = Image.open(str(image_path)).convert("RGB")

        # Resize to terminal width preserving aspect ratio
        aspect = img.height / img.width
        tw = width
        th = max(4, int(tw * aspect * 0.45))  # 0.45 = character height correction
        img = img.resize((tw, th), Image.LANCZOS)

        # Convert to Rich coloured block characters
        text = Text()
        for y in range(th):
            for x in range(tw):
                r, g, b = img.getpixel((x, y))
                text.append("█", style=f"rgb({r},{g},{b})")
            if y < th - 1:
                text.append("\n")

        console.print(Panel(
            text,
            title=f"[bold cyan]Preview — {image_path.name}[/]",
            subtitle=f"[dim]{img.width * (img.size[0] // tw)}×{img.height * (img.size[1] // th)} px[/]",
            border_style="cyan",
            padding=(0, 1),
        ))

    except Exception as e:
        # Silently skip if preview fails
        pass


def show_info_bar(image_path: Path) -> None:
    """Print a one-line info bar below the preview."""
    try:
        from rich.console import Console
        stat = image_path.stat()
        size_kb = stat.st_size / 1024
        img = Image.open(str(image_path))
        Console().print(
            f"  [dim]📁 {image_path}[/]  "
            f"[bold cyan]{img.width}×{img.height}[/]  "
            f"[dim]{size_kb:.1f} KB[/]"
        )
    except Exception:
        pass


# ─── Browser preview server ───────────────────────────────────────────────────

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CLI Thumbnail Studio — Preview</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0d1117;
      color: #c9d1d9;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
      padding: 24px;
    }}
    h1 {{
      color: #58a6ff;
      font-size: 1.4rem;
      margin-bottom: 8px;
      letter-spacing: -0.5px;
    }}
    .meta {{
      color: #7d8590;
      font-size: 0.82rem;
      margin-bottom: 20px;
    }}
    .img-wrap {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 8px 32px #00000088;
      max-width: 100%;
    }}
    img {{
      display: block;
      max-width: min(100vw - 48px, 1280px);
      height: auto;
    }}
    .status {{
      margin-top: 16px;
      font-size: 0.78rem;
      color: #3fb950;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .dot {{
      width: 8px; height: 8px;
      border-radius: 50%;
      background: #3fb950;
      animation: pulse 1.5s ease-in-out infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.3; }}
    }}
    .filename {{
      margin-top: 10px;
      font-size: 0.80rem;
      color: #7d8590;
      font-family: monospace;
    }}
  </style>
</head>
<body>
  <h1>🎨 CLI Thumbnail Studio</h1>
  <p class="meta">Auto-refreshes every 2 seconds</p>
  <div class="img-wrap">
    <img id="preview" src="/image" alt="Generated image">
  </div>
  <div class="status">
    <div class="dot"></div>
    <span id="statusText">Waiting for render…</span>
  </div>
  <p class="filename" id="fname"></p>

  <script>
    let lastSrc = '';
    async function refresh() {{
      try {{
        const r = await fetch('/meta');
        const data = await r.json();
        if (data.path && data.path !== lastSrc) {{
          lastSrc = data.path;
          document.getElementById('preview').src = '/image?' + Date.now();
          document.getElementById('statusText').textContent = 'Updated: ' + new Date().toLocaleTimeString();
          document.getElementById('fname').textContent = data.path;
        }}
      }} catch(e) {{}}
    }}
    setInterval(refresh, 2000);
    refresh();
  </script>
</body>
</html>"""


class _PreviewHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Suppress HTTP log noise

    def do_GET(self):
        global _CURRENT_IMAGE_PATH, _CURRENT_IMAGE_B64
        if self.path == "/" or self.path == "/index.html":
            body = _HTML_TEMPLATE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif self.path.startswith("/image"):
            if _CURRENT_IMAGE_PATH and _CURRENT_IMAGE_PATH.exists():
                data = _CURRENT_IMAGE_PATH.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", len(data))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(204)
                self.end_headers()

        elif self.path == "/meta":
            import json
            path_str = str(_CURRENT_IMAGE_PATH) if _CURRENT_IMAGE_PATH else ""
            body = json.dumps({"path": path_str}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404)
            self.end_headers()


def start_preview_server(auto_open: bool = True) -> str:
    """Start the localhost preview server in a background daemon thread."""
    global _SERVER_THREAD, _SERVER_PORT

    if _SERVER_THREAD and _SERVER_THREAD.is_alive():
        return f"http://localhost:{_SERVER_PORT}"

    server = HTTPServer(("localhost", _SERVER_PORT), _PreviewHandler)

    def _run():
        server.serve_forever()

    _SERVER_THREAD = threading.Thread(target=_run, daemon=True)
    _SERVER_THREAD.start()

    url = f"http://localhost:{_SERVER_PORT}"
    if auto_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    return url


def update_preview(image_path: Path) -> None:
    """Point the preview server to a new image file."""
    global _CURRENT_IMAGE_PATH
    _CURRENT_IMAGE_PATH = image_path


def stop_server() -> None:
    """Nothing to do — daemon thread auto-dies with the process."""
    pass
