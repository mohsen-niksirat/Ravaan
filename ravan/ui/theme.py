"""Unified UI styling palette, typography tokens, and window decoration helpers."""

from __future__ import annotations

import ctypes
import logging
import sys
import tkinter as tk
from dataclasses import dataclass, replace
from pathlib import Path
from tkinter import ttk

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


def get_macos_palette(mode: str = "auto") -> Palette:
    """macOS-style material palette (vibrant accent, hairline border, soft neutrals).

    High-contrast mode intentionally keeps the accessible palette.
    """
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


@dataclass(frozen=True)
class PredictionStyleTokens:
    name: str
    palette: Palette
    corner_radius: float = 8.0
    row_padding_y: int = 4
    row_padding_x: int = 10
    show_separators: bool = False
    separator_color: str = ""
    badge_style: str = "plain"  # "plain" | "circle" | "cyan" | "none"
    selected_row_style: str = "fill"  # "fill" | "leading_bar" | "pill" | "bold_only" | "neon"
    accent_bar_color: str = ""
    show_hint_bar: bool = True
    show_grip: bool = True
    text_align: str = "w"  # "w" | "center"
    confidence_meter_always: bool = False
    border_width: int = 1
    border_color: str = ""
    border_relief: str = "flat"
    alpha: float = 0.95
    acrylic: bool = False
    layout: str = "vertical"  # "vertical" | "horizontal"


def get_fluent_palette(mode: str = "auto") -> Palette:
    """Windows 11 Fluent / Mica palette with subtle elevation and Windows blue accents."""
    base = get_active_palette(mode)
    if base.name == "high_contrast":
        return base
    if base.name == "light":
        return Palette(
            name="fluent_light",
            bg="#F3F3F3",
            fg="#1B1B1B",
            subtext="#5D5D5D",
            card_bg="#FFFFFF",
            accent="#0067C0",
            border="#E5E5E5",
            highlight="#FFFFFF",
            highlight_fg="#1B1B1B",
            alpha=0.96,
            corner_radius=8.0,
            accent_hover="#0078D4",
            card_border="#E5E5E5",
            input_bg="#FFFFFF",
            button_bg="#FFFFFF",
            button_hover="#EDEBE9",
            badge_bg="#EFF6FC",
            badge_fg="#0067C0",
            glow="#0067C0",
        )
    return Palette(
        name="fluent_dark",
        bg="#2C2C2C",
        fg="#FFFFFF",
        subtext="#A0A0A0",
        card_bg="#383838",
        accent="#4CC2FF",
        border="#454545",
        highlight="#383838",
        highlight_fg="#FFFFFF",
        alpha=0.96,
        corner_radius=8.0,
        accent_hover="#70D1FF",
        card_border="#454545",
        input_bg="#262626",
        button_bg="#383838",
        button_hover="#444444",
        badge_bg="#2C2C2C",
        badge_fg="#4CC2FF",
        glow="#4CC2FF",
    )


def get_material_palette(mode: str = "auto") -> Palette:
    """Google Material You expressive tonal palette."""
    base = get_active_palette(mode)
    if base.name == "high_contrast":
        return base
    if base.name == "light":
        return Palette(
            name="material_light",
            bg="#ECE6F0",
            fg="#1D1B20",
            subtext="#49454F",
            card_bg="#E8DEF8",
            accent="#6750A4",
            border="#ECE6F0",
            highlight="#E8DEF8",
            highlight_fg="#1D1B20",
            alpha=0.96,
            corner_radius=20.0,
            accent_hover="#7F67BE",
            card_border="#ECE6F0",
            input_bg="#F7F2FA",
            button_bg="#E8DEF8",
            button_hover="#D9CCE8",
            badge_bg="#EADDFF",
            badge_fg="#6750A4",
            glow="#6750A4",
        )
    return Palette(
        name="material_dark",
        bg="#211A26",
        fg="#E6E1E5",
        subtext="#CAC4D0",
        card_bg="#4A4458",
        accent="#D0BCFF",
        border="#211A26",
        highlight="#4A4458",
        highlight_fg="#FFFFFF",
        alpha=0.96,
        corner_radius=20.0,
        accent_hover="#E8DEF8",
        card_border="#211A26",
        input_bg="#1D192B",
        button_bg="#4A4458",
        button_hover="#5C556C",
        badge_bg="#383244",
        badge_fg="#D0BCFF",
        glow="#D0BCFF",
    )


