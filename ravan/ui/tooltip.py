"""Lightweight, accessible Tkinter tooltip component (Phase 6)."""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Any

from ravan.ui.theme import get_active_palette, get_ui_font

log = logging.getLogger(__name__)


class ToolTip:
    """Hover tooltip for Tkinter widgets."""

    def __init__(
        self,
        widget: tk.Widget,
        text: str,
        delay_ms: int = 400,
    ) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id: str | None = None
        self._tip_window: tk.Toplevel | None = None

        self.widget.bind("<Enter>", self._on_enter, add="+")
        self.widget.bind("<Leave>", self._on_leave, add="+")
        self.widget.bind("<ButtonPress>", self._on_leave, add="+")
        self.widget.bind("<Destroy>", self._on_leave, add="+")

    def _on_enter(self, _event: Any = None) -> None:
        self._schedule()

    def _on_leave(self, _event: Any = None) -> None:
        self._unschedule()
        self.hide()

    def _schedule(self) -> None:
        self._unschedule()
        try:
            self._after_id = self.widget.after(self.delay_ms, self.show)
        except Exception:  # noqa: BLE001
            pass

    def _unschedule(self) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:  # noqa: BLE001
                pass
            self._after_id = None

    def show(self) -> None:
        if self._tip_window is not None or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

            self._tip_window = tk.Toplevel(self.widget)
            self._tip_window.wm_overrideredirect(True)
            self._tip_window.attributes("-topmost", True)

            palette = get_active_palette()
            self._tip_window.configure(bg=palette.border)

            inner = tk.Frame(self._tip_window, bg=palette.card_bg, padx=8, pady=4)
            inner.pack(fill="both", expand=True, padx=1, pady=1)

            lbl = tk.Label(
                inner,
                text=self.text,
                font=get_ui_font(size=8, bold=False),
                bg=palette.card_bg,
                fg=palette.fg,
                justify="left",
                wraplength=320,
            )
            lbl.pack()

            self._tip_window.geometry(f"+{x}+{y}")
        except Exception as exc:  # noqa: BLE001
            log.debug("ToolTip show failed: %s", exc)

    def hide(self) -> None:
        if self._tip_window is not None:
            try:
                self._tip_window.destroy()
            except Exception:  # noqa: BLE001
                pass
            self._tip_window = None
