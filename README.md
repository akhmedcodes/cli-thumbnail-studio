<div align="center">

# 🎨 CLI Thumbnail Studio

**Professional image generator that runs entirely in the terminal.**
Create YouTube thumbnails and educational slides — no GUI, no browser, pure Python CLI.

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Pillow](https://img.shields.io/badge/Pillow-10%2B-ED8B00?style=flat-square)](https://pillow.readthedocs.io)
[![Rich](https://img.shields.io/badge/Rich-13%2B-A020F0?style=flat-square)](https://rich.readthedocs.io)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![GitHub Pages](https://img.shields.io/badge/Docs-GitHub%20Pages-0969DA?style=flat-square&logo=github)](https://akhmedcodes.github.io/cli-thumbnail-studio/)

```bash
pip install Pillow rich colorama
python3 run.py
```

[📖 Full Documentation](https://akhmedcodes.github.io/cli-thumbnail-studio/) · [⭐ Star on GitHub](https://github.com/akhmedcodes/cli-thumbnail-studio)

</div>

---

## ✨ What it generates

| Tool | Output |
|------|--------|
| **Thumbnail Generator** | YouTube-ready PNGs — gaming, tech, AI, cyberpunk, minimal, finance styles |
| **Slide Generator** | Code slides, tutorial steps, timelines, comparison cards, quote screens |
| **Batch Renderer** | All 11 themes or 13 layouts in parallel — one command |

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/akhmedcodes/cli-thumbnail-studio.git
cd cli-thumbnail-studio

# Install
pip install Pillow rich colorama
# Optional — makes gradients 10× faster
pip install numpy

# Run
python3 run.py
```

**CLI shortcuts:**
```bash
python3 run.py --tool 1          # Thumbnail generator (no menu)
python3 run.py --tool 2          # Slide generator (no menu)
python3 run.py --demo            # Generate 10-slide demo gallery
python3 run.py --batch-themes    # Render all 11 themes in parallel
python3 run.py --history         # Browse render history
python3 run.py --preview         # Live browser preview at localhost:7771
python3 run.py --help            # Full help
```

---

## 🎨 Tool 1 — YouTube Thumbnail Generator

8 built-in themes, 4 layout styles, 720p → 4K, auto font-scaling, shadows, glows, gradients.

**Themes:** `gaming` · `tech` · `dark` · `minimal` · `cyberpunk` · `educational` · `finance` · `ai_futuristic`

**Programmatic usage:**
```python
from core.config import ThumbnailConfig
from core.themes import get_theme
from core.renderer import render_and_save

cfg = ThumbnailConfig.from_dict({
    **ThumbnailConfig().to_dict(),
    **get_theme("gaming"),
    "title": "INSANE CHALLENGE",
    "subtitle": "100 Players Survive",
    "labels": ["EPIC", "NEW"],
    "width": 1920, "height": 1080,
})
path = render_and_save(cfg)
```

---

## 📊 Tool 2 — Educational Slide Generator

### 13 Layout Templates

| Layout | Use case |
|--------|----------|
| `standard` | All-purpose: title + body + bullets + code |
| `code_focus` | Code dominates, small title above |
| `two_column` | Text left · code/steps right |
| `numbered_steps` | Step-by-step tutorial |
| `quote` | Large centered quote |
| `checklist` | ✓/○ items with progress bar |
| `comparison` | Side-by-side VS layout |
| `statistic` | Big number / key metric |
| `terminal` | Shell commands window |
| `tip_card` | Info / warning / success card |
| `top_n` | Ranked numbered list |
| `centered` | Intro / outro screen |
| `timeline` | Vertical event timeline |

### 11 Visual Themes

`dark_modern` · `glassmorphism` · `cyberpunk` · `educational` · `minimal` · `futuristic_ai` · `gaming` · `apple_style` · `netflix_doc` · `coding_tutorial` · `finance`

### Syntax-highlighted code blocks

Supports Python · JavaScript/TypeScript · Bash/Shell · HTML/CSS

```python
from core.slide_config import SlideConfig
from core.slide_renderer import render_slide_and_save

cfg = SlideConfig(
    layout_type="code_focus",
    theme="coding_tutorial",
    title="FastAPI Route Handler",
    code_snippet="""@app.post("/items/")
async def create_item(item: Item):
    return {"item": item, "status": "created"}""",
    code_language="python",
    width=1920, height=1080,
)
path = render_slide_and_save(cfg)
```

---

## ⚡ Batch Rendering

```python
from core.slide_config import SlideConfig
from core.batch import BatchRenderer

cfg = SlideConfig(title="My Slide", subtitle="All Themes", width=1920, height=1080)
br = BatchRenderer(cfg)

br.theme_sweep()    # 11 themes in parallel  → output/batch_themes/
br.layout_sweep()   # 13 layouts in parallel → output/batch_layouts/
br.color_sweep()    # 8 accent variations    → output/batch_colors/
br.ratio_sweep()    # 16:9 / 9:16 / 1:1     → output/batch_ratios/
```

---

## 🌐 Live Preview

```bash
python3 run.py --preview
# Opens http://localhost:7771
# Auto-refreshes every 2 seconds after each render
```

---

## 📁 Project Structure

```
cli-thumbnail-studio/
├── run.py                    # Entry point + 7-item main menu
├── requirements.txt
├── docs/                     # GitHub Pages documentation site
│   └── index.html
├── core/
│   ├── cli.py               # Thumbnail CLI (rich-based interactive)
│   ├── renderer.py          # Thumbnail rendering pipeline
│   ├── themes.py            # 8 thumbnail themes
│   ├── config.py            # ThumbnailConfig dataclass
│   ├── slide_cli.py         # Slide generator CLI
│   ├── slide_renderer.py    # Slide rendering pipeline
│   ├── slide_config.py      # SlideConfig dataclass
│   ├── slide_themes.py      # 11 slide themes
│   ├── components.py        # 19 visual components
│   ├── layouts.py           # 13 layout templates
│   ├── gradient.py          # Gradient engine (NumPy + PIL fallback)
│   ├── effects.py           # Vignette, glow, scanlines, particles…
│   ├── text_engine.py       # Text rendering with shadow/glow/stroke
│   ├── font_manager.py      # Font discovery + fallback system
│   ├── utils.py             # Shared drawing utilities
│   ├── batch.py             # Parallel batch renderer + history browser
│   ├── preview.py           # Terminal preview + browser server
│   ├── preset_manager.py    # JSON preset save/load
│   └── history_manager.py   # Render history tracking
├── assets/
│   ├── fonts/               # Drop custom .ttf fonts here
│   ├── icons/
│   └── backgrounds/
├── presets/                 # Saved configurations (JSON)
├── history/                 # render history log
└── output/                  # Generated PNG files
```

---

## 📋 Requirements

| Package | Purpose | Required |
|---------|---------|:--------:|
| `Pillow >= 10.0` | Image generation | ✅ |
| `rich >= 13.7` | Terminal UI | ✅ |
| `colorama >= 0.4` | Cross-platform colours | ✅ |
| `numpy >= 1.24` | Fast gradients (10× speedup) | ⚡ Optional |

---

## 🔑 Features

- ✅ Smart auto-layout with overflow prevention
- ✅ Dynamic font scaling and word-wrap
- ✅ Syntax-highlighted code blocks (Python · JS · Bash · HTML)
- ✅ macOS-style terminal window mockup
- ✅ Real glassmorphism (blurs content behind cards)
- ✅ Neon glow, drop shadows, stroke, vignette
- ✅ Gradient: horizontal, vertical, diagonal, radial
- ✅ Parallel batch rendering (4 threads)
- ✅ Live browser preview (auto-refresh, no WebSocket dep)
- ✅ Preset save/load (JSON)
- ✅ Full render history
- ✅ Auto-timestamped filenames
- ✅ NumPy optional — pure PIL fallback always works
- ✅ System font discovery (Linux · macOS · Windows)
- ✅ Custom image backgrounds with smart centre-crop
- ✅ KeyboardInterrupt safe everywhere
- ✅ `--verbose` / `--silent` / `--help` CLI flags

---

## 📄 License

MIT — free for personal and commercial use.

---

<div align="center">
Made with ❤️ using Python · Pillow · Rich<br>
<a href="https://akhmedcodes.github.io/cli-thumbnail-studio/">📖 Documentation</a> ·
<a href="https://github.com/akhmedcodes/cli-thumbnail-studio/issues">🐛 Issues</a> ·
<a href="https://github.com/akhmedcodes/cli-thumbnail-studio/pulls">🔀 Pull Requests</a>
</div>