def get_ios_palette(mode: str = "auto") -> Palette:
    """MacBook & iOS floating panel style (translucent Apple glass, squircle, electric blue)."""
    base = get_active_palette(mode)
    if base.name == "high_contrast":
        return base
    if base.name == "light":
        return Palette(
            name="ios_light",
            bg="#F5F5F7",
            fg="#1D1D1F",
            subtext="#86868B",
            card_bg="#FFFFFF",
            accent="#007AFF",
            border="#D2D2D7",
            highlight="#007AFF",
            highlight_fg="#FFFFFF",
            alpha=0.95,
            corner_radius=16.0,
            accent_hover="#0051A8",
            card_border="#E5E5EA",
            input_bg="#FFFFFF",
            button_bg="#E5E5EA",
            button_hover="#D1D1D6",
            badge_bg="#E5E5EA",
            badge_fg="#007AFF",
            glow="#007AFF",
        )
    return Palette(
        name="ios_dark",
        bg="#1E1E22",
        fg="#F5F5F7",
        subtext="#98989D",
        card_bg="#2C2C30",
        accent="#0A84FF",
        border="#3A3A40",
        highlight="#0A84FF",
        highlight_fg="#FFFFFF",
        alpha=0.94,
        corner_radius=16.0,
        accent_hover="#3395FF",
        card_border="#3A3A40",
        input_bg="#161618",
        button_bg="#2C2C30",
        button_hover="#3A3A3E",
        badge_bg="#2C2C32",
        badge_fg="#0A84FF",
        glow="#0A84FF",
    )


def get_minimal_palette(mode: str = "auto") -> Palette:
    """Linear / Notion monochrome styling: pure black & white with quiet neutrals."""
    base = get_active_palette(mode)
    if base.name == "high_contrast":
        return base
    if base.name == "light":
        return Palette(
            name="minimal_light",
            bg="#FFFFFF",
            fg="#111111",
            subtext="#888888",
            card_bg="#F8F8F8",
            accent="#666666",
            border="#FFFFFF",
            highlight="#F5F5F5",
            highlight_fg="#000000",
            alpha=0.98,
            corner_radius=4.0,
            accent_hover="#444444",
            card_border="#FFFFFF",
            input_bg="#FAFAFA",
            button_bg="#F2F2F2",
            button_hover="#E6E6E6",
            badge_bg="#F0F0F0",
            badge_fg="#555555",
            glow="#888888",
        )
    return Palette(
        name="minimal_dark",
        bg="#000000",
        fg="#E0E0E0",
        subtext="#666666",
        card_bg="#111111",
        accent="#888888",
        border="#000000",
        highlight="#1A1A1A",
        highlight_fg="#FFFFFF",
        alpha=0.98,
        corner_radius=4.0,
        accent_hover="#AAAAAA",
        card_border="#000000",
        input_bg="#0A0A0A",
        button_bg="#161616",
        button_hover="#222222",
        badge_bg="#111111",
        badge_fg="#888888",
        glow="#666666",
    )


def get_neon_palette(mode: str = "auto") -> Palette:
    """Dark cyberpunk / gaming palette with glowing neon magenta and electric green text. Always dark."""
    return Palette(
        name="neon",
        bg="#080B12",
        fg="#00FF66",
        subtext="#548A6A",
        card_bg="#121826",
        accent="#FF007F",
        border="#FF007F",
        highlight="#2A0820",
        highlight_fg="#FFFFFF",
        alpha=0.98,
        corner_radius=6.0,
        accent_hover="#FF3399",
        card_border="#FF007F",
        input_bg="#0E131E",
        button_bg="#180B1E",
        button_hover="#261030",
        badge_bg="#26081E",
        badge_fg="#FF007F",
        glow="#FF007F",
    )


