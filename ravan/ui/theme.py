"""Unified UI styling palette, typography tokens, and window decoration helpers."""

from __future__ import annotations

import ctypes
import logging
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass

log = logging.getLogger(__name__)

# Preferred font families for Persian and English UI rendering
_PERSIAN_FONTS = ("Vazirmatn", "Vazir", "Segoe UI", "Tahoma", "sans-serif")
_SYSTEM_FONTS = ("Segoe UI", "Tahoma", "Arial", "sans-serif")
_CONFIDENCE_LEVELS = (" ", "▂", "▅", "█")

_FONTS_LOADED = False


def load_bundled_fonts() -> None:
    """Dynamically register bundled Vazirmatn fonts into Windows GDI session."""
    global _FONTS_LOADED
    if _FONTS_LOADED or sys.platform != "win32":
        return
    _FONTS_LOADED = True

    try:
        gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        # FR_PRIVATE = 0x10 ensures font is private to process and cleaned up on exit
        FR_PRIVATE = 0x10

        search_dirs = [
            Path(__file__).resolve().parent.parent / "data" / "fonts",
            Path(__file__).resolve().parent.parent.parent,
            Path(getattr(sys, "_MEIPASS", "")) / "ravan" / "data" / "fonts",
        ]

        loaded_count = 0
        for sdir in search_dirs:
            if sdir.is_dir():
                for ttf in sdir.glob("*.ttf"):
                    res = gdi32.AddFontResourceExW(str(ttf), FR_PRIVATE, 0)
                    if res > 0:
                        loaded_count += 1

        if loaded_count > 0:
            log.debug("Successfully registered %d bundled typography fonts.", loaded_count)
    except Exception as exc:
        log.debug("Font dynamic loading skipped: %s", exc)


# Automatically load bundled fonts at import time
load_bundled_fonts()


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    fg: str
    subtext: str
    card_bg: str
    accent: str
    border: str
    highlight: str
    highlight_fg: str
    alpha: float = 0.95
    corner_radius: float = 8.0
    # Extended Fluent 2 & design tokens
    accent_hover: str = "#9fc2f9"
    card_border: str = "#303236"
    input_bg: str = "#2d2f31"
    button_bg: str = "#2d2f31"
    button_hover: str = "#3c4043"
    success: str = "#34a853"
    warning: str = "#fbbc04"
    danger: str = "#ea4335"
    badge_bg: str = "#1e293b"
    badge_fg: str = "#38bdf8"
    glow: str = "#1a73e8"

    @classmethod
    def dark(cls) -> Palette:
        return cls(
            name="dark",
            bg="#202124",
            fg="#f1f3f4",
            subtext="#9aa0a6",
            card_bg="#2d2f31",
            accent="#8ab4f8",
            border="#3c4043",
            highlight="#4285f4",
            highlight_fg="#ffffff",
            alpha=0.95,
            corner_radius=8.0,
            accent_hover="#a8c7fa",
            card_border="#35373a",
            input_bg="#1e1f22",
            button_bg="#2e3135",
            button_hover="#3c4043",
            success="#81c995",
            warning="#fdd663",
            danger="#f28b82",
            badge_bg="#1e293b",
            badge_fg="#8ab4f8",
            glow="#4285f4",
        )

    @classmethod
    def light(cls) -> Palette:
        return cls(
            name="light",
            bg="#ffffff",
            fg="#202124",
            subtext="#5f6368",
            card_bg="#f8f9fa",
            accent="#1a73e8",
            border="#dadce0",
            highlight="#1a73e8",
            highlight_fg="#ffffff",
            alpha=0.96,
            corner_radius=8.0,
            accent_hover="#1557b0",
            card_border="#e8eaed",
            input_bg="#ffffff",
            button_bg="#f1f3f4",
            button_hover="#e8eaed",
            success="#1e8e3e",
            warning="#f9ab00",
            danger="#d93025",
            badge_bg="#e8f0fe",
            badge_fg="#1a73e8",
            glow="#1a73e8",
        )

    @classmethod
    def high_contrast(cls) -> Palette:
        return cls(
            name="high_contrast",
            bg="#000000",
            fg="#ffffff",
            subtext="#ffff00",
            card_bg="#121212",
            accent="#ffff00",
            border="#ffffff",
            highlight="#ffff00",
            highlight_fg="#000000",
            alpha=1.0,
            corner_radius=4.0,
            accent_hover="#ffffff",
            card_border="#ffffff",
            input_bg="#000000",
            button_bg="#121212",
            button_hover="#333333",
            success="#00ff00",
            warning="#ffff00",
            danger="#ff0000",
            badge_bg="#121212",
            badge_fg="#ffff00",
            glow="#ffffff",
        )


