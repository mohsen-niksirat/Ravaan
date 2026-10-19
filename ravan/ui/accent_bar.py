"""Horizontal floating bar for Quick Accent letter picker."""

from __future__ import annotations

import logging
import tkinter as tk

from ravan.ui.theme import apply_popup_window_attributes, get_active_palette, get_ui_font

log = logging.getLogger(__name__)


class AccentBarWindow:
    """Always-on-top, non-activating horizontal strip displaying letter variants."""

    def __init__(self, parent: tk.Misc | None = None, theme_mode: str = "auto") -> None:
        self.parent = parent
        self.theme_mode = theme_mode
        self._top: tk.Toplevel | None = None
        self._labels: list[tk.Label] = []
        self._variants: list[str] = []
        self._selected: int = 0

    def _ensure_window(self) -> tk.Toplevel:
        if self._top is not None and self._top.winfo_exists():
            return self._top

        p = get_active_palette(self.theme_mode)
        top = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self._top = top
        top.withdraw()
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        try:
            top.attributes("-alpha", p.alpha)
        except tk.TclError:
            pass

        apply_popup_window_attributes(top, p)
        return top

    def show(self, variants: list[str], selected_idx: int, x: int, y: int, height: int = 20) -> None:
        if not variants:
            self.hide()
            return

        self._variants = list(variants)
        self._selected = max(0, min(selected_idx, len(variants) - 1))
        top = self._ensure_window()
        p = get_active_palette(self.theme_mode)

        # Clear existing children
        for widget in top.winfo_children():
            widget.destroy()
        self._labels = []

        outer = tk.Frame(top, bg=p.border, padx=1, pady=1)
        outer.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(outer, bg=p.card_bg, padx=4, pady=3)
        inner.pack(fill=tk.BOTH, expand=True)

        f_font = get_ui_font(size=11, bold=True, rtl=True)
        num_font = get_ui_font(size=8, bold=False)

        for i, ch in enumerate(variants):
            is_sel = i == self._selected
            bg_c = p.highlight if is_sel else p.card_bg
            fg_c = p.highlight_fg if is_sel else p.fg

            cell = tk.Frame(inner, bg=bg_c, padx=6, pady=2)
            cell.pack(side=tk.LEFT, padx=2)

            lbl_num = tk.Label(cell, text=str(i + 1), bg=bg_c, fg=p.subtext if not is_sel else p.highlight_fg, font=num_font)
            lbl_num.pack(side=tk.TOP)

            display_ch = ch if ch != "\u200c" else "نیم‌فاصله"
            lbl_ch = tk.Label(cell, text=display_ch, bg=bg_c, fg=fg_c, font=f_font)
            lbl_ch.pack(side=tk.TOP)

            self._labels.append(lbl_ch)

        top.update_idletasks()
        w = max(top.winfo_reqwidth(), 60)
        h = max(top.winfo_reqheight(), 32)

        # Place just above caret (or below if at top of screen)
        from ravan.platform import winapi as wapi
        m_left, m_top, m_right, m_bottom = wapi.get_monitor_work_area(x, y)
        px = max(m_left + 8, min(x - (w // 2), m_right - w - 8))
        py = y - h - 8 if y - h - 8 >= m_top else y + height + 8

        top.geometry(f"+{px}+{py}")
        top.deiconify()

    def update_selection(self, selected_idx: int) -> None:
        self._selected = selected_idx
        p = get_active_palette(self.theme_mode)
        for i, lbl in enumerate(self._labels):
            cell = lbl.master
            is_sel = i == self._selected
            bg_c = p.highlight if is_sel else p.card_bg
            fg_c = p.highlight_fg if is_sel else p.fg
            if isinstance(cell, tk.Frame):
                cell.configure(bg=bg_c)
            lbl.configure(bg=bg_c, fg=fg_c)

    def hide(self) -> None:
        if self._top is not None and self._top.winfo_exists():
            self._top.withdraw()

    def destroy(self) -> None:
        if self._top is not None and self._top.winfo_exists():
            self._top.destroy()
            self._top = None