def get_modern_palette(mode: str = "auto") -> Palette:
    """Modern cosmic violet / indigo palette with vibrant purple highlights."""
    base = get_active_palette(mode)
    if base.name == "high_contrast":
        return base
    if base.name == "light":
        return Palette(
            name="modern_light",
            bg="#F5F0FF",
            fg="#22123B",
            subtext="#6B5B82",
            card_bg="#EDE4FC",
            accent="#8A2BE2",
            border="#DDD0F5",
            highlight="#8A2BE2",
            highlight_fg="#FFFFFF",
            alpha=0.96,
            corner_radius=12.0,
            badge_bg="#E2D4F8",
            badge_fg="#8A2BE2",
            glow="#8A2BE2",
        )
    return Palette(
        name="modern_dark",
        bg="#181028",
        fg="#F3E8FF",
        subtext="#A894C4",
        card_bg="#26183C",
        accent="#C77DFF",
        border="#3D2860",
        highlight="#8A2BE2",
        highlight_fg="#FFFFFF",
        alpha=0.96,
        corner_radius=12.0,
        badge_bg="#352054",
        badge_fg="#C77DFF",
        glow="#8A2BE2",
    )


def get_glass_palette(mode: str = "auto") -> Palette:
    """Translucent frosted Aero glass palette with light refraction specular edge."""
    return Palette(
        name="glass",
        bg="#182230",
        fg="#FFFFFF",
        subtext="#8FA6BC",
        card_bg="#223044",
        accent="#64B5F6",
        border="#7A9AB8",
        highlight="#2E466B",
        highlight_fg="#FFFFFF",
        alpha=0.68,
        corner_radius=10.0,
        badge_bg="#203046",
        badge_fg="#64B5F6",
        glow="#64B5F6",
    )


def get_classic_palette(mode: str = "auto") -> Palette:
    """Traditional Windows classic desktop styling with 3D bevel and navy blue selection."""
    return Palette(
        name="classic",
        bg="#D4D0C8",
        fg="#000000",
        subtext="#555555",
        card_bg="#ECE9D8",
        accent="#0A246A",
        border="#808080",
        highlight="#0A246A",
        highlight_fg="#FFFFFF",
        alpha=1.0,
        corner_radius=0.0,
        card_border="#FFFFFF",
        badge_bg="#D4D0C8",
        badge_fg="#0A246A",
        glow="#0A246A",
    )


