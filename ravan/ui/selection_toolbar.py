"""Floating non-activating Selection Mini-Toolbar shown near mouse-selected text."""

from __future__ import annotations

import logging
import sys
import tkinter as tk
from collections.abc import Callable

from ravan.core.i18n import is_rtl, t
from ravan.ui.theme import (
    apply_popup_window_attributes,
    get_active_palette,
    get_ui_font,
    resolve_popup_position,
)

log = logging.getLogger(__name__)


class SelectionToolbarWindow:
    """Compact non-activating pill toolbar offering quick actions on selected text."""

    def __init__(
        self,
        parent: tk.Misc | None = None,
        on_action: Callable[[str], None] | None = None,
        theme_mode: str = "auto",
    ) -> None:
        self.parent = parent
        self.on_action = on_action
        self.theme_mode = theme_mode
        self._top: tk.Toplevel | None = None
        self._outer: tk.Frame | None = None
        self._inner: tk.Frame | None = None
        self._buttons: dict[str, tk.Label] = {}
        self._hide_after: str | None = None
        self._visible: bool = False
        self._root_hwnd: int | None = None
        self._last_bounds: tuple[int, int, int, int] | None = None

    @property
    def visible(self) -> bool:
        return self._visible and self._top is not None

    @property
    def hwnd(self) -> int | None:
        return self._root_hwnd

    def bounds(self) -> tuple[int, int, int, int] | None:
        return self._last_bounds if self._visible else None

    def contains_screen_point(self, px: int, py: int) -> bool:
        """Return True when (px, py) falls inside the visible toolbar bounds."""
        if not self._visible or self._top is None:
            return False
        if self._last_bounds is not None:
            x1, y1, x2, y2 = self._last_bounds
            if x1 <= px <= x2 and y1 <= py <= y2:
                return True
        try:
            wx = self._top.winfo_rootx()
            wy = self._top.winfo_rooty()
            ww = self._top.winfo_width()
            wh = self._top.winfo_height()
            return wx <= px <= (wx + ww) and wy <= py <= (wy + wh)
        except Exception:
            return False

    def _ensure_window(self) -> None:
        if self._top is not None:
            try:
                if self._top.winfo_exists():
                    return
            except tk.TclError:
                self._top = None
        try:
            p = get_active_palette(self.theme_mode)
            parent_widget = self.parent if isinstance(self.parent, tk.Misc) else None
            top = tk.Toplevel(parent_widget) if parent_widget else tk.Tk()
            top.withdraw()
            apply_popup_window_attributes(top, p, border_color=p.border, corner_radius=8.0)

            outer = tk.Frame(top, bg=p.border, padx=1, pady=1)
            outer.pack(fill=tk.BOTH, expand=True)

            inner = tk.Frame(outer, bg=p.card_bg, padx=5, pady=4)
            inner.pack(fill=tk.BOTH, expand=True)

            self._buttons = {}
            for action_id in ("convert", "normalize", "digits", "ai"):
                btn = tk.Label(
                    inner,
                    bg=p.button_bg,
                    fg=p.fg,
                    padx=8,
                    pady=3,
                    cursor="hand2",
                    font=get_ui_font(size=9, bold=True),
                )
                btn.bind("<Button-1>", lambda _e, aid=action_id: self._trigger(aid))
                btn.bind("<Enter>", lambda _e, b=btn: b.config(bg=get_active_palette(self.theme_mode).highlight, fg=get_active_palette(self.theme_mode).highlight_fg))
                btn.bind("<Leave>", lambda _e, b=btn: b.config(bg=get_active_palette(self.theme_mode).button_bg, fg=get_active_palette(self.theme_mode).fg))
                self._buttons[action_id] = btn

            self._top = top
            self._outer = outer
            self._inner = inner
            if sys.platform == "win32":
                try:
                    from ravan.platform import winapi as wapi

                    wid = int(top.winfo_id())
                    self._root_hwnd = int(wapi.user32.GetAncestor(wid, 2) or wid)
                except Exception:
                    self._root_hwnd = None
        except Exception as exc:  # noqa: BLE001
            log.debug("SelectionToolbarWindow creation suppressed: %s", exc)
            self._top = None
            self._buttons = {}

    def _trigger(self, action_id: str) -> str:
        self.hide()
        if callable(self.on_action):
            self.on_action(action_id)
        return "break"

    def show(
        self,
        *,
        x: int,
        y: int,
        width: int = 0,
        height: int = 0,
        show_ai: bool = False,
        avoid_rects: list[tuple[int, int, int, int]] | tuple[tuple[int, int, int, int], ...] = (),
        duration_ms: int = 5500,
        theme_mode: str | None = None,
    ) -> None:
        """Show floating mini-toolbar cleanly above/near the selected text range."""
        if theme_mode:
            self.theme_mode = theme_mode
        self._ensure_window()
        if not self._top or not self._outer or not self._inner or not self._buttons:
            return

        if self._hide_after:
            try:
                self._top.after_cancel(self._hide_after)
            except Exception:
                pass
            self._hide_after = None

        p = get_active_palette(self.theme_mode)
        rtl = is_rtl()

        labels = {
            "convert": t("sel_tb.convert", "🔄 تبدیل" if rtl else "🔄 Layout"),
            "normalize": t("sel_tb.normalize", "✨ نگارش" if rtl else "✨ Polish"),
            "digits": t("sel_tb.digits", "۱۲/12"),
            "ai": t("sel_tb.ai", "🤖 AI"),
        }

        self._outer.config(bg=p.border)
        self._inner.config(bg=p.card_bg)

        order = ("convert", "normalize", "digits", "ai") if not rtl else ("ai", "digits", "normalize", "convert")
        for btn in self._buttons.values():
            btn.pack_forget()

        for action_id in order:
            if action_id == "ai" and not show_ai:
                continue
            btn = self._buttons[action_id]
            txt = labels[action_id]
            btn.config(
                text=txt,
                bg=p.button_bg,
                fg=p.fg,
                font=get_ui_font(size=9, bold=True, rtl=any(ord(c) > 127 for c in txt)),
            )
            btn.pack(side=tk.LEFT, padx=2)

        self._top.update_idletasks()
        w = max(140, int(self._top.winfo_reqwidth()))
        h = max(30, int(self._top.winfo_reqheight()))

        center_x = x + max(0, width) // 2
        px = center_x - (w // 2)
        py = y - h - 10
        if py < 12:
            py = y + max(20, height) + 10

        px, py = resolve_popup_position(self._top, px, py, w, h, avoid_rects=avoid_rects)
        self._top.geometry(f"{w}x{h}+{px}+{py}")
        self._top.deiconify()
        apply_popup_window_attributes(
            self._top,
            p,
            show=True,
            border_color=p.border,
            corner_radius=8.0,
        )
        self._last_bounds = (px, py, px + w, py + h)
        self._visible = True

        if duration_ms > 0:
            self._hide_after = self._top.after(duration_ms, self.hide)

    def hide(self) -> None:
        if self._hide_after and self._top:
            try:
                self._top.after_cancel(self._hide_after)
            except Exception:
                pass
            self._hide_after = None
        if self._top:
            try:
                self._top.withdraw()
            except Exception:
                pass
        self._visible = False
        self._last_bounds = None

    def destroy(self) -> None:
        self.hide()
        if self._top:
            try:
                self._top.destroy()
            except Exception:
                pass
            self._top = None
            self._root_hwnd = None
