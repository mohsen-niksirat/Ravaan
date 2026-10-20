"""Accessibility, contrast ratio, keyboard navigation, and typography test suite."""

from __future__ import annotations

import tkinter as tk

from ravan.core.config import Config
from ravan.ui.quick_tips import QuickTipsWindow
from ravan.ui.theme import (
    _CONFIDENCE_LEVELS,
    Palette,
    confidence_bar,
    get_active_palette,
    get_ui_font,
)


def _hex_to_rgb(hex_code: str) -> tuple[float, float, float]:
    """Convert hex color (#rrggbb) to normalized RGB [0.0, 1.0]."""
    cleaned = hex_code.lstrip("#")
    if len(cleaned) == 3:
        cleaned = "".join(c * 2 for c in cleaned)
    r = int(cleaned[0:2], 16) / 255.0
    g = int(cleaned[2:4], 16) / 255.0
    b = int(cleaned[4:6], 16) / 255.0
    return (r, g, b)


def _relative_luminance(rgb: tuple[float, float, float]) -> float:
    """Calculate WCAG 2.1 relative luminance for an sRGB tuple."""
    def _channel_lum(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (_channel_lum(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(hex1: str, hex2: str) -> float:
    """Calculate WCAG 2.1 contrast ratio between two hex colors (>= 1.0 and <= 21.0)."""
    l1 = _relative_luminance(_hex_to_rgb(hex1))
    l2 = _relative_luminance(_hex_to_rgb(hex2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def test_theme_wcag_contrast_ratios():
    """Verify all palettes achieve WCAG AA contrast ratio (>= 4.5:1 for normal text)."""
    palettes = [
        Palette.dark(),
        Palette.light(),
        Palette.high_contrast(),
    ]

    for p in palettes:
        # Background vs foreground text
        ratio_fg = _contrast_ratio(p.bg, p.fg)
        assert ratio_fg >= 4.5, f"Palette {p.name} failed fg contrast: {ratio_fg:.2f} < 4.5"

        # Card background vs foreground text
        ratio_card_fg = _contrast_ratio(p.card_bg, p.fg)
        assert ratio_card_fg >= 4.5, f"Palette {p.name} failed card fg contrast: {ratio_card_fg:.2f} < 4.5"

        # Highlight background vs highlight text
        ratio_hl = _contrast_ratio(p.highlight, p.highlight_fg)
        assert ratio_hl >= 3.0, f"Palette {p.name} failed highlight contrast: {ratio_hl:.2f} < 3.0"

    # High contrast mode must achieve extreme contrast (>= 15.0:1)
    hc = Palette.high_contrast()
    assert _contrast_ratio(hc.bg, hc.fg) >= 15.0
    assert _contrast_ratio(hc.highlight, hc.highlight_fg) >= 15.0


def test_typography_font_selection():
    """Verify proper Persian (Vazirmatn) and English (Segoe UI) font stacks."""
    # Persian RTL typography
    fa_font = get_ui_font(size=12, bold=False, rtl=True)
    assert fa_font[0] == "Vazirmatn"
    assert fa_font[1] == 12
    assert fa_font[2] == "normal"

    # English LTR typography
    en_font = get_ui_font(size=10, bold=True, rtl=False)
    assert en_font[0] == "Segoe UI"
    assert en_font[1] == 10
    assert en_font[2] == "bold"


def test_no_color_only_signals_for_confidence():
    """Verify confidence meter uses Unicode glyph steps rather than just colors."""
    assert len(_CONFIDENCE_LEVELS) == 4
    assert confidence_bar(0.0) == " "
    assert confidence_bar(0.3) == "▂"
    assert confidence_bar(0.6) == "▅"
    assert confidence_bar(1.0) == "█"


def test_keyboard_navigation_escape_bindings():
    """Verify major windows register Escape key closing bindings for keyboard navigation."""
    root = tk.Tk()
    root.withdraw()
    try:
        cfg = Config()

        # 1. QuickTipsWindow
        tips_win = QuickTipsWindow(parent=root, cfg=cfg)
        tips_win.show()
        top = tips_win._top
        assert top is not None
        binds = top.bind()
        assert any(k in binds for k in ("<Key-Escape>", "<Escape>", "<KeyPress-Escape>"))
        tips_win.close()
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def test_palette_modes_switchable():
    """Verify get_active_palette returns appropriate palette for all modes."""
    assert get_active_palette("dark").name == "dark"
    assert get_active_palette("light").name == "light"
    assert get_active_palette("high_contrast").name == "high_contrast"
