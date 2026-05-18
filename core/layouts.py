"""
Layout engine for the slide generator.

Each layout function signature:
    render_<name>(canvas, config, theme, fm) -> Image.Image

The layout function is responsible for:
  1. Choosing which components to show
  2. Placing them with correct spacing
  3. Adding theme-specific decorations
  4. Returning the finished RGBA canvas
"""

from __future__ import annotations

from typing import Any, Dict

from PIL import Image, ImageDraw

from core.slide_config import SlideConfig
from core.components import (
    TitleBlock, SubtitleBlock, BodyText, BulletList, NumberedList,
    ChecklistBlock, QuoteBlock, InfoCard, CodeBlock, TerminalBlock,
    StatCard, ComparisonBlock, ProgressRow, TagsRow, DividerLine,
    FooterBlock, WatermarkBlock, StepProgressBar, TimelineBlock,
)
from core.utils import (
    draw_card, draw_glass_card, draw_divider, draw_multiline,
    draw_glow_rect, draw_circle, draw_progress_bar, measure_text, sv,
)
from core.gradient import hex_to_rgb
from core.effects import (
    add_dark_overlay, add_accent_bar, add_scanlines,
    add_particles, add_grid_pattern, add_hex_pattern,
)
from core.font_manager import font_manager as fm_global


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _pad(W: int, H: int, scale: float = 0.042):
    """Consistent left/right edge padding."""
    return int(W * scale)


def _theme_overlay(canvas: Image.Image, theme: Dict, config: SlideConfig) -> Image.Image:
    """Apply theme-global overlays (scanlines, particles, grid, etc.)."""
    if theme.get("show_scanlines"):
        canvas = add_scanlines(canvas, gap=4, opacity=22)
    if theme.get("show_particles"):
        canvas = add_particles(canvas, color=theme.get("accent_color", "#ffffff"), count=60, seed=42)
    if theme.get("show_grid"):
        canvas = add_grid_pattern(canvas, color=theme.get("accent_color", "#ffffff"), opacity=10, spacing=70)
    return canvas


def _draw_header_line(canvas: Image.Image, x: int, y: int, w: int, theme: Dict) -> Image.Image:
    """Optional thin accent line below the header section."""
    if not theme.get("header_line"):
        return canvas
    accent = theme.get("accent_color", "#58a6ff")
    return draw_divider(canvas, x, y, x + w, accent, thickness=2,
                        opacity=theme.get("divider_opacity", 60))


def _render_footer_and_watermark(canvas, config, theme, x, W, H):
    if config.footer_text:
        font = fm_global.get_font("regular", sv(20, H))
        _, fh = measure_text(config.footer_text, font)
        fb = FooterBlock(config.footer_text, size_hint=sv(20, H), align="left")
        fb.render(canvas, x, H - sv(50, H), W - 2 * x, theme, fm_global)

    if config.watermark:
        WatermarkBlock(config.watermark, size_hint=sv(16, H)).render(
            canvas, 0, 0, W, theme, fm_global
        )

    if config.tags:
        tag_h = sv(36, H)
        tr = TagsRow(config.tags, size_hint=sv(18, H))
        canvas, _ = tr.render(canvas, x, H - sv(80, H), W - 2 * x, theme, fm_global)

    return canvas


def _step_header(canvas, config, theme, x, y, W, H):
    """Render step-progress bar if enabled."""
    if config.show_progress:
        spb = StepProgressBar(config.progress_current, config.progress_total,
                              size_hint=sv(20, H))
        canvas, sh = spb.render(canvas, x, y, W - 2 * x, theme, fm_global)
        return canvas, sh + sv(16, H)
    return canvas, 0


# ─────────────────────────────────────────────────────────────────────────────
#  LAYOUTS
# ─────────────────────────────────────────────────────────────────────────────

