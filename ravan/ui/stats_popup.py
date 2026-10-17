"""Modern overlay popup displaying Quick Text Statistics (Milestone M15)."""

from __future__ import annotations

import ctypes
import logging
import tkinter as tk
from typing import Any

from ravan.core.normalizer import en_to_fa_digits
from ravan.platform import winapi as wapi

log = logging.getLogger(__name__)


class StatsPopupWindow:
    """Non-activating, auto-dismissing floating popup for selected text metrics."""

    def __init__(self, parent: tk.Tk | tk.Toplevel | None = None) -> None:
        self._parent = parent
        self._root: tk.Toplevel | None = None
        self._dismiss_job: str | None = None

    def show(self, stats: dict[str, Any], x: int = 100, y: int = 100) -> None:
        self.close()

        is_dark = True
        try:
            is_dark = wapi.is_windows_dark_mode()
        except Exception:
            pass

        bg = "#202124" if is_dark else "#ffffff"
        fg = "#e8eaed" if is_dark else "#202124"
        card_bg = "#2d2f31" if is_dark else "#f1f3f4"
        accent = "#8ab4f8" if is_dark else "#1a73e8"
        border = "#3c4043" if is_dark else "#dadce0"

        parent = self._parent or tk._default_root
        win = tk.Toplevel(parent) if parent is not None else tk.Toplevel()
        self._root = win
        win.withdraw()
        win.title("Text Stats — Ravaan")
        win.attributes("-topmost", True)
        win.overrideredirect(True)
        try:
            win.attributes("-alpha", 0.96)
        except tk.TclError:
            pass

        frame = tk.Frame(win, bg=bg, highlightbackground=border, highlightthickness=1, padx=14, pady=12)
        frame.pack(fill="both", expand=True)

        # Header
        hdr = tk.Frame(frame, bg=bg)
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(
            hdr,
            text="📊 Text Statistics  |  آمار متن",
            font=("Segoe UI", 10, "bold"),
            bg=bg,
            fg=accent,
        ).pack(side="left")

        # Stats Cards
        words = stats.get("word_count", 0)
        chars = stats.get("char_count", 0)
        no_space = stats.get("char_no_spaces", 0)
        sec = stats.get("reading_time_sec", 0)
        time_str = f"~{sec}s" if sec < 60 else f"~{sec // 60}m {sec % 60}s"
        ratio = stats.get("ratio_str", "—")

        rows = [
            ("Words / واژه‌ها:", f"{words}  ({en_to_fa_digits(str(words))})"),
            ("Characters / نویسه‌ها:", f"{chars}  [بدون فاصله: {no_space}]"),
            ("Reading Time / زمان مطالعه:", f"{time_str}  ({en_to_fa_digits(time_str)})"),
            ("Language Ratio / نسبت زبان:", ratio),
        ]

        body = tk.Frame(frame, bg=card_bg, padx=10, pady=8)
        body.pack(fill="x", pady=2)

        for label_text, val_text in rows:
            r_frm = tk.Frame(body, bg=card_bg)

            r_frm.pack(fill="x", pady=2)
            tk.Label(r_frm, text=label_text, font=("Segoe UI", 9), bg=card_bg, fg=fg).pack(side="left")
            tk.Label(
                r_frm, text=val_text, font=("Segoe UI Semibold", 9), bg=card_bg, fg=accent
            ).pack(side="right")

        footer = tk.Label(
            frame,
            text="Press Esc or click to close • روان",
            font=("Segoe UI", 8),
            bg=bg,
            fg="#70757a" if is_dark else "#80868b",
        )
        footer.pack(anchor="e", pady=(6, 0))

        win.bind("<Button-1>", lambda _: self.close())
        win.bind("<Escape>", lambda _: self.close())
        frame.bind("<Button-1>", lambda _: self.close())

        win.update_idletasks()
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()

        px = max(20, min(int(x), sw - w - 20))
        py = max(20, min(int(y), sh - h - 20))
        win.geometry(f"+{px}+{py}")
        win.deiconify()

        try:
            hwnd = int(win.frame(), 16)
            if hwnd:
                wapi.user32.SetWindowPos(
                    hwnd,
                    wapi.HWND_TOPMOST,
                    px,
                    py,
                    w,
                    h,
                    wapi.SWP_NOACTIVATE | wapi.SWP_SHOWWINDOW,
                )
                # DWM rounded corners
                val = ctypes.c_int(2)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(val), ctypes.sizeof(val))
        except Exception:
            pass

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
