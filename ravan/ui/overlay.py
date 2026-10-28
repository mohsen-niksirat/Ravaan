"""No-activate overlay: language chip + prediction popup."""

from __future__ import annotations

import logging
import sys
import tkinter as tk
from collections.abc import Callable
from typing import Any

from ravan.core.config import Theme
from ravan.core.events import Candidate
from ravan.ui.theme import (
    apply_popup_window_attributes,
    confidence_bar,
    get_active_palette,
    get_ui_font,
)

log = logging.getLogger(__name__)

_HINT_TEXT = "↑↓ انتخاب  ·  Enter تأیید  ·  1-5 سریع  ·  Esc بستن"


class OverlayWindow:
    """Always-on-top overlay that never steals focus (best-effort)."""

    def __init__(
        self,
        theme: Theme | None = None,
        theme_mode: str = "auto",
        cfg: Any = None,
        on_position_changed: Callable[[int, int], None] | None = None,
    ) -> None:
        self.cfg = cfg
        self.on_position_changed = on_position_changed
        self.theme_mode = theme_mode
        self.palette = get_active_palette(theme_mode)
        if theme is None:
            theme = (
                Theme.high_contrast()
                if self.palette.name == "high_contrast"
                else (Theme.dark() if self.palette.name == "dark" else Theme.light())
            )
        self.theme = theme

        # Dragging & focus safety state
        self._is_dragging = False
        self._drag_start_screen_x = 0
        self._drag_start_screen_y = 0
        self._win_start_x = 0
        self._win_start_y = 0
        self._last_active_hwnd: int | None = None

        # Persistent custom position
        self.has_custom_pos = bool(
            cfg
            and getattr(cfg, "overlay_custom_pos", False)
            and getattr(cfg, "overlay_pos_x", -1) >= 0
            and getattr(cfg, "overlay_pos_y", -1) >= 0
        )
        self.custom_x = getattr(cfg, "overlay_pos_x", -1) if cfg else -1
        self.custom_y = getattr(cfg, "overlay_pos_y", -1) if cfg else -1
        self.current_x = -1
        self.current_y = -1

        self._root = tk.Tk()
        if sys.platform != "win32":
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
        self._apply_noactivate(show=False)

    def _apply_theme(self) -> None:
        mode = getattr(self, "theme_mode", "auto")
        self.palette = get_active_palette(mode)
        bg = self.palette.bg
        fg = self.palette.fg
        border = self.palette.border

        ui_style = getattr(self.cfg, "prediction_ui_style", "modern") if self.cfg else "modern"
        opacity = (
            float(getattr(self.cfg, "prediction_opacity", self.palette.alpha))
            if self.cfg
            else self.palette.alpha
        )
        f_sz = (
            int(getattr(self.cfg, "prediction_font_size", int(self.theme.font_size)))
            if self.cfg
            else int(self.theme.font_size)
        )

        if ui_style == "glass":
            opacity = min(opacity, 0.86)
        elif ui_style == "classic":
            opacity = 1.0

        self._target_alpha = opacity
        try:
            self._root.attributes("-alpha", opacity)
        except Exception:  # noqa: BLE001
            pass

        bd = 2 if ui_style == "classic" else 1
        relief = "solid" if ui_style == "classic" else "flat"

        if hasattr(self, "_frame"):
            self._frame.config(bg=bg, highlightbackground=border, bd=bd, relief=relief)
            if hasattr(self, "_grip"):
                self._grip.config(bg=bg, fg=self.palette.subtext)
            self._hint.config(bg=bg, fg=self.palette.subtext)
            self._lang_label.config(bg=bg, fg=fg)
        else:
            self._frame = tk.Frame(
                self._root,
                bg=bg,
                bd=bd,
                relief=relief,
                highlightthickness=1,
                highlightbackground=border,
            )
            self._frame.pack(fill="both", expand=True)

            f_grip = get_ui_font(size=max(8, f_sz - 4))
            self._grip = tk.Label(
                self._frame,
                text="⋮⋮ روان",
                bg=bg,
                fg=self.palette.subtext,
                font=f_grip,
                cursor="fleur",
                padx=8,
                pady=2,
                anchor="w",
            )
            self._bind_drag(self._grip)
            self._bind_drag(self._frame)

            f_hint = get_ui_font(size=max(8, f_sz - 3))
            self._hint = tk.Label(
                self._frame,
                text=_HINT_TEXT,
                bg=bg,
                fg=self.palette.subtext,
                font=f_hint,
                justify="left",
                padx=10,
                pady=4 if ui_style == "compact" else 6,
            )
            self._bind_drag(self._hint)

            f_lang = get_ui_font(size=f_sz + 2, bold=True, rtl=True)
            self._lang_label = tk.Label(
                self._frame,
                text="",
                bg=bg,
                fg=fg,
                font=f_lang,
                padx=12,
                pady=8,
            )

    def apply_config(self, cfg: Any) -> None:
        self.cfg = cfg
        if (
            getattr(cfg, "overlay_custom_pos", False)
            and getattr(cfg, "overlay_pos_x", -1) >= 0
            and getattr(cfg, "overlay_pos_y", -1) >= 0
        ):
            self.has_custom_pos = True
            self.custom_x = cfg.overlay_pos_x
            self.custom_y = cfg.overlay_pos_y
        else:
            self.has_custom_pos = False
            self.custom_x = -1
            self.custom_y = -1
        self._apply_theme()

    def reset_position_to_caret(self) -> None:
        self.has_custom_pos = False
        self.custom_x = -1
        self.custom_y = -1

    def _bind_drag(self, widget: tk.Widget, row_index: int = -1) -> None:
        widget.bind("<Button-1>", lambda e, r=row_index: self._on_mouse_down(e, r))
        widget.bind("<B1-Motion>", self._on_mouse_drag)
        widget.bind("<ButtonRelease-1>", lambda e, r=row_index: self._on_mouse_up(e, r))

    def _on_mouse_down(self, event: tk.Event, row_index: int = -1) -> None:
        self._drag_start_screen_x = event.x_root
        self._drag_start_screen_y = event.y_root
        self._win_start_x = self._root.winfo_x()
        self._win_start_y = self._root.winfo_y()
        self._is_dragging = False
        self._clicked_row = row_index
        if sys.platform == "win32":
            try:
                from ravan.platform import winapi as wapi

                self._last_active_hwnd = int(wapi.user32.GetForegroundWindow() or 0)
            except Exception:  # noqa: BLE001
                pass

    def _on_mouse_drag(self, event: tk.Event) -> None:
        dx = event.x_root - self._drag_start_screen_x
        dy = event.y_root - self._drag_start_screen_y
        if abs(dx) > 3 or abs(dy) > 3:
            self._is_dragging = True
            nx = self._win_start_x + dx
            ny = self._win_start_y + dy
            self._place(nx, ny)

    def _on_mouse_up(self, event: tk.Event, row_index: int = -1) -> None:
        if self._is_dragging:
            self._is_dragging = False
            self.has_custom_pos = True
            self.custom_x = self._root.winfo_x()
            self.custom_y = self._root.winfo_y()
            if self.on_position_changed:
                try:
                    self.on_position_changed(self.custom_x, self.custom_y)
                except Exception as exc:  # noqa: BLE001
                    log.warning("Position change callback error: %s", exc)
        else:
            if row_index >= 0 and self.predicting and 0 <= row_index < len(self._candidates):
                cand = self.accept_index(row_index)
                if cand and self._on_accept:
                    self._on_accept(cand)

        # Guard target app focus
        if sys.platform == "win32" and self._last_active_hwnd:
            try:
                from ravan.platform import winapi as wapi

                cur = int(wapi.user32.GetForegroundWindow() or 0)
                root_hwnd = self._get_root_hwnd()
                if root_hwnd and cur == int(root_hwnd):
                    wapi.user32.SetForegroundWindow(self._last_active_hwnd)
            except Exception:  # noqa: BLE001
                pass

    def set_theme_mode(self, mode: str) -> None:
        self.theme_mode = mode
        self.theme = (
            Theme.high_contrast()
            if mode == "high_contrast"
            else (Theme.dark() if mode == "dark" else Theme.light())
        )
        self._apply_theme()

    def _get_root_hwnd(self) -> int | None:
        try:
            from ravan.platform import winapi as wapi

            hwnd = self._root.winfo_id()
            GA_ROOT = 2
            return int(wapi.user32.GetAncestor(hwnd, GA_ROOT) or hwnd)
        except Exception:  # noqa: BLE001
            return None

    def _apply_noactivate(self, show: bool = False) -> None:
        apply_popup_window_attributes(
            self._root, getattr(self, "palette", get_active_palette()), show=show
        )

    def _fade_in(self) -> None:
        target = getattr(self, "_target_alpha", getattr(self.palette, "alpha", 0.95))
        if hasattr(self, "_fade_job") and self._fade_job:
            try:
                self._root.after_cancel(self._fade_job)
            except Exception:
                pass
            self._fade_job = None

        steps = [max(0.3, target * 0.4), max(0.6, target * 0.75), target]

        def _step(idx: int) -> None:
            if not self.visible:
                return
            try:
                self._root.attributes("-alpha", steps[idx])
            except Exception:
                return
            if idx + 1 < len(steps):
                self._fade_job = self._root.after(16, lambda: _step(idx + 1))
            else:
                self._fade_job = None

        _step(0)

    def _show_no_activate(self) -> None:
        was_visible = self.visible
        if sys.platform == "win32":
            try:
                from ravan.platform import winapi as wapi

                root_hwnd = self._get_root_hwnd()
                if root_hwnd:
                    fg_target = int(wapi.user32.GetForegroundWindow() or 0)
                    style = wapi.user32.GetWindowLongW(root_hwnd, -20)
                    if not (style & 0x08000000):
                        wapi.user32.SetWindowLongW(root_hwnd, -20, style | 0x08000088)
                        wapi.user32.SetWindowPos(root_hwnd, 0, 0, 0, 0, 0, 0x0027)

                    wapi.user32.ShowWindow(root_hwnd, wapi.SW_SHOWNOACTIVATE)
                    current_fg = int(wapi.user32.GetForegroundWindow() or 0)
                    if fg_target and current_fg != fg_target:
                        wapi.user32.SetForegroundWindow(fg_target)
            except Exception:  # noqa: BLE001
                self._root.deiconify()
        else:
            self._root.deiconify()
        self._apply_noactivate(show=False)
        if not was_visible:
            self._fade_in()

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
        if hasattr(self, "_fade_job") and self._fade_job:
            try:
                self._root.after_cancel(self._fade_job)
            except Exception:
                pass
            self._fade_job = None
        self._mode = "idle"
        self._candidates = []
        self._clip_items = []
        self._selected = 0
        self._clear_rows()
        self._lang_label.pack_forget()
        self._hint.pack_forget()
        if hasattr(self, "_grip"):
            self._grip.pack_forget()
        hidden_via_win32 = False
        if sys.platform == "win32":
            try:
                from ravan.platform import winapi as wapi

                root_hwnd = self._get_root_hwnd()
                if root_hwnd:
                    wapi.user32.ShowWindow(root_hwnd, 0)
                    hidden_via_win32 = True
            except Exception:  # noqa: BLE001
                pass
        if not hidden_via_win32:
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
        self._show_no_activate()
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

        m_left, m_top, m_right, m_bottom = wapi.get_monitor_work_area(x, y)

        if self.has_custom_pos and self.custom_x >= 0 and self.custom_y >= 0:
            px = self.custom_x
            py = self.custom_y
        else:
            py = y + eff_h + 8 if y + eff_h + popup_h + 8 < m_bottom else max(m_top + 8, y - popup_h - 8)
            px = x - popup_w + 35 if is_rtl else x

        px = max(m_left + 8, min(px, m_right - popup_w - 8))
        py = max(m_top + 8, min(py, m_bottom - popup_h - 8))
        self._place(px, py)
        self._show_no_activate()

    def _row_text(
        self,
        index: int,
        candidate: Candidate,
        selected: bool,
        show_meter: bool | None = None,
    ) -> str:
        prefix = f"{index + 1}  "
        mark = "▶ " if selected else "   "
        tags = {"SENTENCE": "  [ادامه]", "NEXT_WORD": "  [بعدی]", "AUTOCORRECT": "  ≈"}
        tag = tags.get(candidate.kind.name, "")

        if show_meter is None:
            show_meter = bool(self is not None and getattr(self, "_mode", "") == "predict")

        meter = f" {confidence_bar(candidate.score)}" if (show_meter and candidate.score > 0) else ""
        return f"{mark}{prefix}{candidate.text}{tag}{meter}"

    def _render_candidates(self) -> None:
        p = getattr(self, "palette", get_active_palette())
        ui_style = getattr(self.cfg, "prediction_ui_style", "modern") if self.cfg else "modern"
        f_sz = (
            int(getattr(self.cfg, "prediction_font_size", int(self.theme.font_size)))
            if self.cfg
            else int(self.theme.font_size)
        )

        pad_y = 2 if ui_style == "compact" else 4
        pad_x = 8 if ui_style == "compact" else 10

        if ui_style != "compact" and hasattr(self, "_grip"):
            self._grip.pack(fill="x")
        elif hasattr(self, "_grip"):
            self._grip.pack_forget()

        while len(self._rows) < len(self._candidates):
            idx = len(self._rows)
            fnt = get_ui_font(size=f_sz)
            row = tk.Label(
                self._frame,
                text="",
                bg=p.bg,
                fg=p.fg,
                font=fnt,
                anchor="w",
                padx=pad_x,
                pady=pad_y,
            )
            self._bind_drag(row, row_index=idx)
            self._rows.append(row)

        for i, c in enumerate(self._candidates):
            selected = i == self._selected
            rtl = any(ord(ch) > 127 for ch in c.text[:2])
            fnt = get_ui_font(size=f_sz, bold=selected, rtl=rtl)
            if selected:
                bg, fg = p.highlight, p.highlight_fg
            elif getattr(c, "kind", None) and c.kind.name == "SENTENCE":
                bg, fg = p.bg, p.subtext
            else:
                bg, fg = p.bg, p.fg
            self._rows[i].config(
                text=self._row_text(i, c, selected),
                bg=bg,
                fg=fg,
                font=fnt,
                padx=pad_x,
                pady=pad_y,
            )
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
        self.current_x = int(px)
        self.current_y = int(py)

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
        self._selected = (self._selected + delta) % len(self._candidates)
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

    def accept_sentence_continuation(self) -> Candidate | None:
        """Accept first sentence/bigram continuation candidate if available."""
        if not self.predicting:
            return None
        from ravan.core.events import CandidateKind

        for idx, cand in enumerate(self._candidates):
            if cand.kind == CandidateKind.SENTENCE:
                self._selected = idx
                return self.accept_selected()
        return None

    @staticmethod
    def _rgb(rgb: list[int] | tuple[int, int, int]) -> str:
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