def render_standard(canvas: Image.Image, config: SlideConfig, theme: Dict) -> Image.Image:
    """
    Universal layout — stacks all provided content top-to-bottom.
    Handles: title, subtitle, body, bullets, numbered steps, code, terminal, tags.
    """
    W, H = canvas.size
    pad_x = _pad(W, H)
    pad_y = sv(55, H)
    inner_w = W - 2 * pad_x
    gap = sv(22, H)
    y = pad_y

    # Step progress
    canvas, sph = _step_header(canvas, config, theme, pad_x, y, W, H)
    y += sph

    # Title
    if config.title:
        t = TitleBlock(config.title, style="bold", size_hint=sv(68, H))
        canvas, h = t.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + gap

    # Subtitle
    if config.subtitle:
        s = SubtitleBlock(config.subtitle, size_hint=sv(36, H))
        canvas, h = s.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + sv(10, H)
        canvas = _draw_header_line(canvas, pad_x, y, inner_w, theme)
        y += sv(18, H) + gap

    # Body text
    if config.body_text:
        b = BodyText(config.body_text, size_hint=sv(28, H))
        canvas, h = b.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + gap

    # Bullets
    if config.bullet_points:
        bl = BulletList(config.bullet_points, size_hint=sv(26, H), indent=sv(38, H))
        canvas, h = bl.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + gap

    # Numbered steps
    if config.numbered_steps:
        nl = NumberedList(config.numbered_steps, size_hint=sv(26, H), circle_r=sv(22, H))
        canvas, h = nl.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + gap

    # Checklist
    if config.checklist_items:
        cl = ChecklistBlock(config.checklist_items, size_hint=sv(26, H))
        canvas, h = cl.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + gap

    # Code
    if config.code_snippet:
        cb = CodeBlock(config.code_snippet, language=config.code_language,
                      size_hint=sv(22, H))
        canvas, h = cb.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + gap

    # Terminal
    if config.terminal_commands:
        tb = TerminalBlock(config.terminal_commands, size_hint=sv(22, H))
        canvas, h = tb.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + gap

    canvas = _render_footer_and_watermark(canvas, config, theme, pad_x, W, H)
    return canvas


def render_code_focus(canvas: Image.Image, config: SlideConfig, theme: Dict) -> Image.Image:
    """
    Code takes centre stage — small title above, code fills the rest.
    """
    W, H = canvas.size
    pad_x = _pad(W, H)
    pad_y = sv(40, H)
    inner_w = W - 2 * pad_x
    y = pad_y

    if config.title:
        t = TitleBlock(config.title, size_hint=sv(52, H))
        canvas, h = t.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + sv(8, H)
    if config.subtitle:
        s = SubtitleBlock(config.subtitle, size_hint=sv(28, H))
        canvas, h = s.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + sv(10, H)
        canvas = _draw_header_line(canvas, pad_x, y, inner_w, theme)
        y += sv(16, H)

    # Code fills remaining height
    avail_h = H - y - sv(60, H)
    code_text = config.code_snippet or "\n".join(config.terminal_commands)
    if config.code_snippet:
        cb = CodeBlock(config.code_snippet, config.code_language, size_hint=sv(22, H))
    else:
        cb = TerminalBlock(config.terminal_commands, size_hint=sv(22, H))
    canvas, _ = cb.render(canvas, pad_x, y, inner_w, theme, fm_global)

    canvas = _render_footer_and_watermark(canvas, config, theme, pad_x, W, H)
    return canvas