def _raw_prediction_style(name: str = "macos", mode: str = "auto") -> PredictionStyleTokens:
    """Return raw visual design tokens for the specified prediction UI style."""
    raw_name = (name or "macos").strip().lower()
    base_palette = get_active_palette(mode)
    is_dark = base_palette.name in ("dark", "high_contrast") or (
        mode not in ("light", "high_contrast") and base_palette.name == "dark"
    )

    if raw_name == "fluent":
        pal = get_fluent_palette(mode)
        sep = "#35373E" if is_dark else "#E8E8E8"
        border_col = "#4CC2FF" if is_dark else "#0078D4"
        return PredictionStyleTokens(
            name="fluent",
            palette=pal,
            corner_radius=8.0,
            row_padding_y=5,
            row_padding_x=10,
            show_separators=True,
            separator_color=sep,
            badge_style="plain",
            selected_row_style="leading_bar",
            accent_bar_color="#4CC2FF",
            show_hint_bar=True,
            show_grip=True,
            text_align="w",
            confidence_meter_always=False,
            border_width=2 if is_dark else 1,
            border_color=border_col,
            border_relief="flat",
            alpha=pal.alpha,
            acrylic=False,
        )

    if raw_name == "material":
        pal = get_material_palette(mode)
        sep = "#383244" if is_dark else "#D9CCE8"
        return PredictionStyleTokens(
            name="material",
            palette=pal,
            corner_radius=20.0,
            row_padding_y=6,
            row_padding_x=14,
            show_separators=True,
            separator_color=sep,
            badge_style="circle",
            selected_row_style="pill",
            accent_bar_color="",
            show_hint_bar=True,
            show_grip=True,
            text_align="w",
            confidence_meter_always=False,
            border_width=2,
            border_color="#4B4655" if is_dark else "#CAC4D0",
            border_relief="flat",
            alpha=pal.alpha,
            acrylic=False,
        )

    if raw_name == "ios":
        pal = get_ios_palette(mode)
        sep = "#2D2D30" if is_dark else "#E5E5EA"
        return PredictionStyleTokens(
            name="ios",
            palette=pal,
            corner_radius=16.0,
            row_padding_y=6,
            row_padding_x=14,
            show_separators=True,
            separator_color=sep,
            badge_style="circle",
            selected_row_style="pill",
            accent_bar_color="",
            show_hint_bar=True,
            show_grip=True,
            text_align="w",
            confidence_meter_always=False,
            border_width=1,
            border_color=pal.border,
            border_relief="flat",
            alpha=pal.alpha,
            acrylic=True,
        )

    if raw_name == "minimal":
        pal = get_minimal_palette(mode)
        sep = "#242428" if is_dark else "#EAEAEA"
        return PredictionStyleTokens(
            name="minimal",
            palette=pal,
            corner_radius=4.0,
            row_padding_y=4,
            row_padding_x=10,
            show_separators=True,
            separator_color=sep,
            badge_style="keycap",
            selected_row_style="fill",
            accent_bar_color="#A0A0B0",
            show_hint_bar=True,
            show_grip=True,
            text_align="w",
            confidence_meter_always=False,
            border_width=2,
            border_color="#323238" if is_dark else "#D0D0D8",
            border_relief="flat",
            alpha=pal.alpha,
            acrylic=False,
        )

    if raw_name == "neon":
        pal = get_neon_palette(mode)
        return PredictionStyleTokens(
            name="neon",
            palette=pal,
            corner_radius=6.0,
            row_padding_y=4,
            row_padding_x=10,
            show_separators=True,
            separator_color="#200B1A",
            badge_style="cyan",
            selected_row_style="neon",
            accent_bar_color="#FF007F",
            show_hint_bar=True,
            show_grip=True,
            text_align="w",
            confidence_meter_always=True,
            border_width=1,
            border_color="#FF007F",
            border_relief="flat",
            alpha=pal.alpha,
            acrylic=False,
        )

    if raw_name == "modern":
        pal = get_modern_palette(mode)
        return PredictionStyleTokens(
            name="modern",
            palette=pal,
            corner_radius=12.0,
            row_padding_y=5,
            row_padding_x=12,
            show_separators=True,
            separator_color="#46286E" if is_dark else "#DDD0F5",
            badge_style="plain",
            selected_row_style="pill",
            accent_bar_color="",
            show_hint_bar=True,
            show_grip=True,
            text_align="w",
            confidence_meter_always=False,
            border_width=2,
            border_color="#8A2BE2",
            border_relief="flat",
            alpha=pal.alpha,
            acrylic=False,
        )

    if raw_name == "compact":
        pal = get_active_palette(mode)
        return PredictionStyleTokens(
            name="compact",
            palette=pal,
            corner_radius=4.0,
            row_padding_y=3,
            row_padding_x=8,
            show_separators=True,
            separator_color="#28282E" if is_dark else "#E0E0E5",
            badge_style="plain",
            selected_row_style="fill",
            accent_bar_color="",
            show_hint_bar=True,
            show_grip=False,
            text_align="w",
            confidence_meter_always=False,
            border_width=1,
            border_color=pal.border,
            border_relief="flat",
            alpha=pal.alpha,
            acrylic=False,
        )

    if raw_name == "glass":
        pal = get_glass_palette(mode)
        return PredictionStyleTokens(
            name="glass",
            palette=pal,
            corner_radius=10.0,
            row_padding_y=5,
            row_padding_x=12,
            show_separators=True,
            separator_color="#3C5573",
            badge_style="plain",
            selected_row_style="pill",
            accent_bar_color="",
            show_hint_bar=True,
            show_grip=True,
            text_align="w",
            confidence_meter_always=False,
            border_width=2,
            border_color="#8AB4D8",
            border_relief="flat",
            alpha=pal.alpha,
            acrylic=True,
        )

    if raw_name == "classic":
        pal = get_classic_palette(mode)
        return PredictionStyleTokens(
            name="classic",
            palette=pal,
            corner_radius=0.0,
            row_padding_y=3,
            row_padding_x=8,
            show_separators=False,
            separator_color="",
            badge_style="plain",
            selected_row_style="fill",
            accent_bar_color="",
            show_hint_bar=True,
            show_grip=True,
            text_align="w",
            confidence_meter_always=False,
            border_width=2,
            border_color="#808080",
            border_relief="raised",
            alpha=1.0,
            acrylic=False,
        )

    # Default fallback: macos
    pal = get_macos_palette(mode)
    return PredictionStyleTokens(
        name="macos",
        palette=pal,
        corner_radius=12.0,
        row_padding_y=5,
        row_padding_x=14,
        show_separators=True,
        separator_color="#36363C" if is_dark else "#D6D6DA",
        badge_style="plain",
        selected_row_style="fill",
        accent_bar_color="",
        show_hint_bar=True,
        show_grip=True,
        text_align="w",
        confidence_meter_always=False,
        border_width=1,
        border_color=pal.border,
        border_relief="flat",
        alpha=0.96,
        acrylic=True,
    )


