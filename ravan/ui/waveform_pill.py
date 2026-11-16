"""Floating non-activating Fluent 2 Voice Capsule with live RMS waveform & shimmer."""

from __future__ import annotations

import logging
import math
import sys
import time
import tkinter as tk
from collections import deque
from collections.abc import Callable

from PIL import ImageTk

from ravan.core.i18n import is_rtl, t
from ravan.platform.caret import get_caret_rect
from ravan.platform.winapi import get_monitor_work_area
from ravan.ui.theme import (
    Palette,
    apply_popup_window_attributes,
    clamp_popup_position,
    get_active_palette,
    get_dpi_scale,
    get_ui_font,
)
from ravan.ui.widgets.icons import render_icon_image
from ravan.ui.widgets.surface import render_rounded_surface

log = logging.getLogger(__name__)
PILL_WIDTH, PILL_HEIGHT, BAR_COUNT = 376, 54, 16


def _blend_hex(hex_a: str, hex_b: str, factor: float) -> str:
    fa = max(0.0, min(1.0, factor))
    a, b = int(hex_a.lstrip("#")[:6], 16), int(hex_b.lstrip("#")[:6], 16)
    ch = [int(((a >> sh) & 0xFF) * (1.0 - fa) + ((b >> sh) & 0xFF) * fa) for sh in (16, 8, 0)]
    return f"#{ch[0]:02x}{ch[1]:02x}{ch[2]:02x}"


def _draw_rounded_rect(
    canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float, r: float, fill: str, outline: str = ""
) -> int:
    r = max(1.0, min(r, (x2 - x1) / 2.0, (y2 - y1) / 2.0))
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
        x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, fill=fill, outline=outline)