def render_two_column(canvas: Image.Image, config: SlideConfig, theme: Dict) -> Image.Image:
    """
    Left column: title + subtitle + body/bullets.
    Right column: code / numbered steps / terminal.
    """
    W, H = canvas.size
    pad_x = _pad(W, H)
    pad_y = sv(55, H)
    gap_col = sv(40, H)
    col_w = (W - 2 * pad_x - gap_col) // 2
    y = pad_y

    # ── Left column ───────────────────────────────────────────────────────────
    lx = pad_x
    ly = y
    if config.title:
        t = TitleBlock(config.title, size_hint=sv(56, H))
        canvas, h = t.render(canvas, lx, ly, col_w, theme, fm_global)
        ly += h + sv(16, H)
    if config.subtitle:
        s = SubtitleBlock(config.subtitle, size_hint=sv(30, H))
        canvas, h = s.render(canvas, lx, ly, col_w, theme, fm_global)
        ly += h + sv(10, H)
        canvas = _draw_header_line(canvas, lx, ly, col_w, theme)
        ly += sv(20, H)
    if config.body_text:
        b = BodyText(config.body_text, size_hint=sv(26, H))
        canvas, h = b.render(canvas, lx, ly, col_w, theme, fm_global)
        ly += h + sv(18, H)
    if config.bullet_points:
        bl = BulletList(config.bullet_points, size_hint=sv(24, H), indent=sv(34, H))
        canvas, h = bl.render(canvas, lx, ly, col_w, theme, fm_global)
        ly += h

    # ── Right column ──────────────────────────────────────────────────────────
    rx = pad_x + col_w + gap_col
    ry = y
    if config.code_snippet:
        cb = CodeBlock(config.code_snippet, config.code_language, size_hint=sv(20, H))
        canvas, h = cb.render(canvas, rx, ry, col_w, theme, fm_global)
        ry += h + sv(18, H)
    if config.terminal_commands:
        tb = TerminalBlock(config.terminal_commands, size_hint=sv(20, H))
        canvas, h = tb.render(canvas, rx, ry, col_w, theme, fm_global)
        ry += h + sv(18, H)
    if config.numbered_steps:
        nl = NumberedList(config.numbered_steps, size_hint=sv(24, H), circle_r=sv(20, H))
        canvas, h = nl.render(canvas, rx, ry, col_w, theme, fm_global)
        ry += h

    canvas = _render_footer_and_watermark(canvas, config, theme, pad_x, W, H)
    return canvas


def render_numbered_steps(canvas: Image.Image, config: SlideConfig, theme: Dict) -> Image.Image:
    """Full-slide numbered-step layout with large step circles."""
    W, H = canvas.size
    pad_x = _pad(W, H)
    pad_y = sv(50, H)
    inner_w = W - 2 * pad_x
    y = pad_y

    canvas, sph = _step_header(canvas, config, theme, pad_x, y, W, H)
    y += sph

    if config.title:
        t = TitleBlock(config.title, size_hint=sv(60, H))
        canvas, h = t.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + sv(14, H)
        canvas = _draw_header_line(canvas, pad_x, y, inner_w, theme)
        y += sv(22, H)

    if config.subtitle:
        s = SubtitleBlock(config.subtitle, size_hint=sv(28, H))
        canvas, h = s.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + sv(24, H)

    items = config.numbered_steps or config.bullet_points
    if items:
        nl = NumberedList(items, size_hint=sv(28, H), circle_r=sv(26, H))
        canvas, _ = nl.render(canvas, pad_x, y, inner_w, theme, fm_global)

    canvas = _render_footer_and_watermark(canvas, config, theme, pad_x, W, H)
    return canvas


def render_quote(canvas: Image.Image, config: SlideConfig, theme: Dict) -> Image.Image:
    """Centered large quote — minimal layout."""
    W, H = canvas.size
    pad_x = _pad(W, H, scale=0.07)
    inner_w = W - 2 * pad_x
    body_color = theme.get("body_color", "#cccccc")

    q = QuoteBlock(config.title or config.body_text,
                   author=config.quote_author or config.subtitle,
                   size_hint=sv(40, H))
    qh = q.measure(inner_w, theme, fm_global)
    y = (H - qh) // 2
    canvas, _ = q.render(canvas, pad_x, y, inner_w, theme, fm_global)
    canvas = _render_footer_and_watermark(canvas, config, theme, pad_x, W, H)
    return canvas


