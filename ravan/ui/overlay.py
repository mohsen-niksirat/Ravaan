"""No-activate overlay: language chip + prediction popup."""

from __future__ import annotations

import logging
import sys
import time
import tkinter as tk
from collections.abc import Callable
from typing import Any

from ravan.core.config import Theme
from ravan.core.events import Candidate
from ravan.ui.theme import (
    apply_popup_window_attributes,
    confidence_bar,
    get_active_palette,
    get_prediction_style,
    get_ui_font,
)

log = logging.getLogger(__name__)

_HINT_TEXT = "↑↓ انتخاب  ·  Enter تأیید  ·  1-5 سریع  ·  Esc بستن"


class CandidateRow(tk.Frame):
    """Structured candidate row with dedicated accent bar, badge chip, text, and metadata."""

    def __init__(self, master, row_index: int = 0, **kwargs):
        self.row_index = row_index
        super().__init__(master, **kwargs)
        self._current_bg = self.cget("bg")
        self._formatted_text = ""

        # 1. Accent bar (leading edge)
        self._accent_bar = tk.Frame(self, width=0, bg=self._current_bg)

        # 2. Number badge
        self._badge = tk.Label(self, bg=self._current_bg, bd=0, padx=0, pady=0)

        # 3. Candidate text
        self._text = tk.Label(self, bg=self._current_bg, bd=0, padx=0, pady=0)

        # 4. Meta tag (e.g. [ادامه])
        self._tag = tk.Label(self, bg=self._current_bg, bd=0, padx=0, pady=0)

        # 5. Confidence meter (e.g. █)
        self._meter = tk.Label(self, bg=self._current_bg, bd=0, padx=0, pady=0)

    def set_candidate(
        self,
        candidate: Candidate,
        index: int,
        selected: bool,
        tokens,
        f_sz: int,
        is_horizontal: bool = False,
    ) -> None:
        p = tokens.palette
        is_rtl = any(ord(ch) > 127 for ch in candidate.text[:2])

        if selected:
            if tokens.selected_row_style == "bold_only":
                row_bg = getattr(self.master, "_row_bg", p.bg)
                row_fg = p.accent or p.highlight_fg
            elif tokens.name == "neon":
                row_bg = p.highlight
                row_fg = "#00FF66"
            elif tokens.name == "classic":
                row_bg = "#0A246A"
                row_fg = "#FFFFFF"
            elif tokens.name == "fluent":
                row_bg = "#2D323A"
                row_fg = "#FFFFFF"
            elif tokens.name == "modern":
                row_bg = "#8A2BE2"
                row_fg = "#FFFFFF"
            elif tokens.name == "glass":
                row_bg = "#3B6E9C"
                row_fg = "#FFFFFF"
            elif tokens.name == "material":
                row_bg = "#4A4458"
                row_fg = "#FFFFFF"
            else:
                row_bg = p.highlight
                row_fg = p.highlight_fg
        elif getattr(candidate, "kind", None) and candidate.kind.name == "SENTENCE":
            row_bg = getattr(self.master, "_row_bg", p.bg)
            row_fg = p.subtext
        else:
            row_bg = getattr(self.master, "_row_bg", p.bg)
            if tokens.name == "neon":
                row_fg = "#00FF66"
            elif tokens.name == "classic":
                row_fg = "#000000"
            elif tokens.name == "fluent":
                row_fg = "#E0E0E0"
            elif tokens.name == "modern":
                row_fg = "#F3E8FF"
            else:
                row_fg = p.fg

        self._current_bg = row_bg
        super().config(bg=row_bg)

        # 1. Accent bar (leading edge)
        has_accent_bar = (
            selected
            and bool(tokens.accent_bar_color)
            and tokens.selected_row_style in ("leading_bar", "neon")
        )
        bar_color = tokens.accent_bar_color if has_accent_bar else row_bg
        self._accent_bar.config(bg=bar_color, width=3 if has_accent_bar else 0)

        # 2. Badge setup
        badge_style = tokens.badge_style
        if badge_style == "circle":
            circles = ("❶", "❷", "❸", "❹", "❺", "❻", "❼", "❽", "❾")
            badge_txt = circles[index] if index < len(circles) else str(index + 1)
        elif badge_style in ("cyan", "keycap"):
            badge_txt = f"[{index + 1}]"
        elif badge_style == "none":
            badge_txt = ""
        else:
            badge_txt = str(index + 1)

        if tokens.name == "neon":
            badge_fg = "#FF007F"
        elif tokens.name == "classic":
            badge_fg = "#FFFFFF" if selected else "#000000"
        elif tokens.name == "fluent":
            badge_fg = "#60CDFF" if selected else p.subtext
        elif tokens.name == "modern":
            badge_fg = "#E9D5FF" if selected else p.subtext
        else:
            badge_fg = (
                p.accent
                if selected and tokens.selected_row_style == "bold_only"
                else (p.highlight_fg if selected else p.subtext)
            )
        f_badge = get_ui_font(size=max(8, f_sz - 2), bold=selected)
        self._badge.config(text=badge_txt, bg=row_bg, fg=badge_fg, font=f_badge)

        # 3. Candidate text
        f_text = get_ui_font(size=f_sz, bold=selected, rtl=is_rtl)
        self._text.config(text=candidate.text, bg=row_bg, fg=row_fg, font=f_text)

        # 4. Meta tag setup
        tags = {"SENTENCE": " [ادامه]", "NEXT_WORD": " [بعدی]", "AUTOCORRECT": " ≈"}
        tag_txt = tags.get(getattr(candidate.kind, "name", ""), "")
        tag_fg = p.subtext if not selected else (p.highlight_fg if tokens.name != "neon" else "#546E7A")
        f_tag = get_ui_font(size=max(8, f_sz - 3), rtl=True)
        self._tag.config(text=tag_txt, bg=row_bg, fg=tag_fg, font=f_tag)

        # 5. Meter setup
        always = bool(getattr(tokens, "confidence_meter_always", False))
        if always or candidate.score > 0:
            meter_txt = f" {confidence_bar(candidate.score)}"
        else:
            meter_txt = ""

        meter_fg = "#00FF66" if tokens.name == "neon" else (p.highlight_fg if selected else p.subtext)
        self._meter.config(text=meter_txt, bg=row_bg, fg=meter_fg, font=f_badge)

        # Layout packing
        for w in (self._accent_bar, self._badge, self._text, self._tag, self._meter):
            w.pack_forget()

        lead_side = "right" if is_rtl else "left"
        trail_side = "left" if is_rtl else "right"

        if has_accent_bar:
            self._accent_bar.pack(side=lead_side, fill="y", padx=(0, 3) if is_rtl else (3, 0))

        if badge_txt:
            self._badge.pack(side=lead_side, padx=(3, 5) if is_rtl else (5, 3))

        self._text.pack(side=lead_side, fill="x", expand=True)

        if meter_txt:
            self._meter.pack(side=trail_side, padx=(4, 2) if is_rtl else (2, 4))

        if tag_txt:
            self._tag.pack(side=trail_side, padx=2)

    def config(self, cnf=None, **kwargs):
        if cnf is None:
            cnf = {}
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
        if "text" in kwargs:
            self._formatted_text = kwargs.pop("text")
        if "bg" in kwargs:
            bg_col = kwargs["bg"]
            self._current_bg = bg_col
            super().config(bg=bg_col)
            for w in (self._badge, self._text, self._tag, self._meter):
                try:
                    w.config(bg=bg_col)
                except Exception:
                    pass
        passthrough = {k: v for k, v in kwargs.items() if k not in ("text", "anchor", "justify", "font")}
        if passthrough:
            super().config(**passthrough)

    configure = config

    def cget(self, key):
        if key == "text":
            return self._formatted_text or self._text.cget("text")
        return super().cget(key)

    __getitem__ = cget


