"""
Visual component system for the slide generator.

Every component follows the same contract:
  measure(width, theme, fm) -> int          height needed
  render(canvas, x, y, w, theme, fm) -> (Image, int)   (canvas, height_used)

fm = FontManager instance
All sizes are already scaled to the target canvas by the caller.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter

from core.gradient import hex_to_rgb, hex_to_rgba
from core.font_manager import font_manager
from core.utils import (
    draw_card, draw_glass_card, draw_glow_text, draw_pill,
    draw_circle, draw_progress_bar, draw_divider, draw_accent_card,
    draw_multiline, measure_text, sv, draw_glow_rect,
)
from core.text_engine import wrap_text


# ─── Syntax Highlighter ───────────────────────────────────────────────────────

_PYTHON_KW = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield",
}
_PYTHON_BUILTIN = {
    "print", "len", "range", "type", "isinstance", "str", "int", "float",
    "list", "dict", "set", "tuple", "bool", "input", "open", "super",
    "self", "enumerate", "zip", "map", "filter", "sorted", "reversed",
    "abs", "min", "max", "sum", "round", "any", "all", "dir", "help",
}
_JS_KW = {
    "break", "case", "catch", "class", "const", "continue", "debugger",
    "default", "delete", "do", "else", "export", "extends", "finally",
    "for", "function", "if", "import", "in", "instanceof", "let", "new",
    "return", "static", "super", "switch", "this", "throw", "try",
    "typeof", "var", "void", "while", "with", "yield", "async", "await",
    "of", "from", "null", "undefined", "true", "false",
}
_BASH_KW = {
    "if", "then", "else", "elif", "fi", "for", "do", "done", "while",
    "until", "case", "esac", "function", "return", "echo", "exit",
    "export", "local", "readonly", "source", "alias", "cd", "ls",
    "mkdir", "rm", "cp", "mv", "cat", "grep", "sed", "awk", "curl",
    "wget", "git", "python", "python3", "pip", "apt", "sudo",
}


def _tokenize_line(line: str, language: str) -> List[Tuple[str, str]]:
    """Return list of (text, token_type) for one source line."""
    lang = language.lower()

    # Comment detection
    if lang in ("python",) and line.lstrip().startswith("#"):
        return [(line, "comment")]
    if lang in ("js", "javascript", "ts", "typescript") and line.lstrip().startswith("//"):
        return [(line, "comment")]
    if lang in ("bash", "shell", "sh") and line.lstrip().startswith("#"):
        return [(line, "comment")]

    if lang == "python":
        kw_set, bi_set = _PYTHON_KW, _PYTHON_BUILTIN
    elif lang in ("js", "javascript", "ts", "typescript"):
        kw_set, bi_set = _JS_KW, set()
    elif lang in ("bash", "shell", "sh"):
        kw_set, bi_set = _BASH_KW, set()
    else:
        return [(line, "normal")]

    tokens: List[Tuple[str, str]] = []
    i = 0
    while i < len(line):
        ch = line[i]
        # Inline comment
        if ch == "#" and lang in ("python", "bash", "shell", "sh"):
            tokens.append((line[i:], "comment"))
            break
        if ch in ("'", '"', "`"):
            # String — find closing quote
            j = i + 1
            while j < len(line):
                if line[j] == ch and (j == 0 or line[j - 1] != "\\"):
                    break
                j += 1
            tokens.append((line[i : j + 1], "string"))
            i = j + 1
            continue
        if ch.isdigit() or (ch == "-" and i + 1 < len(line) and line[i + 1].isdigit()):
            j = i + 1
            while j < len(line) and (line[j].isdigit() or line[j] in ".xXabcdefABCDEF"):
                j += 1
            tokens.append((line[i:j], "number"))
            i = j
            continue
        if ch.isalpha() or ch == "_":
            j = i + 1
            while j < len(line) and (line[j].isalnum() or line[j] == "_"):
                j += 1
            word = line[i:j]
            if word in kw_set:
                tokens.append((word, "keyword"))
            elif word in bi_set:
                tokens.append((word, "builtin"))
            else:
                tokens.append((word, "normal"))
            i = j
            continue
        tokens.append((ch, "operator"))
        i += 1
    return tokens


def tokenize_code(code: str, language: str) -> List[List[Tuple[str, str]]]:
    """Return per-line list of (text, token_type) tuples."""
    return [_tokenize_line(ln, language) for ln in code.splitlines()]


# ─── Base component ───────────────────────────────────────────────────────────

class Component:
    def measure(self, width: int, theme: Dict, fm) -> int:
        raise NotImplementedError

    def render(
        self, canvas: Image.Image, x: int, y: int, width: int, theme: Dict, fm
    ) -> Tuple[Image.Image, int]:
        raise NotImplementedError


# ─── Title ────────────────────────────────────────────────────────────────────

class TitleBlock(Component):
    def __init__(self, text: str, style: str = "bold", size_hint: int = 72):
        self.text = text
        self.style = style
        self.size_hint = size_hint    # base size at 1080p

    def _get_font_and_wrapped(self, width: int, fm):
        size = self.size_hint
        for attempt in range(8):
            font = fm.get_font(self.style, size)
            wrapped = wrap_text(self.text, font, width)
            tw, th = measure_text(wrapped, font, spacing=8)
            if tw <= width:
                return font, wrapped, th
            size = max(28, int(size * 0.88))
        font = fm.get_font(self.style, size)
        return font, wrap_text(self.text, font, width), measure_text(wrap_text(self.text, font, width), font, 8)[1]

    def measure(self, width: int, theme: Dict, fm) -> int:
        _, _, h = self._get_font_and_wrapped(width, fm)
        return h

    def render(self, canvas, x, y, width, theme, fm):
        color = theme.get("title_color", "#ffffff")
        glow = theme.get("glow_effects", False)
        font, wrapped, h = self._get_font_and_wrapped(width, fm)
        if glow:
            canvas = draw_glow_text(canvas, wrapped, (x, y), font, color, glow_radius=18, spacing=8)
        else:
            canvas = draw_multiline(canvas, wrapped, (x, y), font, color, spacing=8)
        return canvas, h


# ─── Subtitle ─────────────────────────────────────────────────────────────────

class SubtitleBlock(Component):
    def __init__(self, text: str, size_hint: int = 38):
        self.text = text
        self.size_hint = size_hint

    def _prep(self, width, fm):
        size = self.size_hint
        for _ in range(6):
            font = fm.get_font("regular", size)
            wrapped = wrap_text(self.text, font, width)
            tw, th = measure_text(wrapped, font, 6)
            if tw <= width:
                return font, wrapped, th
            size = max(18, int(size * 0.9))
        font = fm.get_font("regular", size)
        w2 = wrap_text(self.text, font, width)
        return font, w2, measure_text(w2, font, 6)[1]

    def measure(self, width, theme, fm):
        _, _, h = self._prep(width, fm)
        return h

    def render(self, canvas, x, y, width, theme, fm):
        color = theme.get("subtitle_color", "#aaaaaa")
        font, wrapped, h = self._prep(width, fm)
        canvas = draw_multiline(canvas, wrapped, (x, y), font, color, spacing=6)
        return canvas, h


# ─── Body text ────────────────────────────────────────────────────────────────

class BodyText(Component):
    def __init__(self, text: str, size_hint: int = 28, style: str = "regular"):
        self.text = text
        self.size_hint = size_hint
        self.style = style

    def _prep(self, width, fm):
        font = fm.get_font(self.style, self.size_hint)
        wrapped = wrap_text(self.text, font, width)
        _, h = measure_text(wrapped, font, 10)
        return font, wrapped, h

    def measure(self, width, theme, fm):
        _, _, h = self._prep(width, fm)
        return h

    def render(self, canvas, x, y, width, theme, fm):
        color = theme.get("body_color", "#cccccc")
        font, wrapped, h = self._prep(width, fm)
        canvas = draw_multiline(canvas, wrapped, (x, y), font, color, spacing=10)
        return canvas, h


# ─── Bullet list ──────────────────────────────────────────────────────────────

class BulletList(Component):
    def __init__(self, items: List[str], size_hint: int = 28, indent: int = 40):
        self.items = items
        self.size_hint = size_hint
        self.indent = indent

    def _item_height(self, item, font, avail_w) -> int:
        wrapped = wrap_text(item, font, avail_w)
        _, h = measure_text(wrapped, font, 6)
        return h

    def measure(self, width, theme, fm):
        font = fm.get_font("regular", self.size_hint)
        gap = max(10, self.size_hint // 3)
        avail = width - self.indent
        total = 0
        for i, item in enumerate(self.items):
            total += self._item_height(item, font, avail)
            if i < len(self.items) - 1:
                total += gap
        return total

    def render(self, canvas, x, y, width, theme, fm):
        font = fm.get_font("regular", self.size_hint)
        bf_size = max(14, self.size_hint - 4)
        bullet_font = fm.get_font("bold", bf_size)
        body_color = theme.get("body_color", "#cccccc")
        accent = theme.get("accent_color", "#58a6ff")
        bullet_char = theme.get("bullet_char", "•")
        gap = max(10, self.size_hint // 3)
        avail = width - self.indent
        cursor_y = y

        for i, item in enumerate(self.items):
            # Bullet symbol
            canvas = draw_multiline(canvas, bullet_char, (x, cursor_y), bullet_font, accent)
            # Item text
            wrapped = wrap_text(item, font, avail)
            canvas = draw_multiline(canvas, wrapped, (x + self.indent, cursor_y), font, body_color, spacing=6)
            ih = self._item_height(item, font, avail)
            cursor_y += ih + (gap if i < len(self.items) - 1 else 0)

        return canvas, cursor_y - y


# ─── Numbered steps ───────────────────────────────────────────────────────────

class NumberedList(Component):
    def __init__(self, items: List[str], size_hint: int = 28, circle_r: int = 22):
        self.items = items
        self.size_hint = size_hint
        self.circle_r = circle_r

    def measure(self, width, theme, fm):
        font = fm.get_font("regular", self.size_hint)
        indent = self.circle_r * 2 + 20
        gap = max(14, self.size_hint // 2)
        avail = width - indent
        total = 0
        for i, item in enumerate(self.items):
            wrapped = wrap_text(item, font, avail)
            _, h = measure_text(wrapped, font, 6)
            row_h = max(h, self.circle_r * 2)
            total += row_h + (gap if i < len(self.items) - 1 else 0)
        return total

    def render(self, canvas, x, y, width, theme, fm):
        font = fm.get_font("regular", self.size_hint)
        num_font = fm.get_font("bold", self.size_hint - 4)
        circle_fill = theme.get("step_circle_fill", "#58a6ff")
        circle_text = theme.get("step_circle_text", "#ffffff")
        body_color = theme.get("body_color", "#cccccc")
        cr = self.circle_r
        indent = cr * 2 + 20
        gap = max(14, self.size_hint // 2)
        avail = width - indent
        cursor_y = y

        for i, item in enumerate(self.items):
            cy = cursor_y + cr
            canvas = draw_circle(canvas, x + cr, cy, cr, circle_fill)
            num_str = str(i + 1)
            nb = num_font.getbbox(num_str)
            nx = x + cr - (nb[2] - nb[0]) // 2 - nb[0]
            ny = cy - (nb[3] - nb[1]) // 2 - nb[1]
            canvas = draw_multiline(canvas, num_str, (nx, ny), num_font, circle_text)

            wrapped = wrap_text(item, font, avail)
            _, h = measure_text(wrapped, font, 6)
            row_h = max(h, cr * 2)
            ty = cursor_y + (row_h - h) // 2
            canvas = draw_multiline(canvas, wrapped, (x + indent, ty), font, body_color, spacing=6)
            cursor_y += row_h + (gap if i < len(self.items) - 1 else 0)

        return canvas, cursor_y - y


# ─── Checklist ────────────────────────────────────────────────────────────────

class ChecklistBlock(Component):
    def __init__(self, items: List[str], done_count: int = 0, size_hint: int = 26):
        self.items = items
        self.done_count = done_count
        self.size_hint = size_hint

    def measure(self, width, theme, fm):
        font = fm.get_font("regular", self.size_hint)
        indent = self.size_hint + 20
        gap = max(10, self.size_hint // 3)
        avail = width - indent
        total = 0
        for i, item in enumerate(self.items):
            wrapped = wrap_text(item, font, avail)
            _, h = measure_text(wrapped, font, 6)
            total += h + (gap if i < len(self.items) - 1 else 0)
        return total

    def render(self, canvas, x, y, width, theme, fm):
        font = fm.get_font("regular", self.size_hint)
        icon_font = fm.get_font("bold", self.size_hint)
        accent = theme.get("accent_color", "#58a6ff")
        body_color = theme.get("body_color", "#cccccc")
        muted = theme.get("footer_color", "#666666")
        done_char = theme.get("check_char_done", "✓")
        todo_char = theme.get("check_char_todo", "○")
        indent = self.size_hint + 20
        gap = max(10, self.size_hint // 3)
        avail = width - indent
        cursor_y = y

        for i, item in enumerate(self.items):
            done = i < self.done_count
            char = done_char if done else todo_char
            color = accent if done else muted
            txt_color = body_color if done else muted
            canvas = draw_multiline(canvas, char, (x, cursor_y), icon_font, color)
            wrapped = wrap_text(item, font, avail)
            _, h = measure_text(wrapped, font, 6)
            canvas = draw_multiline(canvas, wrapped, (x + indent, cursor_y), font, txt_color, spacing=6)
            cursor_y += h + (gap if i < len(self.items) - 1 else 0)

        return canvas, cursor_y - y


# ─── Quote block ──────────────────────────────────────────────────────────────

class QuoteBlock(Component):
    def __init__(self, text: str, author: str = "", size_hint: int = 38):
        self.text = text
        self.author = author
        self.size_hint = size_hint

    def measure(self, width, theme, fm):
        font = fm.get_font("bold", self.size_hint)
        wrapped = wrap_text(self.text, font, width - 60)
        _, h = measure_text(wrapped, font, 10)
        if self.author:
            af = fm.get_font("regular", max(18, self.size_hint - 12))
            _, ah = measure_text(self.author, af, 4)
            h += ah + 20
        return h + 40

    def render(self, canvas, x, y, width, theme, fm):
        accent = theme.get("accent_color", "#58a6ff")
        body = theme.get("body_color", "#cccccc")
        muted = theme.get("footer_color", "#666666")
        font = fm.get_font("bold", self.size_hint)
        q_font = fm.get_font("bold", self.size_hint + 20)

        # Large quote mark
        canvas = draw_multiline(canvas, "“", (x, y), q_font, accent)
        text_x = x + 60
        wrapped = wrap_text(self.text, font, width - 60)
        canvas = draw_multiline(canvas, wrapped, (text_x, y + 20), font, body, spacing=10)
        _, h = measure_text(wrapped, font, 10)
        cursor_y = y + 20 + h

        if self.author:
            af = fm.get_font("regular", max(18, self.size_hint - 12))
            canvas = draw_multiline(canvas, f"— {self.author}", (text_x, cursor_y + 16), af, muted)
            _, ah = measure_text(self.author, af, 4)
            cursor_y += ah + 20

        return canvas, cursor_y - y + 20


# ─── Info / Warning / Success card ────────────────────────────────────────────

_CARD_ICONS = {
    "info":    ("ℹ", "#58a6ff"),
    "warning": ("⚠", "#f2cc60"),
    "success": ("✓", "#3fb950"),
    "error":   ("✖", "#ff7b72"),
    "tip":     ("💡", "#f2cc60"),
}


class InfoCard(Component):
    """A coloured callout card: info / warning / success / error / tip."""

    def __init__(self, text: str, card_type: str = "info",
                 title: str = "", size_hint: int = 26):
        self.text = text
        self.card_type = card_type.lower()
        self.title = title
        self.size_hint = size_hint

    def measure(self, width, theme, fm):
        pad = 28
        avail = width - pad * 2 - 60
        font = fm.get_font("regular", self.size_hint)
        wrapped = wrap_text(self.text, font, avail)
        _, h = measure_text(wrapped, font, 6)
        if self.title:
            tf = fm.get_font("bold", self.size_hint + 4)
            _, th = measure_text(self.title, tf, 4)
            h += th + 12
        return h + pad * 2

    def render(self, canvas, x, y, width, theme, fm):
        pad = 28
        _, icon_color = _CARD_ICONS.get(self.card_type, ("ℹ", "#58a6ff"))
        icon_char, _ = _CARD_ICONS.get(self.card_type, ("ℹ", "#58a6ff"))
        card_bg = theme.get("card_bg", "#161b22")
        card_border = theme.get("card_border", "#30363d")
        card_radius = theme.get("card_radius", 12)
        body_color = theme.get("body_color", "#cccccc")
        title_color = theme.get("title_color", "#ffffff")
        avail = width - pad * 2 - 60

        h = self.measure(width, theme, fm)
        canvas = draw_accent_card(canvas, x, y, x + width, y + h,
                                  fill=card_bg, accent_color=icon_color, radius=card_radius)

        icon_font = fm.get_font("bold", self.size_hint + 6)
        canvas = draw_multiline(canvas, icon_char, (x + pad + 6, y + pad), icon_font, icon_color)

        tx = x + pad + 60
        ty = y + pad
        if self.title:
            tf = fm.get_font("bold", self.size_hint + 4)
            canvas = draw_multiline(canvas, self.title, (tx, ty), tf, title_color)
            _, th = measure_text(self.title, tf, 4)
            ty += th + 12

        font = fm.get_font("regular", self.size_hint)
        wrapped = wrap_text(self.text, font, avail)
        canvas = draw_multiline(canvas, wrapped, (tx, ty), font, body_color, spacing=6)
        return canvas, h


# ─── Code block ───────────────────────────────────────────────────────────────

class CodeBlock(Component):
    def __init__(self, code: str, language: str = "python",
                 show_header: bool = True, show_line_nums: bool = True,
                 size_hint: int = 22):
        self.code = code.rstrip()
        self.language = language
        self.show_header = show_header
        self.show_line_nums = show_line_nums
        self.size_hint = size_hint
        self._lines = self.code.splitlines()

    def _line_h(self, fm) -> int:
        font = fm.get_font("regular", self.size_hint)
        bb = font.getbbox("Ag")
        return (bb[3] - bb[1]) + max(4, self.size_hint // 5)

    def measure(self, width, theme, fm):
        pad = 20
        header_h = 38 if self.show_header else 0
        line_h = self._line_h(fm)
        return header_h + len(self._lines) * line_h + pad * 2

    def render(self, canvas, x, y, width, theme, fm):
        pad = 20
        header_h = 38 if self.show_header else 0
        line_h = self._line_h(fm)
        total_h = self.measure(width, theme, fm)

        # Card background
        code_bg = theme.get("code_bg", "#0d1117")
        code_border = theme.get("code_border", "#30363d")
        card_radius = min(theme.get("card_radius", 12), 14)

        canvas = draw_card(canvas, x, y, x + width, y + total_h,
                          radius=card_radius, fill=code_bg, fill_alpha=255,
                          border=code_border, border_width=1, shadow=True)

        # Header bar
        if self.show_header:
            hdr_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            hdr_draw = ImageDraw.Draw(hdr_layer)
            r, g, b = hex_to_rgb(code_bg)
            # Slightly lighter header
            hr = min(255, r + 15); hg = min(255, g + 15); hb = min(255, b + 15)
            hdr_draw.rounded_rectangle(
                [(x, y), (x + width, y + header_h)],
                radius=card_radius, fill=(hr, hg, hb, 255)
            )
            hdr_draw.rectangle([(x, y + card_radius), (x + width, y + header_h)],
                               fill=(hr, hg, hb, 255))
            canvas = Image.alpha_composite(canvas.convert("RGBA"), hdr_layer)

            # Window dots
            dot_colors = ["#ff5f56", "#ffbd2e", "#27c93f"]
            dot_r = 7
            for di, dc in enumerate(dot_colors):
                cx = x + 18 + di * 22
                cy = y + header_h // 2
                canvas = draw_circle(canvas, cx, cy, dot_r, dc)

            # Language label
            lang_font = fm.get_font("bold", max(14, self.size_hint - 4))
            lw, _ = measure_text(self.language.upper(), lang_font)
            lx = x + width - lw - 16
            ly = y + (header_h - measure_text(self.language.upper(), lang_font)[1]) // 2
            canvas = draw_multiline(canvas, self.language.upper(), (lx, ly),
                                   lang_font, theme.get("code_line_num", "#484f58"))

        # Code lines
        mono_font = fm.get_font("regular", self.size_hint)
        num_font = fm.get_font("regular", max(12, self.size_hint - 4))
        line_num_w = 50 if self.show_line_nums else 0
        tokens_per_line = tokenize_code(self.code, self.language)

        tok_colors = {
            "keyword":  theme.get("keyword",  "#ff7b72"),
            "string":   theme.get("string",   "#a5d6ff"),
            "comment":  theme.get("comment",  "#8b949e"),
            "number":   theme.get("number",   "#f2cc60"),
            "builtin":  theme.get("builtin",  "#d2a8ff"),
            "operator": theme.get("operator", "#79c0ff"),
            "function": theme.get("function", "#d2a8ff"),
            "normal":   theme.get("code_text", "#c9d1d9"),
        }
        ln_color = theme.get("code_line_num", "#484f58")

        for li, (line_tokens, raw_line) in enumerate(zip(tokens_per_line, self._lines)):
            ly = y + header_h + pad + li * line_h

            # Line number
            if self.show_line_nums:
                ln_str = str(li + 1)
                canvas = draw_multiline(canvas, ln_str, (x + 8, ly),
                                       num_font, ln_color)

            # Syntax-coloured tokens
            tx = x + pad + line_num_w
            for tok_text, tok_type in line_tokens:
                col = tok_colors.get(tok_type, tok_colors["normal"])
                canvas = draw_multiline(canvas, tok_text, (tx, ly), mono_font, col)
                bb = mono_font.getbbox(tok_text)
                tx += bb[2] - bb[0]
                if tx > x + width - pad:
                    break

        return canvas, total_h


# ─── Terminal block ───────────────────────────────────────────────────────────

class TerminalBlock(Component):
    """Linux / macOS terminal window with prompt, commands and optional output."""

    def __init__(self, commands: List[str], show_header: bool = True,
                 os_style: str = "linux", size_hint: int = 22):
        self.commands = commands   # list of "$ command" strings
        self.show_header = show_header
        self.os_style = os_style
        self.size_hint = size_hint

    def _line_h(self, fm):
        font = fm.get_font("regular", self.size_hint)
        bb = font.getbbox("Ag")
        return (bb[3] - bb[1]) + max(4, self.size_hint // 5)

    def measure(self, width, theme, fm):
        header_h = 38 if self.show_header else 0
        return header_h + len(self.commands) * self._line_h(fm) + 32

    def render(self, canvas, x, y, width, theme, fm):
        header_h = 38 if self.show_header else 0
        line_h = self._line_h(fm)
        total_h = self.measure(width, theme, fm)

        term_bg = theme.get("terminal_bg", "#000000")
        term_border = theme.get("terminal_border", "#30363d")
        term_text = theme.get("terminal_text", "#3fb950")
        prompt_col = theme.get("terminal_prompt", "#58a6ff")
        card_r = min(theme.get("card_radius", 12), 14)

        canvas = draw_card(canvas, x, y, x + width, y + total_h,
                          radius=card_r, fill=term_bg, border=term_border,
                          border_width=1, shadow=True)

        if self.show_header:
            hdr_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            r, g, b = hex_to_rgb(term_bg)
            hr = min(255, r + 20); hg = min(255, g + 20); hb = min(255, b + 20)
            ImageDraw.Draw(hdr_layer).rounded_rectangle(
                [(x, y), (x + width, y + header_h)],
                radius=card_r, fill=(hr, hg, hb, 255)
            )
            ImageDraw.Draw(hdr_layer).rectangle(
                [(x, y + card_r), (x + width, y + header_h)],
                fill=(hr, hg, hb, 255)
            )
            canvas = Image.alpha_composite(canvas.convert("RGBA"), hdr_layer)

            dot_colors = ["#ff5f56", "#ffbd2e", "#27c93f"]
            for di, dc in enumerate(dot_colors):
                canvas = draw_circle(canvas, x + 18 + di * 22, y + header_h // 2, 7, dc)

            shell = "bash" if self.os_style == "linux" else "zsh"
            sf = fm.get_font("regular", max(12, self.size_hint - 4))
            canvas = draw_multiline(canvas, shell, (x + width // 2 - 20, y + 8), sf,
                                   theme.get("code_line_num", "#484f58"))

        mono_font = fm.get_font("regular", self.size_hint)
        cy = y + header_h + 16
        for cmd in self.commands:
            # Detect if line is output (not a command)
            if cmd.startswith("$ ") or cmd.startswith("# ") or cmd.startswith("> "):
                prompt = cmd[:2]
                rest = cmd[2:]
                canvas = draw_multiline(canvas, prompt, (x + 16, cy), mono_font, prompt_col)
                bb = mono_font.getbbox(prompt)
                canvas = draw_multiline(canvas, rest, (x + 16 + bb[2] - bb[0], cy),
                                       mono_font, term_text)
            elif cmd.startswith("# "):
                canvas = draw_multiline(canvas, cmd, (x + 16, cy), mono_font,
                                       theme.get("comment", "#8b949e"))
            else:
                canvas = draw_multiline(canvas, cmd, (x + 16, cy), mono_font, term_text)
            cy += line_h

        return canvas, total_h


# ─── Statistics card ─────────────────────────────────────────────────────────

class StatCard(Component):
    def __init__(self, number: str, label: str, sub: str = ""):
        self.number = number
        self.label = label
        self.sub = sub

    def measure(self, width, theme, fm):
        num_font = fm.get_font("bold", 100)
        lbl_font = fm.get_font("regular", 32)
        nw, nh = measure_text(self.number, num_font)
        _, lh = measure_text(self.label, lbl_font)
        return nh + lh + 30

    def render(self, canvas, x, y, width, theme, fm):
        accent = theme.get("accent_color", "#58a6ff")
        body = theme.get("body_color", "#cccccc")
        muted = theme.get("subtitle_color", "#7d8590")
        glow = theme.get("glow_effects", False)

        num_size = 100
        num_font = fm.get_font("bold", num_size)
        while True:
            nw, nh = measure_text(self.number, num_font)
            if nw <= width or num_size <= 48:
                break
            num_size -= 8
            num_font = fm.get_font("bold", num_size)

        nx = x + (width - measure_text(self.number, num_font)[0]) // 2
        if glow:
            canvas = draw_glow_text(canvas, self.number, (nx, y), num_font, accent, glow_radius=24)
        else:
            canvas = draw_multiline(canvas, self.number, (nx, y), num_font, accent)
        _, nh = measure_text(self.number, num_font)
        cy = y + nh + 14

        lbl_font = fm.get_font("regular", 32)
        lw, lh = measure_text(self.label, lbl_font)
        canvas = draw_multiline(canvas, self.label, (x + (width - lw) // 2, cy), lbl_font, body)
        cy += lh

        if self.sub:
            sf = fm.get_font("regular", 22)
            sw, _ = measure_text(self.sub, sf)
            canvas = draw_multiline(canvas, self.sub, (x + (width - sw) // 2, cy + 8), sf, muted)
            cy += 30

        return canvas, cy - y


# ─── Comparison block ─────────────────────────────────────────────────────────

class ComparisonBlock(Component):
    def __init__(self, left_title: str, right_title: str,
                 left_items: List[str], right_items: List[str],
                 size_hint: int = 26):
        self.left_title = left_title
        self.right_title = right_title
        self.left_items = left_items
        self.right_items = right_items
        self.size_hint = size_hint

    def measure(self, width, theme, fm):
        n = max(len(self.left_items), len(self.right_items))
        font = fm.get_font("regular", self.size_hint)
        col_w = width // 2 - 30
        item_h = measure_text("Ag", font)[1] + 14
        header_h = measure_text("Ag", fm.get_font("bold", self.size_hint + 4))[1] + 20
        return header_h + n * item_h + 20

    def render(self, canvas, x, y, width, theme, fm):
        accent = theme.get("accent_color", "#58a6ff")
        accent_alt = theme.get("accent_alt", "#3fb950")
        body = theme.get("body_color", "#cccccc")
        card_bg = theme.get("card_bg", "#161b22")
        card_border = theme.get("card_border", "#30363d")
        card_radius = theme.get("card_radius", 12)
        total_h = self.measure(width, theme, fm)
        gap = 24
        col_w = (width - gap) // 2

        # Cards
        canvas = draw_card(canvas, x, y, x + col_w, y + total_h,
                          radius=card_radius, fill=card_bg, border=accent, border_width=2)
        canvas = draw_card(canvas, x + col_w + gap, y, x + width, y + total_h,
                          radius=card_radius, fill=card_bg, border=accent_alt, border_width=2)

        hdr_font = fm.get_font("bold", self.size_hint + 4)
        body_font = fm.get_font("regular", self.size_hint)
        hh = measure_text("Ag", hdr_font)[1]
        pad = 16
        item_h = measure_text("Ag", body_font)[1] + 14

        # Headers
        canvas = draw_multiline(canvas, self.left_title,  (x + pad, y + pad), hdr_font, accent)
        canvas = draw_multiline(canvas, self.right_title, (x + col_w + gap + pad, y + pad), hdr_font, accent_alt)

        iy = y + pad + hh + 16
        for i in range(max(len(self.left_items), len(self.right_items))):
            if i < len(self.left_items):
                canvas = draw_multiline(canvas, f"• {self.left_items[i]}",
                                       (x + pad, iy), body_font, body)
            if i < len(self.right_items):
                canvas = draw_multiline(canvas, f"• {self.right_items[i]}",
                                       (x + col_w + gap + pad, iy), body_font, body)
            iy += item_h

        return canvas, total_h


# ─── Progress bar row ────────────────────────────────────────────────────────

class ProgressRow(Component):
    def __init__(self, label: str, percent: float, size_hint: int = 24):
        self.label = label
        self.percent = min(max(percent, 0.0), 1.0)
        self.size_hint = size_hint

    def measure(self, width, theme, fm):
        font = fm.get_font("regular", self.size_hint)
        _, h = measure_text(self.label, font)
        return h + 14 + 16

    def render(self, canvas, x, y, width, theme, fm):
        font = fm.get_font("regular", self.size_hint)
        accent = theme.get("accent_color", "#58a6ff")
        body = theme.get("body_color", "#cccccc")
        track = theme.get("progress_track", "#21262d")
        fill = theme.get("progress_fill", "#58a6ff")

        _, lh = measure_text(self.label, font)
        # Label + percent
        pct_str = f"{int(self.percent * 100)}%"
        pf = fm.get_font("bold", self.size_hint)
        pw, _ = measure_text(pct_str, pf)
        canvas = draw_multiline(canvas, self.label, (x, y), font, body)
        canvas = draw_multiline(canvas, pct_str, (x + width - pw, y), pf, accent)
        bar_y = y + lh + 8
        bar_h = 12
        canvas = draw_progress_bar(canvas, x, bar_y, width, bar_h, self.percent, track, fill)
        return canvas, lh + 8 + bar_h + 8


# ─── Tags row ─────────────────────────────────────────────────────────────────

class TagsRow(Component):
    def __init__(self, tags: List[str], size_hint: int = 20):
        self.tags = tags
        self.size_hint = size_hint

    def measure(self, width, theme, fm):
        font = fm.get_font("bold", self.size_hint)
        bb = font.getbbox("Ag")
        h = bb[3] - bb[1]
        return h + 18   # badge height

    def render(self, canvas, x, y, width, theme, fm):
        font = fm.get_font("bold", self.size_hint)
        tag_bg = theme.get("tag_bg", "#1f6feb")
        tag_fg = theme.get("tag_fg", "#ffffff")
        cx = x
        gap = 10
        total_h = self.measure(width, theme, fm)

        for tag in self.tags:
            canvas, bw = draw_pill(canvas, tag, cx, y, tag_bg, tag_fg, font,
                                   pad_x=16, pad_y=8)
            cx += bw + gap
            if cx > x + width:
                break

        return canvas, total_h


# ─── Divider ─────────────────────────────────────────────────────────────────

class DividerLine(Component):
    def __init__(self, gap_above: int = 8, gap_below: int = 8, thickness: int = 2):
        self.gap_above = gap_above
        self.gap_below = gap_below
        self.thickness = thickness

    def measure(self, width, theme, fm):
        return self.gap_above + self.thickness + self.gap_below

    def render(self, canvas, x, y, width, theme, fm):
        accent = theme.get("accent_color", "#58a6ff")
        opacity = theme.get("divider_opacity", 60)
        yy = y + self.gap_above
        canvas = draw_divider(canvas, x, yy, x + width, accent,
                             thickness=self.thickness, opacity=opacity)
        return canvas, self.gap_above + self.thickness + self.gap_below


# ─── Footer ───────────────────────────────────────────────────────────────────

class FooterBlock(Component):
    def __init__(self, text: str, size_hint: int = 20, align: str = "left"):
        self.text = text
        self.size_hint = size_hint
        self.align = align

    def measure(self, width, theme, fm):
        font = fm.get_font("regular", self.size_hint)
        _, h = measure_text(self.text, font)
        return h

    def render(self, canvas, x, y, width, theme, fm):
        font = fm.get_font("regular", self.size_hint)
        color = theme.get("footer_color", "#484f58")
        _, h = measure_text(self.text, font)

        if self.align == "center":
            tw, _ = measure_text(self.text, font)
            pos = (x + (width - tw) // 2, y)
        elif self.align == "right":
            tw, _ = measure_text(self.text, font)
            pos = (x + width - tw, y)
        else:
            pos = (x, y)

        canvas = draw_multiline(canvas, self.text, pos, font, color)
        return canvas, h


# ─── Watermark ───────────────────────────────────────────────────────────────

class WatermarkBlock(Component):
    def __init__(self, text: str, size_hint: int = 18, corner: str = "bottom-right"):
        self.text = text
        self.size_hint = size_hint
        self.corner = corner

    def measure(self, width, theme, fm):
        return 0   # watermark doesn't consume layout space

    def render(self, canvas, x, y, width, theme, fm):
        W, H = canvas.size
        font = fm.get_font("regular", self.size_hint)
        color = theme.get("watermark_color", "#30363d")
        tw, th = measure_text(self.text, font)
        pad = 20
        if self.corner == "bottom-right":
            pos = (W - tw - pad, H - th - pad)
        elif self.corner == "bottom-left":
            pos = (pad, H - th - pad)
        elif self.corner == "top-right":
            pos = (W - tw - pad, pad)
        else:
            pos = (pad, pad)
        canvas = draw_multiline(canvas, self.text, pos, font, color, alpha=160)
        return canvas, 0


# ─── Step progress indicator (top of slide) ───────────────────────────────────

class StepProgressBar(Component):
    """Horizontal dot/segment progress bar — e.g. Step 3 of 7."""

    def __init__(self, current: int, total: int, size_hint: int = 22):
        self.current = current
        self.total = total
        self.size_hint = size_hint

    def measure(self, width, theme, fm):
        return self.size_hint + 8

    def render(self, canvas, x, y, width, theme, fm):
        accent = theme.get("accent_color", "#58a6ff")
        track = theme.get("progress_track", "#21262d")
        body = theme.get("body_color", "#cccccc")
        label_font = fm.get_font("regular", self.size_hint - 4)

        label = f"Step {self.current} of {self.total}"
        lw, lh = measure_text(label, label_font)
        canvas = draw_multiline(canvas, label, (x, y), label_font, body)

        # Segment dots
        seg_w = (width - lw - 20 - self.total * 4) // self.total
        seg_h = 8
        seg_y = y + lh // 2 - seg_h // 2
        sx = x + lw + 20

        for i in range(self.total):
            col = accent if i < self.current else track
            canvas = draw_progress_bar(canvas, sx, seg_y, seg_w, seg_h, 1.0, track, col)
            sx += seg_w + 4

        return canvas, lh + 8


# ─── Timeline ─────────────────────────────────────────────────────────────────

class TimelineBlock(Component):
    def __init__(self, items: List[str], size_hint: int = 26, circle_r: int = 18):
        self.items = items
        self.size_hint = size_hint
        self.circle_r = circle_r

    def measure(self, width, theme, fm):
        font = fm.get_font("regular", self.size_hint)
        avail = width - self.circle_r * 2 - 30
        gap = 24
        total = 0
        for i, item in enumerate(self.items):
            wrapped = wrap_text(item, font, avail)
            _, h = measure_text(wrapped, font, 6)
            row_h = max(h, self.circle_r * 2 + 8)
            total += row_h + (gap if i < len(self.items) - 1 else 0)
        return total

    def render(self, canvas, x, y, width, theme, fm):
        font = fm.get_font("regular", self.size_hint)
        accent = theme.get("accent_color", "#58a6ff")
        body = theme.get("body_color", "#cccccc")
        card_border = theme.get("card_border", "#30363d")
        cr = self.circle_r
        indent = cr * 2 + 30
        gap = 24
        avail = width - indent
        cursor_y = y

        for i, item in enumerate(self.items):
            cy = cursor_y + cr
            # Connecting line to next
            if i < len(self.items) - 1:
                wrapped_cur = wrap_text(item, font, avail)
                row_h_cur = max(measure_text(wrapped_cur, font, 6)[1], cr * 2 + 8)
                line_y1 = cy + cr
                line_y2 = cursor_y + row_h_cur + gap
                # Vertical connecting line between circles
                canvas = canvas.convert("RGBA")
                vline_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
                r, g, b = hex_to_rgb(card_border)
                ImageDraw.Draw(vline_layer).line(
                    [(x + cr, line_y1), (x + cr, line_y2)],
                    fill=(r, g, b, 100), width=2
                )
                canvas = Image.alpha_composite(canvas, vline_layer)

            canvas = draw_circle(canvas, x + cr, cy, cr, accent)
            wrapped = wrap_text(item, font, avail)
            _, h = measure_text(wrapped, font, 6)
            row_h = max(h, cr * 2 + 8)
            ty = cursor_y + (row_h - h) // 2
            canvas = draw_multiline(canvas, wrapped, (x + indent, ty), font, body, spacing=6)
            cursor_y += row_h + (gap if i < len(self.items) - 1 else 0)

        return canvas, cursor_y - y