def get_active_palette(mode: str = "auto") -> Palette:
    """Return Palette based on mode ('auto', 'dark', 'light', 'high_contrast')."""
    if mode == "high_contrast":
        return Palette.high_contrast()
    if mode == "light":
        return Palette.light()
    if mode == "dark":
        return Palette.dark()

    # Auto: query Windows dark mode
    try:
        from ravan.platform.winapi import is_windows_dark_mode

        return Palette.dark() if is_windows_dark_mode() else Palette.light()
    except Exception:
        return Palette.dark()


def get_ui_font(size: int = 10, bold: bool = False, rtl: bool = False) -> tuple[str, int, str]:
    """Return standard font tuple with Vazirmatn / Segoe UI stack."""
    weight = "bold" if bold else "normal"
    family = "Vazirmatn" if rtl else "Segoe UI"
    return (family, size, weight)


def confidence_bar(score: float) -> str:
    """Return a 4-level subtle confidence meter block based on normalized score."""
    clamped = max(0.0, min(1.0, float(score)))
    idx = min(len(_CONFIDENCE_LEVELS) - 1, int(clamped * len(_CONFIDENCE_LEVELS)))
    return _CONFIDENCE_LEVELS[idx]


def apply_popup_window_attributes(win: tk.Tk | tk.Toplevel, palette: Palette, show: bool = False) -> None:
    """Apply unified frameless, topmost, opacity, and DWM rounded corners to a popup window."""
    win.attributes("-topmost", True)
    win.overrideredirect(True)
    try:
        win.attributes("-alpha", palette.alpha)
    except tk.TclError:
        pass

    if sys.platform != "win32":
        return

    try:
        from ravan.platform import winapi as wapi

        hwnd = win.winfo_id()
        root_hwnd = int(wapi.user32.GetAncestor(hwnd, 2) or hwnd)
        if not root_hwnd:
            return

        # WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
        style = wapi.user32.GetWindowLongW(root_hwnd, -20)
        wapi.user32.SetWindowLongW(root_hwnd, -20, style | 0x08000088)
        wapi.user32.SetWindowPos(root_hwnd, 0, 0, 0, 0, 0, 0x0027)
        if show:
            wapi.user32.ShowWindow(root_hwnd, wapi.SW_SHOWNOACTIVATE)

        # DWM rounded corners (DWMWA_WINDOW_CORNER_PREFERENCE = 33)
        corner_pref = ctypes.c_int(2)  # DWMWCP_ROUND
        ctypes.WinDLL("dwmapi", use_last_error=True).DwmSetWindowAttribute(
            wapi.wintypes.HWND(root_hwnd), 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref)
        )
    except Exception:
        pass


def apply_window_decorations(win: tk.Tk | tk.Toplevel, palette: Palette | None = None) -> None:
    """Apply native Windows 11 Fluent dark/light title bar and rounded corners to a window."""
    if palette is None:
        palette = get_active_palette()
    try:
        win.configure(bg=palette.bg)
    except Exception:
        pass

    if sys.platform != "win32":
        return

    try:
        from ravan.platform import winapi as wapi

        win.update_idletasks()
        hwnd = win.winfo_id()
        root_hwnd = int(wapi.user32.GetAncestor(hwnd, 2) or hwnd)
        if not root_hwnd:
            return

        dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)

        # 1. Immersive dark mode (DWMWA_USE_IMMERSIVE_DARK_MODE = 20, fallback 19)
        is_dark = 1 if palette.name in ("dark", "high_contrast") else 0
        val = ctypes.c_int(is_dark)
        res = dwmapi.DwmSetWindowAttribute(root_hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
        if res != 0:
            dwmapi.DwmSetWindowAttribute(root_hwnd, 19, ctypes.byref(val), ctypes.sizeof(val))

        # 2. Window corner preference (DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2)
        corner_pref = ctypes.c_int(2)
        dwmapi.DwmSetWindowAttribute(
            root_hwnd, 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref)
        )
    except Exception as exc:
        log.debug("apply_window_decorations error: %s", exc)


