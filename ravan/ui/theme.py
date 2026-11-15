"""Unified UI styling palette, typography tokens, TTK theme, and window decoration helpers."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ravan.ui.theme_dwm import (
    _disable_acrylic_blur,
    _enable_acrylic_blur,
    _hex_to_colorref,
    _resolve_live_tk_parent,
    _set_dwm_attribute,
    _set_window_composition_accent,
    apply_popup_window_attributes,
    apply_window_decorations,
    clamp_popup_position,
    create_managed_toplevel,
    destroy_managed_toplevel,
    rects_overlap,
    resolve_popup_position,
)
from ravan.ui.theme_palettes import (
    _CONFIDENCE_LEVELS,
    _PERSIAN_FONTS,
    _SYSTEM_FONTS,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
    SPACING,
    Palette,
    confidence_bar,
    get_active_palette,
    get_dpi_scale,
    get_macos_palette,
    get_ui_font,
    load_bundled_fonts,
)
from ravan.ui.theme_prediction_styles import (
    PredictionStyleTokens,
    _accessible_highlight_fg,
    _contrast_ratio,
    _distinct_from_colorkey,
    _raw_prediction_style,
    _relative_luminance,
    get_classic_palette,
    get_fluent_palette,
    get_glass_palette,
    get_ios_palette,
    get_material_palette,
    get_minimal_palette,
    get_modern_palette,
    get_neon_palette,
    get_prediction_style,
)


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

    bg, fg, card = palette.bg_base, palette.fg, palette.bg_surface
    subtext, border = palette.subtext, palette.border_subtle
    highlight, hl_fg = palette.highlight, palette.highlight_fg
    btn_bg, btn_hover, inp_bg = palette.button_bg, palette.button_hover, palette.bg_interactive

    style.configure(".", background=bg, foreground=fg, font=font_regular, bordercolor=border, troughcolor=card)
    style.configure("TFrame", background=bg)
    style.configure("Card.TFrame", background=card, relief="flat", borderwidth=1, bordercolor=border)
    style.configure("Surface.TFrame", background=inp_bg, relief="flat", borderwidth=1, bordercolor=border)

    style.configure(
        "TLabelframe", background=card, foreground=fg, bordercolor=border, lightcolor=border,
        darkcolor=border, borderwidth=1, relief="solid", padding=[14, 10],
    )
    style.configure(
        "TLabelframe.Label", background=card, foreground=palette.accent,
        font=get_ui_font(size=10, bold=True), padding=[6, 2],
    )

    style.configure("TLabel", background=bg, foreground=fg, font=font_regular)
    style.configure("Card.TLabel", background=card, foreground=fg, font=font_regular)
    style.configure("Sub.TLabel", background=bg, foreground=subtext, font=font_sub)
    style.configure("CardSub.TLabel", background=card, foreground=subtext, font=font_sub)
    style.configure("Header.TLabel", background=bg, foreground=fg, font=get_ui_font(size=13, bold=True))
    style.configure("CardHeader.TLabel", background=card, foreground=palette.accent, font=get_ui_font(size=10, bold=True))
    style.configure("Badge.TLabel", background=palette.badge_bg, foreground=palette.badge_fg, font=font_bold, padding=[8, 3])

    style.configure(
        "TButton", background=btn_bg, foreground=fg, bordercolor=border, darkcolor=btn_bg,
        lightcolor=btn_bg, borderwidth=1, focuscolor=palette.border_focus, padding=[12, 6], font=font_regular,
    )
    style.map(
        "TButton",
        background=[("pressed", border), ("active", btn_hover)],
        foreground=[("pressed", fg), ("active", fg)],
        bordercolor=[("active", palette.border_focus)],
    )

    style.configure(
        "Nav.TButton", background=card, foreground=subtext, bordercolor=card, darkcolor=card,
        lightcolor=card, borderwidth=0, padding=[14, 9], font=font_regular, anchor="w",
    )
    style.map("Nav.TButton", background=[("pressed", btn_hover), ("active", btn_hover)], foreground=[("pressed", fg), ("active", fg)])

    style.configure(
        "NavActive.TButton", background=highlight, foreground=hl_fg, bordercolor=highlight,
        darkcolor=highlight, lightcolor=highlight, borderwidth=0, padding=[14, 9], font=font_bold, anchor="w",
    )
    style.map(
        "NavActive.TButton",
        background=[("pressed", palette.accent_hover), ("active", palette.accent_hover)],
        foreground=[("pressed", hl_fg), ("active", hl_fg)],
    )

    style.configure(
        "Accent.TButton", background=highlight, foreground=hl_fg, bordercolor=highlight,
        darkcolor=highlight, lightcolor=highlight, borderwidth=0, focuscolor=palette.accent_hover,
        padding=[16, 7], font=font_bold,
    )
    style.map(
        "Accent.TButton",
        background=[("pressed", palette.accent_hover), ("active", palette.accent_hover)],
        foreground=[("pressed", hl_fg), ("active", hl_fg)],
    )

    style.configure(
        "TSpinbox", fieldbackground=inp_bg, background=card, foreground=fg, bordercolor=border,
        lightcolor=border, darkcolor=border, arrowcolor=fg, insertcolor=fg, padding=[6, 4],
    )
    style.map("TSpinbox", bordercolor=[("focus", palette.border_focus)], fieldbackground=[("readonly", inp_bg)])

    style.configure("TNotebook", background=bg, bordercolor=border, borderwidth=0, tabmargins=[4, 4, 4, 0])
    style.configure(
        "Hidden.TNotebook",
        background=bg,
        bordercolor=bg,
        lightcolor=bg,
        darkcolor=bg,
        borderwidth=0,
        tabmargins=[0, 0, 0, 0],
    )
    style.layout("Hidden.TNotebook", [("Notebook.client", {"sticky": "nswe"})])
    style.layout("Hidden.TNotebook.Tab", [])
    style.configure("TNotebook.Tab", background=card, foreground=subtext, bordercolor=border, padding=[10, 6], font=font_regular)
    style.map(
        "TNotebook.Tab",
        background=[("selected", bg), ("active", card)],
        foreground=[("selected", palette.accent), ("active", fg)],
        bordercolor=[("selected", border), ("active", border)],
        focuscolor=[("selected", highlight)],
    )

    style.configure(
        "TEntry", fieldbackground=inp_bg, foreground=fg, bordercolor=border,
        lightcolor=border, darkcolor=border, insertcolor=fg, padding=[6, 5],
    )
    style.map("TEntry", bordercolor=[("focus", palette.border_focus)])

    style.configure(
        "TCombobox", fieldbackground=inp_bg, background=card, foreground=fg,
        bordercolor=border, lightcolor=border, darkcolor=border, arrowcolor=fg, padding=[6, 5],
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", inp_bg)],
        foreground=[("readonly", fg)],
        bordercolor=[("focus", palette.border_focus)],
    )

    for cb_name, cb_bg in (("TCheckbutton", bg), ("Card.TCheckbutton", card), ("TRadiobutton", bg), ("Card.TRadiobutton", card)):
        style.configure(
            cb_name, background=cb_bg, foreground=fg, indicatorbackground=inp_bg,
            indicatorcolor=palette.accent, focuscolor=cb_bg, padding=[4, 3],
        )
        style.map(
            cb_name,
            indicatorbackground=[("selected", highlight), ("active", card)],
            indicatorcolor=[("selected", hl_fg)],
            background=[("active", cb_bg)],
        )

    style.configure(
        "Treeview", background=card, foreground=fg, fieldbackground=card,
        bordercolor=border, rowheight=28, font=font_regular,
    )
    style.map("Treeview", background=[("selected", highlight)], foreground=[("selected", hl_fg)])
    style.configure("Treeview.Heading", background=bg, foreground=subtext, bordercolor=border, font=font_bold, padding=[8, 6])
    style.map("Treeview.Heading", background=[("active", card)], foreground=[("active", fg)])

    style.configure("TScrollbar", background=card, bordercolor=bg, troughcolor=bg, arrowcolor=subtext)
    style.map("TScrollbar", background=[("active", border), ("pressed", highlight)])
    style.configure("TSeparator", background=border)
    return style


__all__ = [
    "SPACE_LG", "SPACE_MD", "SPACE_SM", "SPACE_XL", "SPACE_XS", "SPACING",
    "Palette", "PredictionStyleTokens",
    "_CONFIDENCE_LEVELS", "_PERSIAN_FONTS", "_SYSTEM_FONTS",
    "_accessible_highlight_fg", "_contrast_ratio", "_disable_acrylic_blur",
    "_distinct_from_colorkey", "_enable_acrylic_blur", "_hex_to_colorref",
    "_raw_prediction_style", "_relative_luminance", "_resolve_live_tk_parent",
    "_set_dwm_attribute", "_set_window_composition_accent",
    "apply_popup_window_attributes", "apply_theme_to_ttk", "apply_window_decorations",
    "clamp_popup_position", "confidence_bar", "create_managed_toplevel",
    "destroy_managed_toplevel", "get_active_palette", "get_classic_palette",
    "get_dpi_scale", "get_fluent_palette", "get_glass_palette", "get_ios_palette",
    "get_macos_palette", "get_material_palette", "get_minimal_palette",
    "get_modern_palette", "get_neon_palette", "get_prediction_style",
    "get_ui_font", "load_bundled_fonts", "rects_overlap", "resolve_popup_position",
]
