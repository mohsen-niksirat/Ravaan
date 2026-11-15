"""Design system palettes, Fluent 2 elevation tokens, and bundled typography."""

from __future__ import annotations

import ctypes
import logging
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

# Preferred font families for Persian and English UI rendering
_PERSIAN_FONTS = ("Vazirmatn", "Vazir", "Segoe UI", "Tahoma", "sans-serif")
_SYSTEM_FONTS = ("Segoe UI", "Tahoma", "Arial", "sans-serif")
_CONFIDENCE_LEVELS = (" ", "▂", "▅", "█")

# Design system 4px spacing rhythm tokens
SPACING: tuple[int, ...] = (4, 8, 12, 16, 24)
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 24

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


def get_ui_font(size: int = 10, bold: bool = False, rtl: bool = False) -> tuple[str, int, str]:
    """Return standard font tuple with Vazirmatn / Segoe UI stack."""
    weight = "bold" if bold else "normal"
    family = "Vazirmatn" if rtl else "Segoe UI"
    return (family, size, weight)


def get_dpi_scale(widget: tk.Misc | None = None) -> float:
    """Return effective DPI scale factor (1.0 at 96 DPI, 1.25 at 120 DPI, etc.)."""
    if widget is not None:
        try:
            pixels_per_inch = float(widget.winfo_fpixels("1i"))
            if pixels_per_inch > 0:
                return max(1.0, min(3.0, pixels_per_inch / 96.0))
        except Exception:
            pass
    return 1.0


def confidence_bar(score: float) -> str:
    """Return a 4-level subtle confidence meter block based on normalized score."""
    clamped = max(0.0, min(1.0, float(score)))
    idx = min(len(_CONFIDENCE_LEVELS) - 1, int(clamped * len(_CONFIDENCE_LEVELS)))
    return _CONFIDENCE_LEVELS[idx]


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
    elevated_bg: str = ""
    border_focus_color: str = ""

    # ── Formalized Fluent 2 Elevation & Border Tiers ──────────────────
    @property
    def bg_base(self) -> str:
        """Lowest window backdrop tier."""
        return self.bg

    @property
    def bg_surface(self) -> str:
        """Primary card / panel surface tier."""
        return self.card_bg

    @property
    def bg_elevated(self) -> str:
        """Elevated modal / header / active card surface tier."""
        if self.elevated_bg:
            return self.elevated_bg
        return "#35383d" if self.name in ("dark", "fluent_dark", "macos_dark") else (
            "#ffffff" if "light" in self.name else self.button_hover
        )

    @property
    def bg_interactive(self) -> str:
        """Interactive control / input / pill background tier."""
        return self.input_bg

    @property
    def border_subtle(self) -> str:
        """1px hairline subtle card border."""
        return self.card_border or self.border

    @property
    def border_focus(self) -> str:
        """Keyboard / active input focus border color."""
        return self.border_focus_color or self.accent

    @classmethod
    def dark(cls) -> Palette:
        return cls(
            name="dark",
            bg="#202124",
            fg="#f1f3f4",
            subtext="#9aa0a6",
            card_bg="#292b2f",
            accent="#8ab4f8",
            border="#3c4043",
            highlight="#4285f4",
            highlight_fg="#ffffff",
            alpha=0.95,
            corner_radius=8.0,
            accent_hover="#a8c7fa",
            card_border="#36393f",
            input_bg="#1e1f22",
            button_bg="#313439",
            button_hover="#3c4043",
            success="#81c995",
            warning="#fdd663",
            danger="#f28b82",
            badge_bg="#1e293b",
            badge_fg="#8ab4f8",
            glow="#4285f4",
            elevated_bg="#32353a",
            border_focus_color="#8ab4f8",
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
            card_border="#e3e6ea",
            input_bg="#ffffff",
            button_bg="#f1f3f4",
            button_hover="#e8eaed",
            success="#1e8e3e",
            warning="#f9ab00",
            danger="#d93025",
            badge_bg="#e8f0fe",
            badge_fg="#1a73e8",
            glow="#1a73e8",
            elevated_bg="#ffffff",
            border_focus_color="#1a73e8",
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
            elevated_bg="#1a1a1a",
            border_focus_color="#ffff00",
        )


def get_active_palette(mode: str = "auto") -> Palette:
    """Return Palette based on mode ('auto', 'dark', 'light', 'high_contrast')."""
    if mode == "high_contrast":
        return Palette.high_contrast()
    if mode == "light":
        return Palette.light()
    if mode == "dark":
        return Palette.dark()

    try:
        from ravan.platform.winapi import is_windows_dark_mode

        return Palette.dark() if is_windows_dark_mode() else Palette.light()
    except Exception:
        return Palette.dark()


def get_macos_palette(mode: str = "auto") -> Palette:
    """macOS-style material palette (vibrant accent, hairline border, soft neutrals)."""
    base = get_active_palette(mode)
    if base.name == "high_contrast":
        return base
    if base.name == "light":
        return Palette(
            name="macos_light",
            bg="#f5f5f7",
            fg="#1d1d1f",
            subtext="#86868b",
            card_bg="#e9e9ee",
            accent="#007aff",
            border="#d6d6da",
            highlight="#0a84ff",
            highlight_fg="#ffffff",
            alpha=0.96,
            corner_radius=12.0,
            accent_hover="#3395ff",
            card_border="#d6d6da",
            input_bg="#ffffff",
            button_bg="#e9e9ee",
            button_hover="#dcdce1",
            badge_bg="#e8f0fe",
            badge_fg="#007aff",
            glow="#0a84ff",
        )
    return Palette(
        name="macos_dark",
        bg="#232326",
        fg="#f5f5f7",
        subtext="#98989d",
        card_bg="#2c2c30",
        accent="#0a84ff",
        border="#3a3a3e",
        highlight="#0a84ff",
        highlight_fg="#ffffff",
        alpha=0.96,
        corner_radius=12.0,
        accent_hover="#409cff",
        card_border="#3a3a3e",
        input_bg="#1b1b1e",
        button_bg="#2c2c30",
        button_hover="#3a3a3f",
        badge_bg="#1e293b",
        badge_fg="#0a84ff",
        glow="#0a84ff",
    )