def _relative_luminance(hex_color: str) -> float:
    """Compute WCAG 2.1 relative luminance (0.0 dark .. 1.0 light) for '#rrggbb'."""
    try:
        rgb = int(hex_color.strip().lstrip("#"), 16)
        r, g, b = ((rgb >> 16) & 0xFF) / 255.0, ((rgb >> 8) & 0xFF) / 255.0, (rgb & 0xFF) / 255.0
    except (ValueError, AttributeError):
        return 0.0

    def _lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _contrast_ratio(hex_a: str, hex_b: str) -> float:
    la, lb = _relative_luminance(hex_a), _relative_luminance(hex_b)
    lighter, darker = (la, lb) if la >= lb else (lb, la)
    return (lighter + 0.05) / (darker + 0.05)


def _accessible_highlight_fg(highlight_hex: str, preferred_fg: str | None) -> str:
    """Ensure selected-row text stays legible on bright/neon custom highlight colors."""
    if preferred_fg and _contrast_ratio(highlight_hex, preferred_fg) >= 3.0:
        return preferred_fg
    return "#11111B" if _relative_luminance(highlight_hex) > 0.40 else "#FFFFFF"


def _distinct_from_colorkey(hex_color: str, key_color: str) -> str:
    """Ensure a widget surface color never matches the Win32 LWA_COLORKEY transparency color."""
    if not hex_color or not key_color or hex_color.strip().lower() != key_color.strip().lower():
        return hex_color
    try:
        rgb = int(hex_color.strip().lstrip("#"), 16)
        r, g, b = (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF
        step = 6 if r < 245 and g < 245 and b < 245 else -6
        nr = max(0, min(255, r + step))
        ng = max(0, min(255, g + step))
        nb = max(0, min(255, b + step))
        return f"#{nr:02X}{ng:02X}{nb:02X}"
    except (ValueError, AttributeError):
        return hex_color


def get_prediction_style(
    name: str = "macos",
    mode: str = "auto",
    custom_colors: dict[str, str] | None = None,
    layout: str = "vertical",
) -> PredictionStyleTokens:
    """Return complete visual & layout design tokens for the specified prediction UI style,
    with optional custom color scheme overrides and layout direction."""
    tokens = _raw_prediction_style(name, mode)

    if custom_colors:
        c_bg = custom_colors.get("bg")
        c_fg = custom_colors.get("fg")
        c_accent = custom_colors.get("accent")
        c_border = custom_colors.get("border")
        c_highlight = custom_colors.get("highlight")
        c_highlight_fg = custom_colors.get("highlight_fg")

        orig_pal = tokens.palette
        eff_bg = c_bg or orig_pal.bg
        eff_card_bg = c_bg or orig_pal.card_bg
        eff_highlight = c_highlight or orig_pal.highlight
        if tokens.acrylic:
            # In acrylic styles, Tk sets -transparentcolor to palette.bg; rows/grip/hint
            # paint with card_bg / highlight and must never collide with the colorkey.
            eff_card_bg = _distinct_from_colorkey(eff_card_bg, eff_bg)
            eff_highlight = _distinct_from_colorkey(eff_highlight, eff_bg)

        eff_highlight_fg = _accessible_highlight_fg(
            eff_highlight, c_highlight_fg or orig_pal.highlight_fg
        )

        custom_pal = Palette(
            name=f"{orig_pal.name}_custom",
            bg=eff_bg,
            fg=c_fg or orig_pal.fg,
            subtext=orig_pal.subtext,
            card_bg=eff_card_bg,
            accent=c_accent or orig_pal.accent,
            border=c_border or orig_pal.border,
            highlight=eff_highlight,
            highlight_fg=eff_highlight_fg,
            alpha=orig_pal.alpha,
            corner_radius=orig_pal.corner_radius,
            accent_hover=c_accent or orig_pal.accent_hover,
            card_border=c_border or orig_pal.card_border,
            input_bg=eff_card_bg,
            button_bg=eff_card_bg,
            button_hover=eff_highlight,
            badge_bg=eff_card_bg,
            badge_fg=c_accent or orig_pal.badge_fg,
            glow=c_accent or orig_pal.glow,
        )
        tokens = replace(
            tokens,
            palette=custom_pal,
            border_color=c_border if tokens.border_width > 0 else (c_border or tokens.border_color),
            accent_bar_color=c_accent if tokens.accent_bar_color else "",
            separator_color=c_border if tokens.show_separators else tokens.separator_color,
        )

    norm_layout = "horizontal" if layout == "horizontal" else "vertical"
    if norm_layout == "horizontal":
        tokens = replace(
            tokens,
            layout="horizontal",
            show_separators=True,
            separator_color=tokens.separator_color or tokens.border_color or tokens.palette.border,
            row_padding_y=max(3, min(tokens.row_padding_y, 6)),
            row_padding_x=max(10, tokens.row_padding_x),
        )
    else:
        tokens = replace(tokens, layout="vertical")

    return tokens


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


def _hex_to_colorref(hex_color: str) -> int | None:
    """Convert '#rrggbb' to a Windows COLORREF (0x00bbggrr)."""
    try:
        rgb = int(hex_color.lstrip("#"), 16)
        return ((rgb & 0xFF) << 16) | (rgb & 0xFF00) | ((rgb >> 16) & 0xFF)
    except (ValueError, AttributeError):
        return None


def _enable_acrylic_blur(hwnd: int, hex_color: str) -> bool:
    """Enable acrylic blur-behind behind a popup window (SetWindowCompositionAttribute).

    The tint color carries the material opacity; Tk paints its background with the
    very same color as a transparency key so the blurred desktop shows through.
    Returns False when the OS refuses (then callers must fall back to plain alpha).
    """
    try:
        rgb = int(hex_color.lstrip("#"), 16)
        r, g, b = (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF
        tint = (0xC8 << 24) | (b << 16) | (g << 8) | r  # ABGR with ~78% opacity

        class ACCENT_POLICY(ctypes.Structure):
            _fields_ = [
                ("AccentState", ctypes.c_int),
                ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint),
                ("AnimationId", ctypes.c_int),
            ]

        class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
            _fields_ = [
                ("dwAttribute", ctypes.c_int),
                ("pData", ctypes.c_void_p),
                ("cbData", ctypes.c_size_t),
            ]

        # ACCENT_ENABLE_ACRYLICBLURBEHIND = 4, WCA_ACCENT_POLICY = 19
        accent = ACCENT_POLICY(4, 0, tint, 0)
        data = WINDOWCOMPOSITIONATTRIBDATA(
            19,
            ctypes.cast(ctypes.byref(accent), ctypes.c_void_p),
            ctypes.sizeof(accent),
        )
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        # Force-refresh: re-tinting requires toggling the accent off and on.
        disable = ACCENT_POLICY(0, 0, 0, 0)  # ACCENT_DISABLED
        data_off = WINDOWCOMPOSITIONATTRIBDATA(
            19, ctypes.cast(ctypes.byref(disable), ctypes.c_void_p), ctypes.sizeof(disable)
        )
        user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data_off))
        return bool(user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data)))
    except Exception as exc:  # noqa: BLE001
        log.debug("Acrylic blur unavailable: %s", exc)
        return False


