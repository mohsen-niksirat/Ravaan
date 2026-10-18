"""Modern overlay popup displaying Quick Text Statistics (Milestone M15)."""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Any

from ravan.core.normalizer import en_to_fa_digits
from ravan.platform import winapi as wapi
from ravan.ui.theme import apply_popup_window_attributes, get_active_palette, get_ui_font

log = logging.getLogger(__name__)


class StatsPopupWindow:
    """Non-activating, auto-dismissing floating popup for selected text metrics."""

    def __init__(self, parent: tk.Tk | tk.Toplevel | None = None) -> None:
        self._parent = parent
        self._root: tk.Toplevel | None = None
        self._dismiss_job: str | None = None

    def show(self, stats: dict[str, Any], x: int = 100, y: int = 100) -> None:
        self.close()

        palette = get_active_palette()
        parent = self._parent or tk._default_root
        win = tk.Toplevel(parent) if parent is not None else tk.Toplevel()
        self._root = win
        win.withdraw()
        win.title("Text Stats — Ravaan")

        frame = tk.Frame(
            win,
            bg=palette.bg,
            highlightbackground=palette.border,
            highlightthickness=1,
            padx=14,
            pady=12,
        )
        frame.pack(fill="both", expand=True)

        from ravan.core.i18n import is_rtl, t

        rtl = is_rtl()
        align_label = "right" if rtl else "left"
        align_val = "left" if rtl else "right"
        footer_anchor = "w" if rtl else "e"

        # Header
        hdr = tk.Frame(frame, bg=palette.bg)
        hdr.pack(fill="x", pady=(0, 8))
        f_hdr = get_ui_font(size=10, bold=True, rtl=rtl)
        tk.Label(
            hdr,
            text=t("stats.header", "📊 Text Statistics"),
            font=f_hdr,
            bg=palette.bg,
            fg=palette.accent,
        ).pack(side=align_label)

        # Stats Cards
        words = stats.get("word_count", 0)
        chars = stats.get("char_count", 0)
        no_space = stats.get("char_no_spaces", 0)
        sec = stats.get("reading_time_sec", 0)
        time_str = f"~{sec}s" if sec < 60 else f"~{sec // 60}m {sec % 60}s"
        ratio = stats.get("ratio_str", "—")

        words_val = en_to_fa_digits(str(words)) if rtl else str(words)
        chars_val = (
            f"{en_to_fa_digits(str(chars))}  [{t('stats.no_spaces', 'without spaces: {count}', count=en_to_fa_digits(str(no_space)))}]"
            if rtl
            else f"{chars}  [{t('stats.no_spaces', 'without spaces: {count}', count=no_space)}]"
        )
        time_val = en_to_fa_digits(time_str) if rtl else time_str

        rows = [
            (t("stats.words", "Words:"), words_val),
            (t("stats.characters", "Characters:"), chars_val),
            (t("stats.reading_time", "Reading Time:"), time_val),
            (t("stats.language_ratio", "Language Ratio:"), ratio),
        ]

        body = tk.Frame(frame, bg=palette.card_bg, padx=10, pady=8)
        body.pack(fill="x", pady=2)

        f_label = get_ui_font(size=9, bold=False, rtl=rtl)
        f_val = get_ui_font(size=9, bold=True, rtl=rtl)

        for label_text, val_text in rows:
            r_frm = tk.Frame(body, bg=palette.card_bg)
            r_frm.pack(fill="x", pady=2)
            tk.Label(r_frm, text=label_text, font=f_label, bg=palette.card_bg, fg=palette.fg).pack(side=align_label)
            tk.Label(
                r_frm, text=val_text, font=f_val, bg=palette.card_bg, fg=palette.accent
            ).pack(side=align_val)

        f_footer = get_ui_font(size=8, bold=False, rtl=rtl)
        footer = tk.Label(
            frame,
            text=t("stats.footer", "Press Esc or click to close • Ravaan"),
            font=f_footer,
            bg=palette.bg,
            fg=palette.subtext,
        )
        footer.pack(anchor=footer_anchor, pady=(6, 0))

        win.bind("<Button-1>", lambda _: self.close())
        win.bind("<Escape>", lambda _: self.close())
        frame.bind("<Button-1>", lambda _: self.close())

        win.update_idletasks()
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()

        m_left, m_top, m_right, m_bottom = wapi.get_monitor_work_area(x, y)
        px = max(m_left + 12, min(int(x), m_right - w - 12))
        py = max(m_top + 12, min(int(y), m_bottom - h - 12))

        win.geometry(f"+{px}+{py}")
        win.deiconify()
        apply_popup_window_attributes(win, palette)

        self._dismiss_job = win.after(6000, self.close)

    def close(self) -> None:
        if self._root is not None:
            if self._dismiss_job:
                try:
                    self._root.after_cancel(self._dismiss_job)
                except Exception:
                    pass
                self._dismiss_job = None
            try:
                self._root.destroy()
            except tk.TclError:
                pass
            self._root = None
