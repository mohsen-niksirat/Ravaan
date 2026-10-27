"""Unified UI styling palette, typography tokens, and window decoration helpers."""

from __future__ import annotations

import ctypes
import logging
import sys
import tkinter as tk
from dataclasses import dataclass

log = logging.getLogger(__name__)

# Preferred font families for Persian and English UI rendering
_PERSIAN_FONTS = ("Vazirmatn", "Vazir", "Segoe UI", "Tahoma", "sans-serif")
_SYSTEM_FONTS = ("Segoe UI", "Tahoma", "Arial", "sans-serif")
_CONFIDENCE_LEVELS = (" ", "▂", "▅", "█")


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

        # Get top-level HWND
        hwnd = win.winfo_id()
        root_hwnd = int(wapi.user32.GetAncestor(hwnd, 2) or hwnd)
        if not root_hwnd:
            return

        # WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
        style = wapi.user32.GetWindowLongW(root_hwnd, -20)
        wapi.user32.SetWindowLongW(root_hwnd, -20, style | 0x08000088)
        # Apply style changes without activating
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