def _disable_acrylic_blur(hwnd: int) -> None:
    """Remove any acrylic accent previously applied to the window."""
    try:

        class ACCENT_POLICY(ctypes.Structure):
            _fields_ = [
                ("AccentState", ctypes.c_int),
                ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint),
                ("AnimationId", ctypes.c_int),
            ]

        class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
            _fields_ = [
                ("dwAttribute", ctypes.c_int),
                ("pData", ctypes.c_void_p),
                ("cbData", ctypes.c_size_t),
            ]

        disable = ACCENT_POLICY(0, 0, 0, 0)  # ACCENT_DISABLED
        data = WINDOWCOMPOSITIONATTRIBDATA(
            19,
            ctypes.cast(ctypes.byref(disable), ctypes.c_void_p),
            ctypes.sizeof(disable),
        )
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
    except Exception:  # noqa: BLE001
        pass


def apply_popup_window_attributes(
    win: tk.Tk | tk.Toplevel,
    palette: Palette,
    show: bool = False,
    acrylic: bool = False,
    border_color: str | None = None,
    corner_radius: float = 8.0,
) -> dict[str, bool]:
    """Apply unified frameless, topmost, opacity, and DWM rounded corners to a popup window."""
    result = {"acrylic": False}
    win.attributes("-topmost", True)
    win.overrideredirect(True)
    try:
        win.attributes("-alpha", palette.alpha)
    except tk.TclError:
        pass

    if sys.platform != "win32":
        return result

    try:
        from ravan.platform import winapi as wapi

        hwnd = win.winfo_id()
        root_hwnd = int(wapi.user32.GetAncestor(hwnd, 2) or hwnd)
        if not root_hwnd:
            return result

        # WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
        style = wapi.user32.GetWindowLongW(root_hwnd, -20)
        wapi.user32.SetWindowLongW(root_hwnd, -20, style | 0x08000088)
        wapi.user32.SetWindowPos(root_hwnd, -1, 0, 0, 0, 0, 0x0037)
        if show:
            wapi.user32.ShowWindow(root_hwnd, wapi.SW_SHOWNOACTIVATE)

        dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)

        # DWM rounded corners (DWMWA_WINDOW_CORNER_PREFERENCE = 33)
        # 1 = DWMWCP_DONOTROUND, 2 = DWMWCP_ROUND, 3 = DWMWCP_ROUNDSMALL
        if corner_radius <= 0:
            corner_val = 1
        elif corner_radius <= 6:
            corner_val = 3
        else:
            corner_val = 2
        corner_pref = ctypes.c_int(corner_val)
        dwmapi.DwmSetWindowAttribute(
            wapi.wintypes.HWND(root_hwnd), 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref)
        )

        # Crisp 1px material border (DWMWA_BORDER_COLOR = 34, Win11)
        if border_color:
            cref = _hex_to_colorref(border_color)
            if cref is not None:
                val = ctypes.c_uint(cref)
                dwmapi.DwmSetWindowAttribute(
                    wapi.wintypes.HWND(root_hwnd), 34, ctypes.byref(val), ctypes.sizeof(val)
                )

        # macOS-style acrylic material (falls back to plain window alpha)
        if acrylic:
            result["acrylic"] = _enable_acrylic_blur(root_hwnd, palette.bg)
        else:
            _disable_acrylic_blur(root_hwnd)
        return result
    except Exception:
        return result


