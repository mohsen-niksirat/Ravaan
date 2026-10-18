"""No-activate overlay: language chip + prediction popup."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ravan.core.config import Theme
from ravan.core.events import Candidate

_HINT_TEXT = "↑↓ انتخاب  ·  Enter تأیید  ·  1-5 سریع  ·  Esc بستن"


class OverlayWindow:
    """Always-on-top overlay that never steals focus (best-effort)."""

    def __init__(self, theme: Theme | None = None) -> None:
        if theme is None:
            try:
                from ravan.platform.winapi import is_windows_dark_mode

                theme = Theme.dark() if is_windows_dark_mode() else Theme.light()
            except Exception:
                theme = Theme()
        self.theme = theme
        self._root = tk.Tk()
        self._root.withdraw()
        self._root.title("Ravan")
        self._root.attributes("-topmost", True)
        self._root.overrideredirect(True)
        try:
            self._root.attributes("-alpha", 0.94)
        except tk.TclError:
            pass
        try:
            from ravan.platform.winapi import get_system_dpi

            self._root.tk.call("tk", "scaling", get_system_dpi() / 72.0)
        except Exception:
            pass

        self._apply_theme()

        self._rows: list[tk.Label] = []

        self._candidates: list[Candidate] = []
        self._clip_items: list[str] = []
        self._selected = 0
        self._mode = "idle"  # idle | lang | predict | clipboard
        self._on_accept: Callable[[Candidate], None] | None = None
        self._fade_after: str | None = None

        self._root.update_idletasks()
        self._apply_noactivate()

    def _apply_theme(self) -> None:
        bg = self._rgb(self.theme.background_color)
        fg = self._rgb(self.theme.text_color)
        border = "#3c4043" if sum(self.theme.background_color[:3]) < 380 else "#dadce0"
        self._frame = tk.Frame(
            self._root, bg=bg, bd=1, highlightthickness=1, highlightbackground=border
        )
        self._frame.pack(fill="both", expand=True)

        self._hint = tk.Label(
            self._frame,
            text=_HINT_TEXT,
            bg=bg,
            fg="#9aa0a6",
            font=("Segoe UI", max(9, int(self.theme.font_size) - 3)),
            justify="left",
            padx=10,
            pady=6,
        )
        self._lang_label = tk.Label(
            self._frame,
            text="",
            bg=bg,
            fg=fg,
            font=("Segoe UI Semibold", int(self.theme.font_size) + 2),
            padx=12,
            pady=8,
        )

    @staticmethod
    def _rgb(rgba: list[int]) -> str:
        return f"#{rgba[0]:02x}{rgba[1]:02x}{rgba[2]:02x}"

    def _get_root_hwnd(self) -> int | None:
        try:
            from ravan.platform import winapi as wapi

            hwnd = self._root.winfo_id()
            GA_ROOT = 2
            return int(wapi.user32.GetAncestor(hwnd, GA_ROOT) or hwnd)
        except Exception:
            return None

    def _apply_noactivate(self) -> None:
        try:
            import ctypes

            from ravan.platform import winapi as wapi

            root_hwnd = self._get_root_hwnd()
            if not root_hwnd:
                return
            style = wapi.user32.GetWindowLongW(root_hwnd, -20)
            wapi.user32.SetWindowLongW(root_hwnd, -20, style | 0x08000088)
            wapi.user32.ShowWindow(root_hwnd, wapi.SW_SHOWNOACTIVATE)
            wcp = ctypes.c_int(2)  # Native DWM rounded corners
            ctypes.WinDLL("dwmapi", use_last_error=True).DwmSetWindowAttribute(
                wapi.wintypes.HWND(root_hwnd), 33, ctypes.byref(wcp), ctypes.sizeof(wcp)
            )
        except Exception:  # noqa: BLE001
            pass

    def tick(self) -> None:
        try:
            self._root.update_idletasks()
            self._root.update()
        except (tk.TclError, RuntimeError):
            pass

    def destroy(self) -> None:
        try:
            self._root.destroy()
        except tk.TclError:
            pass

    def hide(self) -> None:
        self._mode = "idle"
        self._candidates = []
        self._clip_items = []
        self._selected = 0
        self._clear_rows()
        self._lang_label.pack_forget()
        self._hint.pack_forget()
        self._root.withdraw()
        if self._fade_after is not None:
            try:
                self._root.after_cancel(self._fade_after)
            except Exception:  # noqa: BLE001
                pass
            self._fade_after = None
        try:
            from ravan.platform.hook import set_popup_visible

            set_popup_visible(False)
        except Exception:
            pass

    def _clear_rows(self) -> None:
        for row in self._rows:
            row.pack_forget()

    def show_language(self, label: str, x: int, y: int, height: int = 16) -> None:
        self.hide()
        self._mode = "lang"
        self._lang_label.config(text=label)
        self._lang_label.pack()
        self._place(x, y + height + 4)
        self._root.deiconify()
        self._apply_noactivate()
        self._fade_after = self._root.after(1200, self.hide)

    def show_predictions(
        self,
        candidates: list[Candidate],
        x: int,
        y: int,
        height: int = 16,
        on_accept: Callable[[Candidate], None] | None = None,
    ) -> None:
        if not candidates:
            self.hide()
            return
        if self._fade_after is not None:
            try:
                self._root.after_cancel(self._fade_after)
            except Exception:  # noqa: BLE001
                pass
            self._fade_after = None

        keep_selection = (
            self._mode == "predict"
            and self._candidates
            and [c.text for c in self._candidates] == [c.text for c in candidates]
        )
        prev_selected = self._selected if keep_selection else 0

        self._mode = "predict"
        self._candidates = list(candidates)
        self._selected = min(prev_selected, len(self._candidates) - 1)
        self._on_accept = on_accept
        self._lang_label.pack_forget()
        self._render_candidates()

        self._root.update_idletasks()
        popup_w = max(self._root.winfo_reqwidth(), 180)
        popup_h = max(self._root.winfo_reqheight(), 28 * len(candidates) + 28)
        eff_h = max(height, 22)

        from ravan.platform import winapi as wapi

        m_left, m_top, m_right, m_bottom = wapi.get_monitor_work_area(x, y)
        if y + eff_h + popup_h + 8 < m_bottom:
            py = y + eff_h + 8
        else:
            py = max(m_top + 8, y - popup_h - 8)

        from ravan.core.predictor import is_arabic_persian

        is_rtl = any(
            is_arabic_persian(c)
            for cand in candidates
            for c in cand.text[:2]
        )
        px = x - popup_w + 35 if is_rtl else x

        self._place(px, py)
        self._root.deiconify()
        self._apply_noactivate()

    def _row_text(self, index: int, candidate: Candidate, selected: bool) -> str:
        prefix = f"{index + 1}  "
        mark = "▶ " if selected else "   "
        tag = ""
        if candidate.kind.name == "SENTENCE":
            tag = "  [جمله]"
        elif candidate.kind.name == "NEXT_WORD":
            tag = "  [بعدی]"
        elif candidate.kind.name == "AUTOCORRECT":
            tag = "  ≈"
        return f"{mark}{prefix}{candidate.text}{tag}"

    def _render_candidates(self) -> None:
        bg = self._rgb(self.theme.background_color)
        fg = self._rgb(self.theme.text_color)
        hi = self._rgb(self.theme.highlight_color)

        f_sz = int(self.theme.font_size)
        while len(self._rows) < len(self._candidates):
            row = tk.Label(self._frame, text="", bg=bg, fg=fg, font=("Segoe UI", f_sz), anchor="w", padx=10, pady=4)
            self._rows.append(row)

        for i, c in enumerate(self._candidates):
            selected = i == self._selected
            fnt = ("Segoe UI Semibold" if selected else "Segoe UI", f_sz)
            self._rows[i].config(text=self._row_text(i, c, selected), bg=hi if selected else bg, fg=fg, font=fnt)
            self._rows[i].pack(fill="x")

        for j in range(len(self._candidates), len(self._rows)):
            self._rows[j].pack_forget()

        self._hint.pack(fill="x")

    def _place(self, x: int, y: int) -> None:
        self._root.update_idletasks()
        w = self._root.winfo_reqwidth()
        h = self._root.winfo_reqheight()
        try:
            from ravan.platform import winapi as wapi

            m_left, m_top, m_right, m_bottom = wapi.get_monitor_work_area(x, y)
            px = max(m_left + 8, min(int(x), m_right - w - 8))
            py = max(m_top + 8, min(int(y), m_bottom - h - 8))

            root_hwnd = self._get_root_hwnd()
            if root_hwnd:
                wapi.user32.SetWindowPos(
                    root_hwnd,
                    wapi.HWND_TOPMOST,
                    int(px),
                    int(py),
                    0,
                    0,
                    wapi.SWP_NOSIZE | wapi.SWP_NOACTIVATE | wapi.SWP_SHOWWINDOW,
                )
        except Exception:
            sw = self._root.winfo_screenwidth()
            px = max(0, min(int(x), sw - w - 8))
            py = max(0, int(y))
        self._root.geometry(f"+{px}+{py}")

    @property
    def visible(self) -> bool:
        return self._mode != "idle"

    @property
    def predicting(self) -> bool:
        return self._mode == "predict" and bool(self._candidates)

    @property
    def clipboard_open(self) -> bool:
        return self._mode == "clipboard" and bool(self._clip_items)

    @property
    def active_popup(self) -> bool:
        return self.predicting or self.clipboard_open

    def show_clipboard(self, items: list[str], x: int, y: int, height: int = 16) -> None:
        if not items:
            self.hide()
            return
        from ravan.core.events import CandidateKind

        self._mode = "clipboard"
        self._clip_items = list(items[:9])
        cands: list[Candidate] = []
        for it in self._clip_items:
            first_line = it.splitlines()[0] if it.splitlines() else it
            preview = first_line[:36] + ("…" if len(it) > 36 or "\n" in it else "")
            cands.append(Candidate(text=preview, score=1.0, kind=CandidateKind.COMPLETION))
        self._candidates = cands
        self._selected = 0
        self._lang_label.pack_forget()
        self._render_candidates()
        self._root.update_idletasks()
        popup_h = max(self._root.winfo_reqheight(), 28 * len(cands) + 28)
        eff_h = max(height, 22)

        from ravan.platform import winapi as wapi

        m_left, m_top, m_right, m_bottom = wapi.get_monitor_work_area(x, y)
        if y + eff_h + popup_h + 8 < m_bottom:
            py = y + eff_h + 8
        else:
            py = max(m_top + 8, y - popup_h - 8)

        self._place(x, py)
        self._root.deiconify()
        self._apply_noactivate()

    def accept_clipboard_selected(self) -> str | None:
        if not self.clipboard_open:
            return None
        item = self._clip_items[self._selected]
        self.hide()
        return item

    def accept_clipboard_index(self, index: int) -> str | None:
        if not self.clipboard_open or not (0 <= index < len(self._clip_items)):
            return None
        self._selected = index
        return self.accept_clipboard_selected()

    def move_selection(self, delta: int) -> None:
        if not self.active_popup:
            return
        old_idx = self._selected
        self._selected = (self._selected + delta) % len(self._candidates)
        if len(self._rows) == len(self._candidates):
            bg = self._rgb(self.theme.background_color)
            hi = self._rgb(self.theme.highlight_color)
            f_sz = int(self.theme.font_size)
            if 0 <= old_idx < len(self._rows):
                self._rows[old_idx].config(
                    bg=bg, text=self._row_text(old_idx, self._candidates[old_idx], False), font=("Segoe UI", f_sz)
                )
            if 0 <= self._selected < len(self._rows):
                self._rows[self._selected].config(
                    bg=hi, text=self._row_text(self._selected, self._candidates[self._selected], True), font=("Segoe UI Semibold", f_sz)
                )
        else:
            self._render_candidates()

    def accept_selected(self) -> Candidate | None:
        if not self.predicting:
            return None
        cand = self._candidates[self._selected]
        self.hide()
        return cand

    def accept_index(self, index: int) -> Candidate | None:
        if not self.predicting or not (0 <= index < len(self._candidates)):
            return None
        self._selected = index
        return self.accept_selected()
