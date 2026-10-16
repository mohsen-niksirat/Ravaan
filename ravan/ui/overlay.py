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
        self.theme = theme or Theme()
        self._root = tk.Tk()
        self._root.withdraw()
        self._root.title("Ravan")
        self._root.attributes("-topmost", True)
        self._root.overrideredirect(True)
        try:
            self._root.attributes("-alpha", 0.94)
        except tk.TclError:
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
        self._frame = tk.Frame(self._root, bg=bg, bd=0, highlightthickness=0)
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
            from ravan.platform import winapi as wapi

            root_hwnd = self._get_root_hwnd()
            if not root_hwnd:
                return
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_TOPMOST = 0x00000008
            style = wapi.user32.GetWindowLongW(root_hwnd, GWL_EXSTYLE)
            wapi.user32.SetWindowLongW(
                root_hwnd,
                GWL_EXSTYLE,
                style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST,
            )
            # Show without activating foreground
            wapi.user32.ShowWindow(root_hwnd, wapi.SW_SHOWNOACTIVATE)
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
        popup_h = 28 * len(candidates) + 28
        py = y - popup_h - 4 if y > popup_h + 8 else y + height + 4
        self._place(x, max(0, py))
        self._root.deiconify()
        self._apply_noactivate()

    def _row_text(self, index: int, candidate: Candidate, selected: bool) -> str:
        prefix = f"{index + 1}  "
        mark = "▶ " if selected else "   "
        text = f"{mark}{prefix}{candidate.text}"
        if candidate.kind.name == "AUTOCORRECT":
            text += "  ≈"
        return text

    def _render_candidates(self) -> None:
        bg = self._rgb(self.theme.background_color)
        fg = self._rgb(self.theme.text_color)
        hi = self._rgb(self.theme.highlight_color)

        while len(self._rows) < len(self._candidates):
            row = tk.Label(
                self._frame,
                text="",
                bg=bg,
                fg=fg,
                font=("Segoe UI", int(self.theme.font_size)),
                anchor="w",
                justify="left",
                padx=10,
                pady=4,
            )
            self._rows.append(row)

        for i, c in enumerate(self._candidates):
            selected = i == self._selected
            text = self._row_text(i, c, selected)
            row = self._rows[i]
            row.config(
                text=text,
                bg=hi if selected else bg,
                fg=fg,
            )
            row.pack(fill="x")

        for j in range(len(self._candidates), len(self._rows)):
            self._rows[j].pack_forget()

        self._hint.pack(fill="x")

    def _place(self, x: int, y: int) -> None:
        self._root.update_idletasks()
        w = self._root.winfo_reqwidth()
        h = self._root.winfo_reqheight()
        try:
            from ravan.platform import winapi as wapi

            vx = int(wapi.user32.GetSystemMetrics(wapi.SM_XVIRTUALSCREEN))
            vy = int(wapi.user32.GetSystemMetrics(wapi.SM_YVIRTUALSCREEN))
            vw = int(wapi.user32.GetSystemMetrics(wapi.SM_CXVIRTUALSCREEN))
            vh = int(wapi.user32.GetSystemMetrics(wapi.SM_CYVIRTUALSCREEN))
            if vw > 0 and vh > 0:
                px = max(vx, min(int(x), vx + vw - w - 8))
                py = max(vy, min(int(y), vy + vh - h - 8))
            else:
                sw = self._root.winfo_screenwidth()
                px = max(0, min(int(x), sw - w - 8))
                py = max(0, int(y))

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
        popup_h = 28 * len(cands) + 28
        py = y - popup_h - 4 if y > popup_h + 8 else y + height + 4
        self._place(x, max(0, py))
        self._root.deiconify()
        self._apply_noactivate()

    def accept_clipboard_selected(self) -> str | None:
        if not self.clipboard_open:
            return None
        item = self._clip_items[self._selected]
        self.hide()
        return item

    def accept_clipboard_index(self, index: int) -> str | None:
        if not self.clipboard_open or index < 0 or index >= len(self._clip_items):
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
            if 0 <= old_idx < len(self._rows):
                self._rows[old_idx].config(
                    bg=bg,
                    text=self._row_text(old_idx, self._candidates[old_idx], False),
                )
            if 0 <= self._selected < len(self._rows):
                self._rows[self._selected].config(
                    bg=hi,
                    text=self._row_text(self._selected, self._candidates[self._selected], True),
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
        if not self.predicting or index < 0 or index >= len(self._candidates):
            return None
        self._selected = index
        return self.accept_selected()