def rects_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    """Return True when two screen-space rectangles (x1, y1, x2, y2) intersect."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def clamp_popup_position(
    win: tk.Tk | tk.Toplevel,
    px: int,
    py: int,
    width: int,
    height: int,
    margin: int = 10,
) -> tuple[int, int]:
    """Clamp popup top-left coordinates safely inside the primary screen dimensions."""
    try:
        sw = max(320, int(win.winfo_screenwidth()))
        sh = max(240, int(win.winfo_screenheight()))
    except Exception:
        return max(margin, px), max(margin, py)
    return max(margin, min(px, sw - width - margin)), max(margin, min(py, sh - height - margin))


def resolve_popup_position(
    win: tk.Tk | tk.Toplevel,
    px: int,
    py: int,
    width: int,
    height: int,
    avoid_rects: list[tuple[int, int, int, int]] | tuple[tuple[int, int, int, int], ...] = (),
) -> tuple[int, int]:
    """Clamp (px, py) to screen and shift vertically away from any overlapping popups."""
    cx, cy = clamp_popup_position(win, px, py, width, height)
    for rect in avoid_rects:
        if rects_overlap((cx, cy, cx + width, cy + height), rect):
            _ax1, ay1, _ax2, ay2 = rect
            above_y = ay1 - height - 8
            candidate_y = above_y if above_y >= 10 else ay2 + 8
            cx, cy = clamp_popup_position(win, cx, candidate_y, width, height)
    return cx, cy


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
    style.configure("Surface.TFrame", background=inp_bg, relief="flat", borderwidth=1, bordercolor=border)

    # LabelFrames (Fluent 2 Elevated Cards)
    style.configure(
        "TLabelframe",
        background=card,
        foreground=fg,
        bordercolor=border,
        lightcolor=border,
        darkcolor=border,
        borderwidth=1,
        relief="solid",
        padding=[14, 10],
    )
    style.configure(
        "TLabelframe.Label",
        background=card,
        foreground=palette.accent,
        font=get_ui_font(size=10, bold=True),
        padding=[6, 2],
    )

    # Labels
    style.configure("TLabel", background=bg, foreground=fg, font=font_regular)
    style.configure("Card.TLabel", background=card, foreground=fg, font=font_regular)
    style.configure("Sub.TLabel", background=bg, foreground=subtext, font=font_sub)
    style.configure("CardSub.TLabel", background=card, foreground=subtext, font=font_sub)
    style.configure("Header.TLabel", background=bg, foreground=fg, font=get_ui_font(size=13, bold=True))
    style.configure("CardHeader.TLabel", background=card, foreground=palette.accent, font=get_ui_font(size=10, bold=True))
    style.configure("Badge.TLabel", background=palette.badge_bg, foreground=palette.badge_fg, font=font_bold, padding=[8, 3])

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

    # Sidebar Navigation Buttons
    style.configure(
        "Nav.TButton",
        background=card,
        foreground=subtext,
        bordercolor=card,
        darkcolor=card,
        lightcolor=card,
        borderwidth=0,
        padding=[14, 9],
        font=font_regular,
        anchor="w",
    )
    style.map(
        "Nav.TButton",
        background=[("pressed", btn_hover), ("active", btn_hover)],
        foreground=[("pressed", fg), ("active", fg)],
    )
    style.configure(
        "NavActive.TButton",
        background=highlight,
        foreground=hl_fg,
        bordercolor=highlight,
        darkcolor=highlight,
        lightcolor=highlight,
        borderwidth=0,
        padding=[14, 9],
        font=font_bold,
        anchor="w",
    )
    style.map(
        "NavActive.TButton",
        background=[("pressed", palette.accent_hover), ("active", palette.accent_hover)],
        foreground=[("pressed", hl_fg), ("active", hl_fg)],
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
        padding=[16, 7],
        font=font_bold,
    )
    style.map(
        "Accent.TButton",
        background=[("pressed", palette.accent_hover), ("active", palette.accent_hover)],
        foreground=[("pressed", hl_fg), ("active", hl_fg)],
    )

    # Spinbox
    style.configure(
        "TSpinbox",
        fieldbackground=inp_bg,
        background=card,
        foreground=fg,
        bordercolor=border,
        lightcolor=border,
        darkcolor=border,
        arrowcolor=fg,
        insertcolor=fg,
        padding=[6, 4],
    )
    style.map(
        "TSpinbox",
        bordercolor=[("focus", highlight)],
        fieldbackground=[("readonly", inp_bg)],
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
        "Hidden.TNotebook",
        background=bg,
        bordercolor=bg,
        borderwidth=0,
        tabmargins=[0, 0, 0, 0],
    )
    style.layout("Hidden.TNotebook.Tab", [])
    style.configure(
        "TNotebook.Tab",
        background=card,
        foreground=subtext,
        bordercolor=border,
        padding=[10, 6],
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
        padding=[4, 3],
    )
    style.map(
        "TCheckbutton",
        indicatorbackground=[("selected", highlight), ("active", card)],
        indicatorcolor=[("selected", hl_fg)],
        background=[("active", bg)],
    )
    style.configure(
        "Card.TCheckbutton",
        background=card,
        foreground=fg,
        indicatorbackground=inp_bg,
        indicatorcolor=palette.accent,
        focuscolor=card,
        padding=[4, 3],
    )
    style.map(
        "Card.TCheckbutton",
        indicatorbackground=[("selected", highlight), ("active", inp_bg)],
        indicatorcolor=[("selected", hl_fg)],
        background=[("active", card)],
    )

    style.configure(
        "TRadiobutton",
        background=bg,
        foreground=fg,
        indicatorbackground=inp_bg,
        indicatorcolor=palette.accent,
        focuscolor=bg,
        padding=[4, 3],
    )
    style.map(
        "TRadiobutton",
        indicatorbackground=[("selected", highlight), ("active", card)],
        indicatorcolor=[("selected", hl_fg)],
        background=[("active", bg)],
    )
    style.configure(
        "Card.TRadiobutton",
        background=card,
        foreground=fg,
        indicatorbackground=inp_bg,
        indicatorcolor=palette.accent,
        focuscolor=card,
        padding=[4, 3],
    )
    style.map(
        "Card.TRadiobutton",
        indicatorbackground=[("selected", highlight), ("active", inp_bg)],
        indicatorcolor=[("selected", hl_fg)],
        background=[("active", card)],
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
