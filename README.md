# 🎨 CLI Thumbnail Studio

A professional, terminal-based image creation tool with **two powerful generators**:

1. **YouTube Thumbnail Generator** — MrBeast-style, gaming, tech, AI, cyberpunk and more
2. **Educational Slide Generator** — Code slides, tutorial steps, timelines, quote cards, comparisons

All inside the terminal. No web browser. No GUI. Pure CLI.

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install Pillow rich colorama

# Optional — speeds up gradient rendering significantly
pip install numpy

# Run the app
python3 run.py
```

---

## 📁 Project Structure

```
cli-thumbnail-studio/
├── run.py                    # Entry point — tool selection menu
├── requirements.txt
├── core/
│   ├── cli.py               # Thumbnail CLI (rich-based)
│   ├── renderer.py          # Thumbnail rendering pipeline
│   ├── themes.py            # 8 thumbnail themes
│   ├── config.py            # ThumbnailConfig dataclass
│   ├── gradient.py          # Gradient engine (NumPy + PIL fallback)
│   ├── effects.py           # Visual effects (vignette, glow, scanlines…)
│   ├── text_engine.py       # Text rendering with shadow/glow/stroke
│   ├── font_manager.py      # Font discovery & fallback system
│   ├── slide_cli.py         # Slide generator CLI
│   ├── slide_renderer.py    # Slide rendering pipeline
│   ├── slide_config.py      # SlideConfig dataclass
│   ├── slide_themes.py      # 11 slide themes
│   ├── components.py        # 19 visual components
│   ├── layouts.py           # 13 layout templates
│   ├── utils.py             # Shared drawing utilities
│   ├── preset_manager.py    # JSON preset save/load
│   └── history_manager.py   # Render history tracking
├── assets/
│   ├── fonts/               # Drop custom .ttf fonts here
│   ├── icons/
│   └── backgrounds/
├── presets/                 # Saved JSON configurations
├── history/                 # Render history log
└── output/                  # Generated PNG images
```

---

## 🎨 Tool 1 — YouTube Thumbnail Generator

### 8 Built-in Themes

| Theme | Style |
|-------|-------|
| `gaming` | Deep purple gradient · orange neon · MrBeast energy |
| `tech` | Near-black · cyan glow · developer aesthetic |
| `dark` | Charcoal · red accent · cinematic drama |
| `minimal` | White background · Apple-clean |
| `cyberpunk` | Black · magenta/cyan neon · sci-fi |
| `educational` | Ocean blue gradient · warm and friendly |
| `finance` | Dark navy · gold accents · professional |
| `ai_futuristic` | Deep space · violet glow · AI/ML content |

### Features
- 4 positioning styles: **centered**, **left-aligned**, **modern YouTube**, **cinematic**
- 4 resolutions: 720p → 4K, supports 16:9 and 9:16
- Auto font-scaling and word-wrap
- Drop shadow, text glow, stroke/outline
- Gradient (horizontal, vertical, diagonal, radial)
- Custom image backgrounds with smart crop
- Badge/label pills
- Preset save & load system
- Auto-timestamped PNG export

---

## 📊 Tool 2 — Educational Slide Generator

### 13 Layout Templates

| Layout | Best for |
|--------|----------|
| `standard` | General purpose — title + body + bullets + code |
| `code_focus` | Code snippet dominates the slide |
| `two_column` | Text left · code/steps right |
| `numbered_steps` | Step-by-step tutorial |
| `quote` | Centered large quote card |
| `checklist` | ✓/○ items with progress bar |
| `comparison` | Side-by-side comparison |
| `statistic` | Big number / key metric |
| `terminal` | Shell commands front and center |
| `tip_card` | Info / warning / success / error card |
| `top_n` | Ranked numbered list |
| `centered` | Intro / outro screens |
| `timeline` | Vertical event timeline |

### 11 Visual Themes

| Theme | Style |
|-------|-------|
| `dark_modern` | GitHub/VS Code dark — developer default |
| `glassmorphism` | Frosted glass cards on purple gradient |
| `cyberpunk` | Magenta & cyan neon on black |
| `educational` | Ocean teal — friendly & approachable |
| `minimal` | Apple gray — clean and distraction-free |
| `futuristic_ai` | Deep space purple — AI/ML content |
| `gaming` | Orange neon on deep purple |
| `apple_style` | White keynote-style — dramatic typography |
| `netflix_doc` | Black + Netflix red — cinematic |
| `coding_tutorial` | Catppuccin Mocha — developer favourite |
| `finance` | Dark navy + gold — premium business |

### Components Available

**Text:** TitleBlock, SubtitleBlock, BodyText  
**Lists:** BulletList, NumberedList, ChecklistBlock, TimelineBlock  
**Media:** CodeBlock (syntax highlighted), TerminalBlock (macOS/Linux style)  
**Cards:** InfoCard (info/warning/success/error/tip), ComparisonBlock  
**Data:** StatCard (big numbers), ProgressRow (labelled bars)  
**UI:** TagsRow, DividerLine, FooterBlock, WatermarkBlock, StepProgressBar

### Syntax Highlighting Support
- Python
- JavaScript / TypeScript
- Bash / Shell
- HTML / CSS
- Generic (no highlighting)

---

## 💡 Usage Examples

### Quick render (programmatic)

```python
from core.config import ThumbnailConfig
from core.themes import get_theme
from core.renderer import render_and_save

cfg = ThumbnailConfig.from_dict({
    **ThumbnailConfig().to_dict(),
    **get_theme("gaming"),
    "title": "INSANE CHALLENGE",
    "subtitle": "100 Players Survive",
    "labels": ["EPIC", "WATCH NOW"],
    "width": 1920, "height": 1080,
})
path = render_and_save(cfg)
print(f"Saved: {path}")
```

```python
from core.slide_config import SlideConfig
from core.slide_renderer import render_slide_and_save

cfg = SlideConfig(
    layout_type="code_focus",
    theme="coding_tutorial",
    title="FastAPI Route Handler",
    subtitle="async def with type hints",
    code_snippet="""from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
async def hello():
    return {"message": "Hello World"}""",
    code_language="python",
    width=1920, height=1080,
)
path = render_slide_and_save(cfg)
print(f"Saved: {path}")
```

---

## 📋 Requirements

| Package | Purpose | Required |
|---------|---------|----------|
| `Pillow >= 10.0` | Image generation | ✅ Yes |
| `rich >= 13.7` | Beautiful terminal UI | ✅ Yes |
| `colorama >= 0.4` | Cross-platform colours | ✅ Yes |
| `numpy >= 1.24` | Fast gradient rendering | ⚡ Optional |

---

## 🗂 Features Checklist

- [x] Smart auto-layout engine
- [x] Dynamic text resizing
- [x] Auto word-wrap
- [x] Overflow prevention
- [x] Responsive aspect-ratio scaling
- [x] Gradient rendering (4 directions + radial)
- [x] Glassmorphism cards (real blur)
- [x] Neon glow text
- [x] Drop shadows
- [x] Syntax-highlighted code blocks
- [x] macOS-style terminal window mockup
- [x] Rounded cards with borders
- [x] Progress bars & step indicators
- [x] Vignette, scanlines, particles, hex grid
- [x] Preset save/load (JSON)
- [x] Render history
- [x] Auto-timestamped filenames
- [x] KeyboardInterrupt safe everywhere
- [x] NumPy optional — pure PIL fallback
- [x] Font fallback engine (searches system fonts)
- [x] Custom image backgrounds with smart crop

---

## 📄 License

MIT License — use freely for personal and commercial projects.

---

Made with ❤️ using Python + Pillow + Rich