class WaveformPillWindow:
    """Translucent non-activating floating voice capsule with animated waveform."""

    def __init__(
        self,
        parent: tk.Misc | None = None,
        theme_mode: str = "auto",
        on_cancel: Callable[[], None] | None = None,
    ) -> None:
        self.parent, self.theme_mode, self.on_cancel = parent, theme_mode, on_cancel
        self._top: tk.Toplevel | tk.Tk | None = None
        self._canvas: tk.Canvas | None = None
        self._visible, self._state, self._language = False, "hidden", "fa"
        self._start_ts, self._phase, self._target_rms = 0.0, 0.0, 0.08
        self._bars: deque[float] = deque([0.12] * BAR_COUNT, maxlen=BAR_COUNT)
        self._rms_provider: Callable[[], float] | None = None
        self._elapsed_provider: Callable[[], float] | None = None
        self._anim_after: str | None = None
        self._bg_photo: ImageTk.PhotoImage | None = None
        self._mic_photo: ImageTk.PhotoImage | None = None
        self._close_photo: ImageTk.PhotoImage | None = None
        self._palette: Palette = get_active_palette(theme_mode)
        self._dpi, self._close_hover = 1.0, False
        self._last_bounds: tuple[int, int, int, int] | None = None
        self._font_badge = get_ui_font(size=8, bold=True)
        self._font_timer = get_ui_font(size=9, bold=True, rtl=False)
        self._font_trans = get_ui_font(size=8, bold=True, rtl=True)

    @property
    def visible(self) -> bool:
        return self._visible and self._top is not None

    @property
    def state(self) -> str:
        return self._state if self._visible else "hidden"

    def bounds(self) -> tuple[int, int, int, int] | None:
        return self._last_bounds if self._visible else None

    def push_rms(self, level: float) -> None:
        """Push an audio RMS sample [0.0..1.0] into the equalizer target."""
        self._target_rms = max(0.04, min(1.0, float(level)))

    def _ensure_window(self) -> None:
        if self._top is not None:
            try:
                if self._top.winfo_exists():
                    return
            except tk.TclError:
                self._top = None
        try:
            self._palette = get_active_palette(self.theme_mode)
            pal = self._palette
            parent_w = self.parent if isinstance(self.parent, tk.Misc) else None
            top: tk.Toplevel | tk.Tk = tk.Toplevel(parent_w) if parent_w else tk.Tk()
            top.withdraw()
            apply_popup_window_attributes(
                top, pal, border_color=pal.border_focus, corner_radius=20.0, acrylic=True, show=False
            )
            self._dpi = get_dpi_scale(top)
            w_px, h_px = int(round(PILL_WIDTH * self._dpi)), int(round(PILL_HEIGHT * self._dpi))
            canvas = tk.Canvas(top, width=w_px, height=h_px, bg=pal.bg_surface, highlightthickness=0, bd=0)
            canvas.pack(fill=tk.BOTH, expand=True)

            surf = render_rounded_surface(
                width=w_px,
                height=h_px,
                radius=int(min(h_px * 0.44, 22 * self._dpi)),
                fill_hex=pal.bg_surface,
                border_hex=pal.border_focus,
                bg_hex=pal.bg_base,
            )
            self._bg_photo = ImageTk.PhotoImage(surf, master=top)
            self._mic_photo = ImageTk.PhotoImage(
                render_icon_image("mic", size=int(16 * self._dpi), color=pal.highlight_fg, dpi=1.0), master=top
            )
            self._close_photo = ImageTk.PhotoImage(
                render_icon_image("close", size=int(12 * self._dpi), color=pal.subtext, dpi=1.0), master=top
            )
            rtl = is_rtl()
            self._font_badge = get_ui_font(size=8, bold=True)
            self._font_timer = get_ui_font(size=9, bold=True, rtl=rtl)
            self._font_trans = get_ui_font(size=8, bold=True, rtl=rtl)
            canvas.bind("<Button-1>", self._on_canvas_click)
            canvas.bind("<Motion>", self._on_canvas_motion)
            canvas.bind("<Leave>", lambda _e: self._set_close_hover(False))
            self._top, self._canvas = top, canvas
        except Exception as exc:  # noqa: BLE001
            log.debug("Failed to initialize WaveformPillWindow: %s", exc)
            self._top, self._canvas = None, None

    def _set_close_hover(self, hovering: bool) -> None:
        if self._close_hover != hovering:
            self._close_hover = hovering
            if self._visible:
                self._draw_frame()

    def _close_zone(self) -> tuple[float, float, float, float]:
        s = self._dpi
        w_px, h_px, pad_x, btn_w, btn_h = PILL_WIDTH * s, PILL_HEIGHT * s, 12 * s, 48 * s, 26 * s
        y1 = (h_px - btn_h) / 2
        if is_rtl():
            return (pad_x, y1, pad_x + btn_w, y1 + btn_h)
        return (w_px - pad_x - btn_w, y1, w_px - pad_x, y1 + btn_h)

    def _on_canvas_motion(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        x1, y1, x2, y2 = self._close_zone()
        hov = x1 <= event.x <= x2 and y1 <= event.y <= y2
        self._set_close_hover(hov)
        if self._canvas is not None:
            self._canvas.configure(cursor="hand2" if hov else "")

    def _on_canvas_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        x1, y1, x2, y2 = self._close_zone()
        if x1 <= event.x <= x2 and y1 <= event.y <= y2:
            if self.on_cancel:
                self.on_cancel()
            else:
                self.hide()

    def _resolve_pill_coords(self, w_px: int, h_px: int) -> tuple[int, int]:
        assert self._top is not None
        caret = get_caret_rect()
        if caret is not None and (caret.x != 0 or caret.y != 0):
            cw = int(getattr(caret, "width", getattr(caret, "w", 0)) or 0)
            ch = int(getattr(caret, "height", getattr(caret, "h", 22)) or 22)
            px = caret.x + max(0, cw // 2) - w_px // 2
            py = caret.y - h_px - 14
            if py < 24:
                py = caret.y + max(22, ch) + 12
            return clamp_popup_position(self._top, px, py, w_px, h_px, margin=12)

        if sys.platform == "win32":
            m_left, _, m_right, m_bottom = get_monitor_work_area(0, 0)
        else:
            m_left = 0
            m_right = max(800, int(self._top.winfo_screenwidth()))
            m_bottom = max(600, int(self._top.winfo_screenheight()))
        px = m_left + ((m_right - m_left - w_px) // 2)
        py = m_bottom - h_px - 28
        return clamp_popup_position(self._top, px, py, w_px, h_px, margin=12)

    def _present(self) -> None:
        if self._top is None or self._canvas is None:
            return
        w_px, h_px = int(round(PILL_WIDTH * self._dpi)), int(round(PILL_HEIGHT * self._dpi))
        x, y = self._resolve_pill_coords(w_px, h_px)
        self._top.geometry(f"{w_px}x{h_px}+{x}+{y}")
        self._top.deiconify()
        apply_popup_window_attributes(
            self._top, self._palette, border_color=self._palette.border_focus, corner_radius=20.0, acrylic=True, show=True
        )
        self._visible = True
        self._last_bounds = (x, y, x + w_px, y + h_px)
        self._draw_frame()
        self._schedule_tick()

    def show_recording(
        self,
        language: str = "fa",
        rms_provider: Callable[[], float] | None = None,
        elapsed_provider: Callable[[], float] | None = None,
    ) -> None:
        """Display the capsule in live waveform recording mode."""
        self._ensure_window()
        if self._top is None:
            return
        self._state, self._language = "recording", (language or "fa").upper()
        self._start_ts, self._phase = time.monotonic(), 0.0
        self._rms_provider, self._elapsed_provider = rms_provider, elapsed_provider
        self._bars = deque([0.12] * BAR_COUNT, maxlen=BAR_COUNT)
        self._present()

    def show_transcribing(self, language: str | None = None) -> None:
        """Transition capsule to shimmering transcribing indicator."""
        self._ensure_window()
        if self._top is None:
            return
        self._state = "transcribing"
        if language:
            self._language = language.upper()
        self._rms_provider = None
        self._present()

    def _schedule_tick(self) -> None:
        if self._anim_after is not None and self._top is not None:
            try:
                self._top.after_cancel(self._anim_after)
            except Exception:
                pass
            self._anim_after = None
        if self._visible and self._top is not None:
            try:
                self._anim_after = self._top.after(45, self._tick_anim)
            except Exception:
                self._anim_after = None

    def step_frame(self) -> None:
        """Advance waveform phase by one tick and redraw without spawning extra timers."""
        if not self._visible or self._top is None:
            return
        self._phase += 0.24
        if self._state == "recording":
            rms = self._target_rms
            if self._rms_provider is not None:
                try:
                    rms = max(0.04, min(1.0, float(self._rms_provider())))
                except Exception:
                    pass
            ripple = 0.04 * (0.5 + 0.5 * math.sin(self._phase * 1.4))
            self._bars.append(max(0.06, min(1.0, rms + ripple)))
        self._draw_frame()

    def _tick_anim(self) -> None:
        if not self._visible or self._top is None:
            self._anim_after = None
            return
        # Cancel any still-pending timer if _tick_anim was invoked manually rather than by Tk
        self.step_frame()
        self._schedule_tick()

    def _draw_frame(self) -> None:
        canvas = self._canvas
        if canvas is None:
            return
        pal, s, rtl = self._palette, self._dpi, is_rtl()
        w_px, h_px = PILL_WIDTH * s, PILL_HEIGHT * s
        cy, pad_x, orb_r = h_px / 2, 12 * s, 14 * s
        if not canvas.find_withtag("bg") and self._bg_photo is not None:
            canvas.create_image(w_px / 2, h_px / 2, image=self._bg_photo, tags="bg")
        canvas.delete("dyn")

        orb_cx = (w_px - pad_x - orb_r) if rtl else (pad_x + orb_r)
        pulse = 0.5 + 0.5 * math.sin(self._phase * 1.8)
        base_orb = pal.danger if self._state == "recording" else pal.accent
        orb_col = _blend_hex(base_orb, "#ff6b6b" if self._state == "recording" else pal.highlight, pulse * 0.45)
        glow_r = orb_r + (2.5 + 1.5 * pulse) * s
        canvas.create_oval(
            orb_cx - glow_r, cy - glow_r, orb_cx + glow_r, cy + glow_r,
            fill=_blend_hex(pal.bg_surface, orb_col, 0.26), outline="", tags="dyn",
        )
        canvas.create_oval(orb_cx - orb_r, cy - orb_r, orb_cx + orb_r, cy + orb_r, fill=orb_col, outline="", tags="dyn")
        if self._mic_photo is not None:
            canvas.create_image(orb_cx, cy, image=self._mic_photo, tags="dyn")

        wave_w, bar_w = 96 * s, max(2.0, 3.0 * s)
        wave_x0 = (orb_cx - orb_r - 12 * s - wave_w) if rtl else (orb_cx + orb_r + 12 * s)
        step, bars = wave_w / BAR_COUNT, list(self._bars)
        for idx in range(BAR_COUNT):
            bx = wave_x0 + idx * step + (step - bar_w) / 2
            env = 0.55 + 0.45 * math.sin(math.pi * (idx + 0.5) / BAR_COUNT)
            if self._state == "transcribing":
                shimmer = 0.5 + 0.5 * math.sin(self._phase * 2.2 - idx * 0.45)
                amp, b_col = 0.18 + 0.42 * shimmer * env, _blend_hex(pal.subtext, pal.accent, shimmer)
            else:
                amp = max(0.10, min(1.0, bars[idx] * env))
                b_col = _blend_hex(pal.subtext, pal.accent, min(1.0, amp * 1.15))
            bh = max(bar_w + 1.0, amp * 26.0 * s)
            half_span = max(0.5, (bh - bar_w) / 2.0)
            cx_bar = bx + bar_w / 2.0
            canvas.create_line(
                cx_bar, cy - half_span, cx_bar, cy + half_span,
                width=bar_w, capstyle=tk.ROUND, fill=b_col, tags="dyn",
            )

        elapsed = self._elapsed_provider() if self._elapsed_provider else (time.monotonic() - self._start_ts)
        secs = max(0, int(elapsed))
        status_txt = (
            t("voice.transcribing_short", "در حال تبدیل..." if rtl else "Transcribing...")
            if self._state == "transcribing"
            else f"{secs // 60:02d}:{secs % 60:02d}"
        )
        cx_1, cy_1, cx_2, cy_2 = self._close_zone()
        btn_bg = pal.button_hover if self._close_hover else pal.bg_interactive
        btn_id = _draw_rounded_rect(canvas, cx_1, cy_1, cx_2, cy_2, 8 * s, fill=btn_bg, outline=pal.border_subtle)
        canvas.addtag_withtag("dyn", btn_id)
        if self._close_photo is not None:
            canvas.create_image(cx_1 + 13 * s, cy, image=self._close_photo, tags="dyn")
        canvas.create_text(cx_1 + 33 * s, cy, text="Esc", fill=pal.subtext, font=self._font_badge, tags="dyn")

        badge_w, badge_h = 30 * s, 22 * s
        badge_x1 = (cx_2 + 8 * s) if rtl else (cx_1 - 8 * s - badge_w)
        timer_x, timer_anchor = (badge_x1 + badge_w + 10 * s, "w") if rtl else (badge_x1 - 10 * s, "e")
        badge_id = _draw_rounded_rect(
            canvas, badge_x1, cy - badge_h / 2, badge_x1 + badge_w, cy + badge_h / 2, 7 * s, fill=pal.badge_bg
        )
        canvas.addtag_withtag("dyn", badge_id)
        canvas.create_text(
            badge_x1 + badge_w / 2, cy, text=self._language[:4], fill=pal.badge_fg, font=self._font_badge, tags="dyn"
        )
        canvas.create_text(
            timer_x, cy, text=status_txt, anchor=timer_anchor, fill=pal.fg,
            font=self._font_trans if self._state == "transcribing" else self._font_timer, tags="dyn",
        )

    def hide(self) -> None:
        self._visible, self._state, self._rms_provider = False, "hidden", None
        if self._anim_after is not None and self._top is not None:
            try:
                self._top.after_cancel(self._anim_after)
            except Exception:
                pass
            self._anim_after = None
        if self._top is not None:
            try:
                self._top.withdraw()
            except Exception:
                pass

    def destroy(self) -> None:
        self.hide()
        self.on_cancel = None
        self._elapsed_provider = None
        self._bg_photo = None
        self._mic_photo = None
        self._close_photo = None
        if self._top is not None:
            try:
                self._top.destroy()
            except Exception:
                pass
            self._top, self._canvas = None, None
