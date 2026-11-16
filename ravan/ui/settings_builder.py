"""Shared Settings UI section helpers and facade re-exports."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ravan.core.i18n import is_rtl
from ravan.ui.settings_ai_voice import build_ai_voice_section
from ravan.ui.settings_general import (
    _bind_live_capture,
    _get_win_palette,
    build_general_section,
    build_hotkeys_section,
)
from ravan.ui.settings_prediction import (
    _style_text_widget,
    build_prediction_section,
)
from ravan.ui.settings_tabs_misc import (
    build_about_section,
    build_exclusions_section,
    build_snippets_section,
    build_sync_section,
)
from ravan.ui.theme import Palette, get_active_palette
from ravan.ui.widgets import FluentCard, FluentSectionBanner


class _ScrollableTab:
    """Scrollable container for Notebook tabs with responsive layout and mousewheel handling."""

    def __init__(self, notebook: ttk.Notebook, palette: Palette, rtl: bool = False, padding: int = 8) -> None:
        self.outer = ttk.Frame(notebook)
        self.canvas = tk.Canvas(self.outer, bg=palette.bg_base, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self.outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="left" if rtl else "right", fill="y")
        self.canvas.pack(side="right" if rtl else "left", fill="both", expand=True)

        self.inner = ttk.Frame(self.canvas, padding=padding)
        self.win_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.win_id, width=max(100, e.width)))
        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        def _on_wheel(e: tk.Event) -> None:
            if not self.canvas.winfo_exists():
                return
            if getattr(e, "num", None) in (4, 5):
                self.canvas.yview_scroll(-2 if e.num == 4 else 2, "units")
            elif getattr(e, "delta", 0):
                self.canvas.yview_scroll(int(-1 * (e.delta / 120) * 2), "units")

        self._on_wheel = _on_wheel
        for target in (self.canvas, self.inner):
            for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                target.bind(seq, _on_wheel)

    def bind_recursive_scroll(self, widget: tk.Widget) -> None:
        try:
            for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                widget.bind(seq, self._on_wheel, add="+")
        except Exception:
            pass
        for child in widget.winfo_children():
            self.bind_recursive_scroll(child)


def _make_section_banner(
    parent: ttk.Frame | tk.Misc,
    icon: str,
    title: str,
    subtitle: str,
    palette: Palette,
    rtl: bool,
) -> tk.Frame:
    """Create a prominent Fluent 2 section title banner at the top of a tab page."""
    return FluentSectionBanner(
        parent=parent,
        icon=icon,
        title=title,
        subtitle=subtitle,
        palette=palette,
        rtl=rtl,
    )


def _make_card(
    parent: ttk.Frame | tk.Misc,
    title: str,
    padding: int = 12,
    palette: Palette | None = None,
    rtl: bool | None = None,
    icon: str | None = None,
) -> FluentCard:
    """Create a Fluent 2 grouped settings card with vector header icon and 1px hairline border."""
    pal = palette or get_active_palette("auto")
    is_rtl_mode = is_rtl() if rtl is None else rtl
    return FluentCard(
        parent=parent,
        title=title,
        padding=padding,
        palette=pal,
        rtl=is_rtl_mode,
        icon=icon,
    )


__all__ = [
    "_bind_live_capture",
    "_get_win_palette",
    "_make_card",
    "_make_section_banner",
    "_style_text_widget",
    "build_about_section",
    "build_ai_voice_section",
    "build_exclusions_section",
    "build_general_section",
    "build_hotkeys_section",
    "build_prediction_section",
    "build_snippets_section",
    "build_sync_section",
]