class OverlayWindow:
    """Always-on-top overlay that never steals focus (best-effort)."""

    @staticmethod
    def _get_grip_text(style: str) -> str:
        if style == "macos":
            return "🔴 🟡 🟢   روان"
        if style == "ios":
            return "   روان"
        if style == "classic":
            return "روان           — □ ✕"
        if style == "neon":
            return "// RAVAAN HUD //"
        if style == "fluent":
            return "⊞  روان"
        if style == "modern":
            return "✦  روان  ✦"
        if style == "minimal":
            return "⋯ روان ⋯"
        return "•• روان ••"

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
        self._separators: list[tk.Frame] = []

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
        self._ui_style = (
            getattr(self.cfg, "prediction_ui_style", "macos") if self.cfg else "macos"
        )
        layout = getattr(self.cfg, "prediction_layout", "vertical") if self.cfg else "vertical"
        custom_colors = None
        if self.cfg and getattr(self.cfg, "prediction_use_custom_colors", False):
            custom_colors = {
                "bg": getattr(self.cfg, "prediction_custom_bg", "#202024"),
                "fg": getattr(self.cfg, "prediction_custom_fg", "#F5F5F7"),
                "accent": getattr(self.cfg, "prediction_custom_accent", "#0A84FF"),
                "border": getattr(self.cfg, "prediction_custom_border", "#3A3A42"),
                "highlight": getattr(self.cfg, "prediction_custom_highlight", "#0A84FF"),
                "highlight_fg": getattr(self.cfg, "prediction_custom_highlight_fg", "#FFFFFF"),
            }
        self.style_tokens = get_prediction_style(
            self._ui_style, mode, custom_colors=custom_colors, layout=layout
        )
        self.palette = self.style_tokens.palette
        tokens = self.style_tokens
        bg = self.palette.bg
        border = tokens.border_color or self.palette.border

        opacity = (
            float(getattr(self.cfg, "prediction_opacity", tokens.alpha))
            if self.cfg
            else tokens.alpha
        )
        f_sz = (
            int(getattr(self.cfg, "prediction_font_size", int(self.theme.font_size)))
            if self.cfg
            else int(self.theme.font_size)
        )

        if self._ui_style == "glass":
            opacity = min(opacity, 0.72)
        elif self._ui_style == "classic":
            opacity = 1.0

        self._target_alpha = opacity
        try:
            self._root.attributes("-alpha", opacity)
        except Exception:  # noqa: BLE001
            pass
        # Theme changed: force the next show_predictions to re-render rows with
        # the new palette (the dedup must not keep stale colors on screen).
        self._last_render_key = None

        bd = tokens.border_width
        relief = tokens.border_relief

        # Acrylic blur-behind: enabled only when style tokens allow it.
        attrs = self._apply_noactivate()
        self._acrylic_active = bool(attrs.get("acrylic")) if isinstance(attrs, dict) else False
        if self._acrylic_active:
            self._target_alpha = 1.0
            try:
                self._root.attributes("-alpha", 1.0)
                self._root.attributes("-transparentcolor", bg)
            except Exception:  # noqa: BLE001
                self._acrylic_active = False
        elif hasattr(self, "_frame"):
            # Leaving the acrylic style: neutralize any leftover transparency key.
            try:
                self._root.attributes("-transparentcolor", "#010101")
            except Exception:  # noqa: BLE001
                pass
        self._row_bg = self.palette.card_bg if self._acrylic_active else bg

        grip_bg = "#0A246A" if self._ui_style == "classic" else self._row_bg
        grip_fg = (
            "#FFFFFF"
            if self._ui_style == "classic"
            else (
                "#4CC2FF"
                if self._ui_style == "fluent"
                else (
                    "#FF007F"
                    if self._ui_style == "neon"
                    else (
                        "#E9D5FF"
                        if self._ui_style == "modern"
                        else (
                            "#8AB4D8"
                            if self._ui_style == "glass"
                            else (
                                "#D0BCFF"
                                if self._ui_style == "material"
                                else self.palette.subtext
                            )
                        )
                    )
                )
            )
        )
        hint_bg = "#D4D0C8" if self._ui_style == "classic" else self._row_bg
        hint_fg = (
            "#404040"
            if self._ui_style == "classic"
            else (
                "#FF007F"
                if self._ui_style == "neon"
                else (
                    "#60CDFF"
                    if self._ui_style == "fluent"
                    else (
                        "#A894C4"
                        if self._ui_style == "modern"
                        else self.palette.subtext
                    )
                )
            )
        )

        if hasattr(self, "_frame"):
            self._frame.config(
                bg=bg,
                highlightbackground=border,
                highlightthickness=bd,
                bd=bd,
                relief=relief,
            )
            if hasattr(self, "_grip"):
                grip_text = self._get_grip_text(self._ui_style)
                self._grip.config(text=grip_text, bg=grip_bg, fg=grip_fg)
            self._hint.config(bg=hint_bg, fg=hint_fg)
            self._lang_label.config(bg=self.palette.card_bg, fg=self.palette.accent)
        else:
            self._frame = tk.Frame(
                self._root,
                bg=bg,
                bd=bd,
                relief=relief,
                highlightthickness=bd,
                highlightbackground=border,
            )
            self._frame.pack(fill="both", expand=True)

            f_grip = get_ui_font(size=max(8, f_sz - 4))
            grip_text = self._get_grip_text(self._ui_style)
            self._grip = tk.Label(
                self._frame,
                text=grip_text,
                bg=grip_bg,
                fg=grip_fg,
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
                bg=hint_bg,
                fg=hint_fg,
                font=f_hint,
                justify="left",
                padx=10,
                pady=tokens.row_padding_y,
            )
            self._bind_drag(self._hint)

            f_lang = get_ui_font(size=f_sz + 1, bold=True, rtl=True)
            self._lang_label = tk.Label(
                self._frame,
                text="",
                bg=self.palette.card_bg,
                fg=self.palette.accent,
                font=f_lang,
                padx=14,
                pady=7,
                relief="flat",
            )

        # Live refresh: when the popup is currently visible (style/theme changed
        # mid-session from Settings), re-render the rows with the new palette.
        if getattr(self, "_mode", "idle") == "predict" and self._candidates:
            try:
                self._render_candidates()
            except Exception:  # noqa: BLE001
                pass

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
        targets: list[tk.Widget] = [widget]
        if isinstance(widget, CandidateRow):
            targets.extend([
                widget._accent_bar,
                widget._badge,
                widget._text,
                widget._tag,
                widget._meter,
            ])
        for w in targets:
            w.bind("<Button-1>", lambda e, r=row_index: self._on_mouse_down(e, r))
            w.bind("<B1-Motion>", self._on_mouse_drag)
            w.bind("<ButtonRelease-1>", lambda e, r=row_index: self._on_mouse_up(e, r))
            if row_index >= 0:
                w.bind("<Enter>", lambda _e, r=row_index: self._on_row_enter(r))
                w.bind("<Leave>", lambda _e, r=row_index: self._on_row_leave(r))

    def _on_row_enter(self, idx: int) -> None:
        if idx < len(self._candidates) and idx != self._selected and idx < len(self._rows):
            p = getattr(self, "palette", get_active_palette())
            self._rows[idx].config(bg=getattr(p, "button_hover", p.card_bg))

    def _on_row_leave(self, idx: int) -> None:
        if idx < len(self._candidates) and idx != self._selected and idx < len(self._rows):
            p = getattr(self, "palette", get_active_palette())
            self._rows[idx].config(bg=getattr(self, "_row_bg", p.bg))

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

    def _apply_noactivate(self, show: bool = False) -> dict[str, bool]:
        tokens = getattr(self, "style_tokens", None)
        palette = getattr(self, "palette", get_active_palette())
        acrylic = tokens.acrylic if tokens else (getattr(self, "_ui_style", "modern") == "macos")
        border_col = (tokens.border_color or palette.border) if (tokens and tokens.border_width > 0) else None
        radius = tokens.corner_radius if tokens else 8.0
        return apply_popup_window_attributes(
            self._root,
            palette,
            show=show,
            acrylic=acrylic,
            border_color=border_col,
            corner_radius=radius,
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
                    style = wapi.user32.GetWindowLongW(root_hwnd, -20)
                    if not (style & 0x08000000):
                        wapi.user32.SetWindowLongW(root_hwnd, -20, style | 0x08000088)
                    wapi.user32.SetWindowPos(root_hwnd, -1, 0, 0, 0, 0, 0x0037)
                    self._root.deiconify()
                    wapi.user32.ShowWindow(root_hwnd, wapi.SW_SHOWNOACTIVATE)
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
            # Full event processing at ~40 Hz instead of every loop tick (~125 Hz):
            # update() is expensive and, on the UI thread, starves the keyboard
            # hook thread of the GIL — a direct source of typed-echo lag.
            now = time.monotonic()
            if now - getattr(self, "_last_full_update", 0.0) >= 0.025:
                self._last_full_update = now
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
        self.current_x = -1
        self.current_y = -1
        self._clear_rows()
        self._lang_label.pack_forget()
        self._hint.pack_forget()
        if hasattr(self, "_grip"):
            self._grip.pack_forget()
        try:
            self._root.withdraw()
        except Exception:  # noqa: BLE001
            pass
        if sys.platform == "win32":
            try:
                from ravan.platform import winapi as wapi

                root_hwnd = self._get_root_hwnd()
                if root_hwnd:
                    wapi.user32.ShowWindow(root_hwnd, 0)
            except Exception:  # noqa: BLE001
                pass
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
        for sep in getattr(self, "_separators", []):
            sep.pack_forget()

    @staticmethod
    def _format_lang_label(label: str) -> str:
        raw = label.strip()
        if raw in ("FA", "فا"):
            return "🇮🇷 فارسی"
        if raw in ("FA-TL", "TL", "فا-TL"):
            return "🔤 فینگلیش (FA)"
        if raw in ("EN", "En", "en"):
            return "🇺🇸 English"
        if raw.lower().startswith("ar") or raw == "عرب":
            return "🇸🇦 العربية"
        return raw

    def show_language(self, label: str, x: int, y: int, height: int = 16, placement: str = "click") -> None:
        self.hide()
        self._mode = "lang"
        display_label = self._format_lang_label(label)
        self._lang_label.config(text=display_label)
        self._lang_label.pack(padx=10, pady=6)
        if placement in ("bottom_right", "bottom_left", "top_right", "top_left"):
            self._place_at_corner(placement)
        else:
            if (x <= 1 and y <= 1) or x < 0 or y < 0:
                try:
                    from ravan.platform.caret import _cursor_position

                    cp = _cursor_position()
                    x, y, height = cp.x, cp.y, cp.height
                except Exception:
                    pass
            self._place(x, y + height + 4)
        self._show_no_activate()
        self._fade_after = self._root.after(1400, self.hide)

    @staticmethod
    def corner_position(
        placement: str,
        work_area: tuple[int, int, int, int],
        popup_w: int,
        popup_h: int,
    ) -> tuple[int, int]:
        """Anchor point for a screen-corner placement (default: above the tray icons)."""
        m_left, m_top, m_right, m_bottom = work_area
        px = (m_right - popup_w - 12) if "right" in placement else (m_left + 12)
        py = (m_top + 8) if placement.startswith("top") else (m_bottom - popup_h - 8)
        return int(px), int(py)

    def _place_at_corner(self, placement: str) -> None:
        """Anchor the chip to a screen corner of the primary monitor."""
        self._root.update_idletasks()
        w = max(self._root.winfo_reqwidth(), 60)
        h = max(self._root.winfo_reqheight(), 24)
        try:
            from ravan.platform import winapi as wapi

            sw = self._root.winfo_screenwidth()
            sh = self._root.winfo_screenheight()
            area = wapi.get_monitor_work_area(sw // 2, sh // 2)
        except Exception:
            area = (0, 0, self._root.winfo_screenwidth(), self._root.winfo_screenheight())
        px, py = self.corner_position(placement, area, w, h)
        self._place(px, py)

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

        # Identical candidate list while typing: keep the popup exactly as it is —
        # no widget re-render, no SetWindowPos per keystroke (typing smoothness).
        render_key = (tuple(c.text for c in candidates), prev_selected)
        if (
            keep_selection
            and self.visible
            and self._mode == "predict"
            and render_key == getattr(self, "_last_render_key", None)
        ):
            return
        self._last_render_key = render_key

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
        tokens = getattr(self, "style_tokens", None)
        is_horizontal = (tokens and tokens.layout == "horizontal") or (
            getattr(self.cfg, "prediction_layout", "vertical") == "horizontal"
        )
        if is_horizontal:
            popup_w = max(self._root.winfo_reqwidth(), 160)
            popup_h = max(self._root.winfo_reqheight(), 34)
        else:
            popup_w = max(self._root.winfo_reqwidth(), 180)
            popup_h = max(self._root.winfo_reqheight(), 28 * len(self._candidates) + 28)
        eff_h = max(height, 22)
        from ravan.platform import winapi as wapi

        m_left, m_top, m_right, m_bottom = wapi.get_monitor_work_area(x, y)

        if self.has_custom_pos and self.custom_x >= 0 and self.custom_y >= 0:
            px = self.custom_x
            py = self.custom_y
        elif self.visible and self.current_x >= 0 and self.current_y >= 0:
            # Word prediction in progress: keep popup position stable, do not jump with each keystroke!
            px = self.current_x
            py = self.current_y
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
        tokens = getattr(self, "style_tokens", None)
        badge_style = tokens.badge_style if tokens else "plain"
        sel_style = tokens.selected_row_style if tokens else "fill"

        if badge_style == "circle":
            circles = ("❶", "❷", "❸", "❹", "❺", "❻", "❼", "❽", "❾")
            prefix = f"{circles[index]} " if index < len(circles) else f"{index + 1} "
        elif badge_style == "cyan":
            prefix = f"[{index + 1}] "
        elif badge_style == "none":
            prefix = ""
        else:
            prefix = f"{index + 1}  "

        if sel_style in ("leading_bar", "neon"):
            mark = "▌ " if selected else "  "
        elif sel_style in ("bold_only", "pill"):
            mark = ""
        else:
            mark = "▶ " if selected else "   "

        tags = {"SENTENCE": "  [ادامه]", "NEXT_WORD": "  [بعدی]", "AUTOCORRECT": "  ≈"}
        tag = tags.get(candidate.kind.name, "")

        if show_meter is None:
            always = bool(tokens and getattr(tokens, "confidence_meter_always", False))
            show_meter = bool(always or (self is not None and getattr(self, "_mode", "") == "predict"))

        if show_meter and (candidate.score > 0 or getattr(tokens, "confidence_meter_always", False)):
            meter = f" {confidence_bar(candidate.score)}"
        else:
            meter = ""

        if tokens and tokens.text_align == "center":
            return f"{candidate.text}{tag}{meter}"

        return f"{mark}{prefix}{candidate.text}{tag}{meter}"

    def _render_candidates(self) -> None:
        ui_style = getattr(self.cfg, "prediction_ui_style", "macos") if self.cfg else "macos"
        mode = getattr(self, "theme_mode", "auto")
        layout = getattr(self.cfg, "prediction_layout", "vertical") if self.cfg else "vertical"
        custom_colors = None
        if self.cfg and getattr(self.cfg, "prediction_use_custom_colors", False):
            custom_colors = {
                "bg": getattr(self.cfg, "prediction_custom_bg", "#202024"),
                "fg": getattr(self.cfg, "prediction_custom_fg", "#F5F5F7"),
                "accent": getattr(self.cfg, "prediction_custom_accent", "#0A84FF"),
                "border": getattr(self.cfg, "prediction_custom_border", "#3A3A42"),
                "highlight": getattr(self.cfg, "prediction_custom_highlight", "#0A84FF"),
                "highlight_fg": getattr(self.cfg, "prediction_custom_highlight_fg", "#FFFFFF"),
            }
        tokens = get_prediction_style(
            ui_style, mode, custom_colors=custom_colors, layout=layout
        )
        self.style_tokens = tokens

        p = tokens.palette
        self.palette = p
        ui_style = tokens.name
        f_sz = (
            int(getattr(self.cfg, "prediction_font_size", int(self.theme.font_size)))
            if self.cfg
            else int(self.theme.font_size)
        )

        pad_y = tokens.row_padding_y
        pad_x = tokens.row_padding_x
        is_horizontal = tokens.layout == "horizontal"
        is_rtl = any(ord(ch) > 127 for cand in self._candidates for ch in cand.text[:2])
        pack_side = "right" if is_rtl else "left"

        if tokens.show_grip and ui_style != "compact" and hasattr(self, "_grip"):
            if is_horizontal:
                self._grip.config(
                    text="••",
                    bg=getattr(self, "_row_bg", p.bg),
                    fg=p.subtext,
                    padx=5,
                    pady=2,
                )
                self._grip.pack(side=pack_side, fill="y", padx=(2, 0))
            else:
                grip_txt = self._get_grip_text(ui_style)
                grip_bg = "#0A246A" if ui_style == "classic" else getattr(self, "_row_bg", p.bg)
                grip_fg = "#FFFFFF" if ui_style == "classic" else (
                    "#FF007F" if ui_style == "neon" else (
                        "#60CDFF" if ui_style == "fluent" else (
                            "#D8B4FE" if ui_style == "modern" else p.subtext
                        )
                    )
                )
                self._grip.config(
                    text=grip_txt,
                    bg=grip_bg,
                    fg=grip_fg,
                    padx=8,
                    pady=2,
                )
                self._grip.pack(side="top", fill="x")
        elif hasattr(self, "_grip"):
            self._grip.pack_forget()

        if not hasattr(self, "_separators"):
            self._separators = []

        while len(self._rows) < len(self._candidates):
            idx = len(self._rows)
            row = CandidateRow(
                self._frame,
                row_index=idx,
                bg=getattr(self, "_row_bg", p.bg),
                padx=pad_x,
                pady=pad_y,
            )
            self._bind_drag(row, row_index=idx)
            self._rows.append(row)

        while len(self._separators) < max(0, len(self._candidates) - 1):
            sep = tk.Frame(self._frame, height=1)
            self._separators.append(sep)

        # Clear existing packs
        for r in self._rows:
            r.pack_forget()
        for s in self._separators:
            s.pack_forget()

        for i, c in enumerate(self._candidates):
            selected = i == self._selected
            self._rows[i].set_candidate(
                candidate=c,
                index=i,
                selected=selected,
                tokens=tokens,
                f_sz=f_sz,
                is_horizontal=is_horizontal,
            )
            self._rows[i]._formatted_text = self._row_text(i, c, selected)
            if is_horizontal:
                self._rows[i].pack(side=pack_side, padx=3, pady=pad_y)
                if tokens.show_separators and i < len(self._candidates) - 1:
                    sep_frame = self._separators[i]
                    sep_frame.config(width=1, height=18, bg=tokens.separator_color or p.border)
                    sep_frame.pack(side=pack_side, fill="y", padx=1, pady=3)
            else:
                self._rows[i].pack(fill="x")
                if tokens.show_separators and i < len(self._candidates) - 1:
                    sep_frame = self._separators[i]
                    sep_frame.config(height=1, width=0, bg=tokens.separator_color or p.border)
                    sep_frame.pack(fill="x")

        for j in range(len(self._candidates), len(self._rows)):
            self._rows[j].pack_forget()

        if tokens.show_hint_bar and not is_horizontal:
            self._hint.config(
                bg=getattr(self, "_row_bg", p.bg),
                fg=p.subtext,
                font=get_ui_font(size=max(8, f_sz - 3), rtl=True),
            )
            self._hint.pack(fill="x")
        else:
            self._hint.pack_forget()

        self._last_render_key = (tuple(c.text for c in self._candidates), self._selected)

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

    @property
    def is_horizontal(self) -> bool:
        tokens = getattr(self, "style_tokens", None)
        return bool(
            (tokens and tokens.layout == "horizontal")
            or (getattr(self.cfg, "prediction_layout", "vertical") == "horizontal")
        )

    @property
    def _is_horizontal(self) -> bool:
        return self.is_horizontal

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

