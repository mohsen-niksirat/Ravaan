"""No-activate overlay: language chip + prediction popup."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ravan.core.config import Theme
from ravan.core.events import Candidate
from ravan.ui.theme import (
    apply_popup_window_attributes,
    confidence_bar,
    get_active_palette,
    get_ui_font,
)

_HINT_TEXT = "↑↓ انتخاب  ·  Enter تأیید  ·  1-5 سریع  ·  Esc بستن"


class OverlayWindow:
    """Always-on-top overlay that never steals focus (best-effort)."""

    def __init__(self, theme: Theme | None = None, theme_mode: str = "auto") -> None:
        self.theme_mode = theme_mode
        self.palette = get_active_palette(theme_mode)
        if theme is None:
            if self.palette.name == "high_contrast":
                theme = Theme.high_contrast()
            elif self.palette.name == "dark":
                theme = Theme.dark()
            else:
                theme = Theme.light()
        self.theme = theme
        self._root = tk.Tk()
        self._root.withdraw()
        self._root.title("Ravan")
        self._root.attributes("-topmost", True)
        self._root.overrideredirect(True)
        try:
            self._root.attributes("-alpha", self.palette.alpha)
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
        mode = getattr(self, "theme_mode", "auto")
        self.palette = get_active_palette(mode)
        bg = self.palette.bg
        fg = self.palette.fg
        border = self.palette.border
        try:
            self._root.attributes("-alpha", self.palette.alpha)
        except Exception:
            pass

        if hasattr(self, "_frame"):
            self._frame.config(bg=bg, highlightbackground=border)
            self._hint.config(bg=bg, fg=self.palette.subtext)
            self._lang_label.config(bg=bg, fg=fg)
        else:
            self._frame = tk.Frame(
                self._root, bg=bg, bd=1, highlightthickness=1, highlightbackground=border
            )
            self._frame.pack(fill="both", expand=True)

            f_hint = get_ui_font(size=max(9, int(self.theme.font_size) - 3))
            self._hint = tk.Label(
                self._frame,
                text=_HINT_TEXT,
                bg=bg,
                fg=self.palette.subtext,
                font=f_hint,
                justify="left",
                padx=10,
                pady=6,
            )
            f_lang = get_ui_font(size=int(self.theme.font_size) + 2, bold=True, rtl=True)
            self._lang_label = tk.Label(
                self._frame,
                text="",
                bg=bg,
                fg=fg,
                font=f_lang,
                padx=12,
                pady=8,
            )

    def set_theme_mode(self, mode: str) -> None:
        self.theme_mode = mode
        if mode == "high_contrast":
            self.theme = Theme.high_contrast()
        elif mode == "dark":
            self.theme = Theme.dark()
        elif mode == "light":
            self.theme = Theme.light()
        self._apply_theme()

    def _get_root_hwnd(self) -> int | None:
        try:
            from ravan.platform import winapi as wapi

            hwnd = self._root.winfo_id()
            GA_ROOT = 2
            return int(wapi.user32.GetAncestor(hwnd, GA_ROOT) or hwnd)
        except Exception:
            return None

    def _apply_noactivate(self) -> None:
        apply_popup_window_attributes(self._root, getattr(self, "palette", get_active_palette()))

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

        from ravan.core.predictor import is_arabic_persian

        is_rtl = any(is_arabic_persian(c) for cand in candidates for c in cand.text[:2])
        self._show_candidates_popup(x, y, height, is_rtl)

    def _show_candidates_popup(self, x: int, y: int, height: int, is_rtl: bool) -> None:
        self._root.update_idletasks()
        popup_w = max(self._root.winfo_reqwidth(), 180)
        popup_h = max(self._root.winfo_reqheight(), 28 * len(self._candidates) + 28)
        eff_h = max(height, 22)
        from ravan.platform import winapi as wapi

        _, m_top, _, m_bottom = wapi.get_monitor_work_area(x, y)
        py = y + eff_h + 8 if y + eff_h + popup_h + 8 < m_bottom else max(m_top + 8, y - popup_h - 8)
        px = x - popup_w + 35 if is_rtl else x
        self._place(px, py)
        self._root.deiconify()
        self._apply_noactivate()

    @staticmethod
    def _rgb(vals: list[int] | tuple[int, ...]) -> str:
        return f"#{vals[0]:02x}{vals[1]:02x}{vals[2]:02x}"

    def _row_text(
        self,
        index: int,
        candidate: Candidate,
        selected: bool,
        show_meter: bool | None = None,
    ) -> str:
        prefix = f"{index + 1}  "
        mark = "▶ " if selected else "   "
        tags = {"SENTENCE": "  [جمله]", "NEXT_WORD": "  [بعدی]", "AUTOCORRECT": "  ≈"}
        tag = tags.get(candidate.kind.name, "")

        if show_meter is None:
            show_meter = bool(self is not None and getattr(self, "_mode", "") == "predict")

        meter = f" {confidence_bar(candidate.score)}" if (show_meter and candidate.score > 0) else ""
        return f"{mark}{prefix}{candidate.text}{tag}{meter}"

    def _render_candidates(self) -> None:
        p = getattr(self, "palette", get_active_palette())
        f_sz = int(self.theme.font_size)

        while len(self._rows) < len(self._candidates):
            fnt = get_ui_font(size=f_sz)
            row = tk.Label(self._frame, text="", bg=p.bg, fg=p.fg, font=fnt, anchor="w", padx=10, pady=4)
            self._rows.append(row)

        for i, c in enumerate(self._candidates):
            selected = i == self._selected
            rtl = any(ord(ch) > 127 for ch in c.text[:2])
            fnt = get_ui_font(size=f_sz, bold=selected, rtl=rtl)
            bg = p.highlight if selected else p.bg
            fg = p.highlight_fg if selected else p.fg
            self._rows[i].config(text=self._row_text(i, c, selected), bg=bg, fg=fg, font=fnt)
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

            off_x = getattr(self.theme, "offset_x", 0)
            off_y = getattr(self.theme, "offset_y", 0)
            m_left, m_top, m_right, m_bottom = wapi.get_monitor_work_area(x + off_x, y + off_y)
            px = max(m_left + 8, min(int(x + off_x), m_right - w - 8))
            py = max(m_top + 8, min(int(y + off_y), m_bottom - h - 8))

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
        self._show_candidates_popup(x, y, height, False)

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
            p = getattr(self, "palette", get_active_palette())
            f_sz = int(self.theme.font_size)
            if 0 <= old_idx < len(self._rows):
                cand = self._candidates[old_idx]
                rtl = any(ord(ch) > 127 for ch in cand.text[:2])
                fnt = get_ui_font(size=f_sz, bold=False, rtl=rtl)
                self._rows[old_idx].config(
                    bg=p.bg,
                    fg=p.fg,
                    text=self._row_text(old_idx, cand, False),
                    font=fnt,
                )
            if 0 <= self._selected < len(self._rows):
                cand = self._candidates[self._selected]
                rtl = any(ord(ch) > 127 for ch in cand.text[:2])
                fnt = get_ui_font(size=f_sz, bold=True, rtl=rtl)
                self._rows[self._selected].config(
                    bg=p.highlight,
                    fg=p.highlight_fg,
                    text=self._row_text(self._selected, cand, True),
                    font=fnt,
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