def render_checklist(canvas: Image.Image, config: SlideConfig, theme: Dict) -> Image.Image:
    """Checklist layout with optional progress bar."""
    W, H = canvas.size
    pad_x = _pad(W, H)
    pad_y = sv(55, H)
    inner_w = W - 2 * pad_x
    y = pad_y

    if config.title:
        t = TitleBlock(config.title, size_hint=sv(60, H))
        canvas, h = t.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + sv(14, H)
        canvas = _draw_header_line(canvas, pad_x, y, inner_w, theme)
        y += sv(20, H)

    if config.subtitle:
        s = SubtitleBlock(config.subtitle, size_hint=sv(28, H))
        canvas, h = s.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + sv(20, H)

    items = config.checklist_items or config.bullet_points
    if items:
        # Show progress bar above checklist
        done = config.progress_current
        total = len(items)
        if total > 0:
            pct = done / total
            pr = ProgressRow(f"Progress: {done}/{total} completed", pct, size_hint=sv(22, H))
            canvas, ph = pr.render(canvas, pad_x, y, inner_w, theme, fm_global)
            y += ph + sv(20, H)

        cl = ChecklistBlock(items, done_count=done, size_hint=sv(27, H))
        canvas, _ = cl.render(canvas, pad_x, y, inner_w, theme, fm_global)

    canvas = _render_footer_and_watermark(canvas, config, theme, pad_x, W, H)
    return canvas