def apply_theme_to_ttk(
    target: tk.Tk | tk.Toplevel | ttk.Style | None = None,
    palette: Palette | None = None,
) -> ttk.Style:
    """Configure modern Fluent design styling for all ttk widgets in the application."""
    if palette is None:
        palette = get_active_palette()

    try:
        style = target if isinstance(target, ttk.Style) else ttk.Style(target)
    except Exception:
        style = ttk.Style()

    try:
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    font_regular = get_ui_font(size=9, bold=False)
    font_bold = get_ui_font(size=9, bold=True)
    font_sub = get_ui_font(size=8, bold=False)

    bg = palette.bg
    fg = palette.fg
    card = palette.card_bg
    subtext = palette.subtext
    border = palette.border
    highlight = palette.highlight
    hl_fg = palette.highlight_fg
    btn_bg = palette.button_bg
    btn_hover = palette.button_hover
    inp_bg = palette.input_bg

    # Root "."
    style.configure(
        ".",
        background=bg,
        foreground=fg,
        font=font_regular,
        bordercolor=border,
        troughcolor=card,
    )

    # Frames
    style.configure("TFrame", background=bg)
    style.configure("Card.TFrame", background=card, relief="flat", borderwidth=1, bordercolor=border)

    # Labels
    style.configure("TLabel", background=bg, foreground=fg, font=font_regular)
    style.configure("Card.TLabel", background=card, foreground=fg, font=font_regular)
    style.configure("Sub.TLabel", background=bg, foreground=subtext, font=font_sub)
    style.configure("CardSub.TLabel", background=card, foreground=subtext, font=font_sub)
    style.configure("Header.TLabel", background=bg, foreground=fg, font=get_ui_font(size=11, bold=True))
    style.configure("CardHeader.TLabel", background=card, foreground=palette.accent, font=get_ui_font(size=10, bold=True))

    # Buttons
    style.configure(
        "TButton",
        background=btn_bg,
        foreground=fg,
        bordercolor=border,
        darkcolor=btn_bg,
        lightcolor=btn_bg,
        borderwidth=1,
        focuscolor=palette.accent,
        padding=[12, 6],
        font=font_regular,
    )
    style.map(
        "TButton",
        background=[("pressed", border), ("active", btn_hover)],
        foreground=[("pressed", fg), ("active", fg)],
        bordercolor=[("active", palette.accent)],
    )

    # Accent Primary Button
    style.configure(
        "Accent.TButton",
        background=highlight,
        foreground=hl_fg,
        bordercolor=highlight,
        darkcolor=highlight,
        lightcolor=highlight,
        borderwidth=0,
        focuscolor=palette.accent_hover,
        padding=[14, 6],
        font=font_bold,
    )
    style.map(
        "Accent.TButton",
        background=[("pressed", palette.accent_hover), ("active", palette.accent_hover)],
        foreground=[("pressed", hl_fg), ("active", hl_fg)],
    )

    # Notebook & Tabs
    style.configure(
        "TNotebook",
        background=bg,
        bordercolor=border,
        borderwidth=0,
        tabmargins=[4, 4, 4, 0],
    )
    style.configure(
        "TNotebook.Tab",
        background=card,
        foreground=subtext,
        bordercolor=border,
        padding=[14, 7],
        font=font_regular,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", bg), ("active", card)],
        foreground=[("selected", palette.accent), ("active", fg)],
        bordercolor=[("selected", border), ("active", border)],
        focuscolor=[("selected", highlight)],
    )

    # Entry & Combobox
    style.configure(
        "TEntry",
        fieldbackground=inp_bg,
        foreground=fg,
        bordercolor=border,
        lightcolor=border,
        darkcolor=border,
        insertcolor=fg,
        padding=[6, 5],
    )
    style.map("TEntry", bordercolor=[("focus", highlight)])

    style.configure(
        "TCombobox",
        fieldbackground=inp_bg,
        background=card,
        foreground=fg,
        bordercolor=border,
        arrowcolor=fg,
        padding=[6, 5],
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", inp_bg)],
        foreground=[("readonly", fg)],
        bordercolor=[("focus", highlight)],
    )

    # Checkbutton & Radiobutton
    style.configure(
        "TCheckbutton",
        background=bg,
        foreground=fg,
        indicatorbackground=inp_bg,
        indicatorcolor=palette.accent,
        focuscolor=bg,
        padding=[2, 2],
    )
    style.map(
        "TCheckbutton",
        indicatorbackground=[("selected", highlight), ("active", card)],
        indicatorcolor=[("selected", hl_fg)],
        background=[("active", bg)],
    )

    style.configure(
        "TRadiobutton",
        background=bg,
        foreground=fg,
        indicatorbackground=inp_bg,
        indicatorcolor=palette.accent,
        focuscolor=bg,
        padding=[2, 2],
    )
    style.map(
        "TRadiobutton",
        indicatorbackground=[("selected", highlight), ("active", card)],
        indicatorcolor=[("selected", hl_fg)],
        background=[("active", bg)],
    )

    # Treeview
    style.configure(
        "Treeview",
        background=card,
        foreground=fg,
        fieldbackground=card,
        bordercolor=border,
        rowheight=28,
        font=font_regular,
    )
    style.map(
        "Treeview",
        background=[("selected", highlight)],
        foreground=[("selected", hl_fg)],
    )
    style.configure(
        "Treeview.Heading",
        background=bg,
        foreground=subtext,
        bordercolor=border,
        font=font_bold,
        padding=[8, 6],
    )
    style.map(
        "Treeview.Heading",
        background=[("active", card)],
        foreground=[("active", fg)],
    )

    # Scrollbar
    style.configure(
        "TScrollbar",
        background=card,
        bordercolor=bg,
        troughcolor=bg,
        arrowcolor=subtext,
    )
    style.map(
        "TScrollbar",
        background=[("active", border), ("pressed", highlight)],
    )

    # Separator
    style.configure("TSeparator", background=border)

    return style
