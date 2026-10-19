"""Transient toast notification widget using active theme palette."""

from __future__ import annotations

import logging
import tkinter as tk

from ravan.ui.theme import (
    apply_popup_window_attributes,
    get_active_palette,
    get_ui_font,
)

log = logging.getLogger(__name__)


class ToastPopup:
    """Transient on-screen toast for quick feedback (e.g. undo, translit toggle)."""

    def __init__(self, parent: tk.Misc | None = None, theme_mode: str = "auto") -> None:
        self.parent = parent
        self.theme_mode = theme_mode
        self._top: tk.Toplevel | None = None
        self._label: tk.Label | None = None
        self._hide_after: str | None = None

    def _ensure_window(self) -> None:
        if self._top is not None and self._top.winfo_exists():
            return
        try:
            p = get_active_palette(self.theme_mode)
            parent_widget = self.parent if isinstance(self.parent, tk.Misc) else None
            top = tk.Toplevel(parent_widget) if parent_widget else tk.Tk()
            top.withdraw()
            top.overrideredirect(True)
            top.attributes("-topmost", True)
            try:
                top.attributes("-alpha", p.alpha)
            except tk.TclError:
                pass
            apply_popup_window_attributes(top, p)

            frame = tk.Frame(top, bg=p.border, padx=1, pady=1)
            frame.pack(fill=tk.BOTH, expand=True)

            inner = tk.Frame(frame, bg=p.card_bg, padx=12, pady=6)
            inner.pack(fill=tk.BOTH, expand=True)

            lbl = tk.Label(
                inner,
                bg=p.card_bg,
                fg=p.fg,
                font=get_ui_font(size=11, bold=True),
            )
            lbl.pack()

            self._top = top
            self._label = lbl
        except (tk.TclError, Exception) as exc:
            log.debug("Toast window creation suppressed: %s", exc)
            self._top = None
            self._label = None

    def show(
        self,
        message: str,
        duration_ms: int = 2200,
        x: int | None = None,
        y: int | None = None,
    ) -> None:
        """Display a transient toast near coordinates or bottom-right."""
        self._ensure_window()
        if not self._top or not self._label:
            return

        if self._hide_after:
            try:
                self._top.after_cancel(self._hide_after)
            except Exception:
                pass
            self._hide_after = None

        p = get_active_palette(self.theme_mode)
        rtl = any(ord(c) > 127 for c in message[:4])
        self._label.config(
            text=message,
            bg=p.card_bg,
            fg=p.fg,
            font=get_ui_font(size=11, bold=True, rtl=rtl),
        )

        self._top.update_idletasks()
        w = self._top.winfo_reqwidth()
        h = self._top.winfo_reqheight()

        if x is not None and y is not None:
            px = max(10, x)
            py = max(10, y - h - 10)
        else:
            sw = self._top.winfo_screenwidth()
            sh = self._top.winfo_screenheight()
            px = sw - w - 24
            py = sh - h - 48

        self._top.geometry(f"{w}x{h}+{px}+{py}")
        self._top.deiconify()
        self._top.lift()

        self._hide_after = self._top.after(duration_ms, self.hide)

    def hide(self) -> None:
        if self._top and self._top.winfo_exists():
            self._top.withdraw()
        self._hide_after = None