def render_comparison(canvas: Image.Image, config: SlideConfig, theme: Dict) -> Image.Image:
    """Two-column comparison."""
    W, H = canvas.size
    pad_x = _pad(W, H)
    pad_y = sv(50, H)
    inner_w = W - 2 * pad_x
    y = pad_y

    if config.title:
        t = TitleBlock(config.title, size_hint=sv(56, H))
        canvas, h = t.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + sv(14, H)
        canvas = _draw_header_line(canvas, pad_x, y, inner_w, theme)
        y += sv(20, H)

    lt = config.comparison_left_title or "Option A"
    rt = config.comparison_right_title or "Option B"
    li = config.comparison_left_items or config.bullet_points[:len(config.bullet_points)//2]
    ri = config.comparison_right_items or config.bullet_points[len(config.bullet_points)//2:]

    comp = ComparisonBlock(lt, rt, li, ri, size_hint=sv(26, H))
    canvas, _ = comp.render(canvas, pad_x, y, inner_w, theme, fm_global)
    canvas = _render_footer_and_watermark(canvas, config, theme, pad_x, W, H)
    return canvas


def render_statistic(canvas: Image.Image, config: SlideConfig, theme: Dict) -> Image.Image:
    """Big number — impressive statistics card."""
    W, H = canvas.size
    pad_x = _pad(W, H)
    inner_w = W - 2 * pad_x

    number = config.stat_number or config.title
    label = config.stat_label or config.subtitle
    sub = config.body_text

    sc = StatCard(number, label, sub)
    sh = sc.measure(inner_w, theme, fm_global)
    y = (H - sh) // 2 - sv(20, H)
    canvas, _ = sc.render(canvas, pad_x, y, inner_w, theme, fm_global)
    canvas = _render_footer_and_watermark(canvas, config, theme, pad_x, W, H)
    return canvas


def render_terminal(canvas: Image.Image, config: SlideConfig, theme: Dict) -> Image.Image:
    """Terminal-centric layout — commands front and center."""
    W, H = canvas.size
    pad_x = _pad(W, H)
    pad_y = sv(40, H)
    inner_w = W - 2 * pad_x
    y = pad_y

    if config.title:
        t = TitleBlock(config.title, size_hint=sv(48, H))
        canvas, h = t.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + sv(12, H)

    tb = TerminalBlock(config.terminal_commands or ["$ echo 'Hello, World!'"],
                      size_hint=sv(22, H))
    canvas, h = tb.render(canvas, pad_x, y, inner_w, theme, fm_global)
    y += h + sv(18, H)

    if config.body_text:
        b = BodyText(config.body_text, size_hint=sv(24, H))
        canvas, _ = b.render(canvas, pad_x, y, inner_w, theme, fm_global)

    canvas = _render_footer_and_watermark(canvas, config, theme, pad_x, W, H)
    return canvas


def render_tip_card(canvas: Image.Image, config: SlideConfig, theme: Dict) -> Image.Image:
    """Single prominent tip / warning / info card."""
    W, H = canvas.size
    pad_x = _pad(W, H)
    inner_w = W - 2 * pad_x

    card_type = "info"
    if any(w in (config.title or "").lower() for w in ("warn", "caution", "danger")):
        card_type = "warning"
    elif any(w in (config.title or "").lower() for w in ("error", "fail", "broken")):
        card_type = "error"
    elif any(w in (config.title or "").lower() for w in ("success", "done", "complete")):
        card_type = "success"
    elif any(w in (config.title or "").lower() for w in ("tip", "hint", "idea")):
        card_type = "tip"

    text = config.body_text or config.subtitle or ""
    ic = InfoCard(text, card_type=card_type, title=config.title, size_hint=sv(28, H))
    ih = ic.measure(inner_w, theme, fm_global)
    y = (H - ih) // 2
    canvas, _ = ic.render(canvas, pad_x, y, inner_w, theme, fm_global)
    canvas = _render_footer_and_watermark(canvas, config, theme, pad_x, W, H)
    return canvas


def render_top_n(canvas: Image.Image, config: SlideConfig, theme: Dict) -> Image.Image:
    """Top-N list with large accent numbers."""
    W, H = canvas.size
    pad_x = _pad(W, H)
    pad_y = sv(55, H)
    inner_w = W - 2 * pad_x
    y = pad_y

    if config.title:
        t = TitleBlock(config.title, size_hint=sv(58, H))
        canvas, h = t.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + sv(14, H)
        canvas = _draw_header_line(canvas, pad_x, y, inner_w, theme)
        y += sv(20, H)

    items = config.numbered_steps or config.bullet_points
    if items:
        nl = NumberedList(items, size_hint=sv(30, H), circle_r=sv(28, H))
        canvas, _ = nl.render(canvas, pad_x, y, inner_w, theme, fm_global)

    canvas = _render_footer_and_watermark(canvas, config, theme, pad_x, W, H)
    return canvas


def render_centered(canvas: Image.Image, config: SlideConfig, theme: Dict) -> Image.Image:
    """Everything centered — great for intro/outro screens."""
    W, H = canvas.size
    pad_x = _pad(W, H, scale=0.08)
    inner_w = W - 2 * pad_x
    glow = theme.get("glow_effects", False)

    # Calculate total content height
    sizes = []
    if config.title:
        tf = TitleBlock(config.title, size_hint=sv(72, H))
        sizes.append(("title", tf.measure(inner_w, theme, fm_global)))
    if config.subtitle:
        sf = SubtitleBlock(config.subtitle, size_hint=sv(36, H))
        sizes.append(("subtitle", sf.measure(inner_w, theme, fm_global)))
    if config.body_text:
        bf = BodyText(config.body_text, size_hint=sv(26, H))
        sizes.append(("body", bf.measure(inner_w, theme, fm_global)))
    if config.tags:
        tr = TagsRow(config.tags, size_hint=sv(20, H))
        sizes.append(("tags", tr.measure(inner_w, theme, fm_global)))

    gap = sv(22, H)
    total_h = sum(h for _, h in sizes) + gap * (len(sizes) - 1)
    y = max(sv(60, H), (H - total_h) // 2)

    for kind, h in sizes:
        if kind == "title":
            t = TitleBlock(config.title, size_hint=sv(72, H))
            font = fm_global.get_font("bold", sv(72, H))
            from core.text_engine import wrap_text
            from core.utils import measure_text
            wrapped = wrap_text(config.title, font, inner_w)
            tw, _ = measure_text(wrapped, font, 8)
            cx = pad_x + (inner_w - tw) // 2
            canvas, _ = t.render(canvas, cx, y, inner_w, theme, fm_global)
        elif kind == "subtitle":
            s = SubtitleBlock(config.subtitle, size_hint=sv(36, H))
            font2 = fm_global.get_font("regular", sv(36, H))
            from core.text_engine import wrap_text as wt2
            wrapped2 = wt2(config.subtitle, font2, inner_w)
            tw2, _ = measure_text(wrapped2, font2, 6)
            cx2 = pad_x + (inner_w - tw2) // 2
            canvas, _ = s.render(canvas, cx2, y, inner_w, theme, fm_global)
        elif kind == "body":
            b = BodyText(config.body_text, size_hint=sv(26, H))
            canvas, _ = b.render(canvas, pad_x, y, inner_w, theme, fm_global)
        elif kind == "tags":
            tr2 = TagsRow(config.tags, size_hint=sv(20, H))
            canvas, _ = tr2.render(canvas, pad_x + (inner_w - min(inner_w, 600)) // 2, y,
                                   min(inner_w, 600), theme, fm_global)
        y += h + gap

    canvas = _render_footer_and_watermark(canvas, config, theme, pad_x, W, H)
    return canvas


def render_timeline(canvas: Image.Image, config: SlideConfig, theme: Dict) -> Image.Image:
    """Vertical timeline layout."""
    W, H = canvas.size
    pad_x = _pad(W, H)
    pad_y = sv(55, H)
    inner_w = W - 2 * pad_x
    y = pad_y

    if config.title:
        t = TitleBlock(config.title, size_hint=sv(56, H))
        canvas, h = t.render(canvas, pad_x, y, inner_w, theme, fm_global)
        y += h + sv(12, H)
        canvas = _draw_header_line(canvas, pad_x, y, inner_w, theme)
        y += sv(20, H)

    items = config.timeline_items or config.numbered_steps or config.bullet_points
    if items:
        tl = TimelineBlock(items, size_hint=sv(26, H), circle_r=sv(18, H))
        canvas, _ = tl.render(canvas, pad_x, y, inner_w, theme, fm_global)

    canvas = _render_footer_and_watermark(canvas, config, theme, pad_x, W, H)
    return canvas


# ─── Layout dispatch ──────────────────────────────────────────────────────────

_LAYOUT_MAP = {
    "standard":       render_standard,
    "code_focus":     render_code_focus,
    "two_column":     render_two_column,
    "numbered_steps": render_numbered_steps,
    "quote":          render_quote,
    "checklist":      render_checklist,
    "comparison":     render_comparison,
    "statistic":      render_statistic,
    "terminal":       render_terminal,
    "tip_card":       render_tip_card,
    "top_n":          render_top_n,
    "centered":       render_centered,
    "timeline":       render_timeline,
}

LAYOUT_NAMES = {
    "standard":       "Standard",
    "code_focus":     "Code Focus",
    "two_column":     "Two Column",
    "numbered_steps": "Numbered Steps",
    "quote":          "Quote Card",
    "checklist":      "Checklist",
    "comparison":     "Comparison",
    "statistic":      "Statistic",
    "terminal":       "Terminal",
    "tip_card":       "Tip / Info Card",
    "top_n":          "Top-N List",
    "centered":       "Centered (Intro/Outro)",
    "timeline":       "Timeline",
}

LAYOUT_HINTS = {
    "standard":       "Fill: title + subtitle + body + bullets + code + terminal",
    "code_focus":     "Fill: title + code_snippet  (code dominates)",
    "two_column":     "Left: title+body+bullets  |  Right: code+terminal+steps",
    "numbered_steps": "Fill: title + numbered_steps",
    "quote":          "Fill: title (as quote text) + subtitle (author)",
    "checklist":      "Fill: title + checklist_items",
    "comparison":     "Fill: comparison_left/right_title + items",
    "statistic":      "Fill: stat_number + stat_label + body_text",
    "terminal":       "Fill: title + terminal_commands + body_text",
    "tip_card":       "Fill: title (card header) + body_text",
    "top_n":          "Fill: title + numbered_steps",
    "centered":       "Fill: title + subtitle + body — all centered",
    "timeline":       "Fill: title + timeline_items",
}


def dispatch(layout_type: str, canvas: Image.Image, config: SlideConfig, theme: Dict) -> Image.Image:
    """Call the correct layout renderer based on config.layout_type."""
    fn = _LAYOUT_MAP.get(layout_type, render_standard)
    return fn(canvas, config, theme)
