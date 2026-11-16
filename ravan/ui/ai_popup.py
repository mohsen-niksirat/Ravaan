"""Spotlight-grade Fluent 2 AI Command Palette with live streaming & Before/After diff."""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from collections.abc import Callable, Iterator
from tkinter import ttk
from typing import Any

from ravan.core.ai import AI_PRESET_SPECS
from ravan.core.i18n import is_rtl, t
from ravan.ui.ai_diff import compute_word_diff, summarize_source_preview
from ravan.ui.theme import (
    Palette,
    apply_popup_window_attributes,
    clamp_popup_position,
    get_active_palette,
    get_dpi_scale,
    get_ui_font,
)
from ravan.ui.widgets import FluentBadge, FluentEntry, FluentPillButton, get_icon

log = logging.getLogger(__name__)
StreamCallback = Callable[[str, str, str, threading.Event | None], Iterator[str]]


class AIAssistantPopup:
    """Borderless translucent Fluent 2 command palette for AI text transformations."""

    def __init__(
        self,
        parent: tk.Misc | None,
        on_replace: Callable[[str], None],
        on_copy: Callable[[str], None],
        process_callback: Callable[[str, str, str], str],
        theme_mode: str = "auto",
        stream_callback: StreamCallback | None = None,
    ) -> None:
        self.parent, self.on_replace, self.on_copy = parent, on_replace, on_copy
        self.process_callback, self.stream_callback = process_callback, stream_callback
        self.theme_mode = theme_mode
        self._top: tk.Toplevel | tk.Tk | None = None
        self._input_text = self._latest_output = self._last_custom = ""
        self._last_action = "rewrite"
        self._diff_mode, self._streaming, self._closed = False, False, True
        self._cancel_event: threading.Event | None = None
        self._status_var: tk.StringVar | None = None
        self._txt_output: tk.Text | None = None
        self._ent_custom: FluentEntry | None = None
        self._chip_buttons: dict[str, FluentPillButton] = {}
        self._diff_btn = self._stop_btn = None
        self._shimmer_canvas: tk.Canvas | None = None
        self._shimmer_job: str | None = None
        self._shimmer_pos = 0.0
        self._drag_origin: tuple[int, int] | None = None
        self._palette: Palette = get_active_palette(theme_mode)
        self._sparkle_photo: Any = None

    def _pill(
        self, parent: tk.Misc, text: str, variant: str, rtl: bool, height: int, width: int, command: Any, icon: str | None = None
    ) -> FluentPillButton:
        return FluentPillButton(
            parent, text=text, icon=icon, variant=variant, palette=self._palette,
            rtl=rtl, parent_bg=self._palette.bg_surface, height=height, width=width, command=command,
        )

    def show(self, text: str, x: int, y: int) -> None:
        """Open the Fluent 2 AI command palette anchored near `(x, y)`."""
        self.hide()
        self._input_text, self._latest_output, self._last_action, self._last_custom = text, "", "rewrite", ""
        self._diff_mode, self._streaming, self._closed = False, False, False

        p = get_active_palette(self.theme_mode)
        self._palette, rtl = p, is_rtl()
        top: tk.Toplevel | tk.Tk = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        top.withdraw()
        self._top = top
        top.title("Ravaan AI Assistant")
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.configure(bg=p.bg_base)
        apply_popup_window_attributes(top, p, border_color=p.border_focus, corner_radius=14.0, acrylic=False, activate=True, show=False)

        shell = tk.Frame(top, bg=p.bg_base, highlightthickness=1, highlightbackground=p.border_focus, bd=0)
        shell.pack(fill=tk.BOTH, expand=True)
        container = tk.Frame(shell, bg=p.bg_surface, padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        self._build_header(container, top, p, rtl)
        self._build_source_and_presets(container, p, rtl)
        self._build_custom_and_output(container, p, rtl)
        self._build_footer(container, p, rtl)

        top.bind("<Escape>", lambda _e: self.hide())
        top.bind("<Return>", self._on_root_return)
        top.update_idletasks()
        dpi = get_dpi_scale(top)
        w, h = max(int(560 * dpi), int(top.winfo_reqwidth())), max(int(430 * dpi), int(top.winfo_reqheight()))
        px, py = clamp_popup_position(top, x - w // 6, y + 20, w, h, margin=12)
        top.geometry(f"{w}x{h}+{px}+{py}")
        top.deiconify()
        apply_popup_window_attributes(top, p, border_color=p.border_focus, corner_radius=14.0, acrylic=False, activate=True, show=True)
        top.focus_force()
        if self._ent_custom is not None:
            self._ent_custom.entry.focus_set()

    def _build_header(self, parent: tk.Frame, top: tk.Misc, p: Palette, rtl: bool) -> None:
        hdr = tk.Frame(parent, bg=p.bg_surface, cursor="fleur")
        hdr.pack(fill=tk.X, pady=(0, 10))
        lead, trail = ("right", "left") if rtl else ("left", "right")
        self._sparkle_photo = get_icon("sparkle", size=18, color=p.accent, dpi=get_dpi_scale(top), master=top)
        if self._sparkle_photo is not None:
            ic_lbl = tk.Label(hdr, image=self._sparkle_photo, bg=p.bg_surface, bd=0)
            ic_lbl.pack(side=lead, padx=(8, 0) if rtl else (0, 8))
            self._bind_drag(ic_lbl)
        title_lbl = tk.Label(
            hdr, text=t("ai.title", "دستیار هوشمند روان" if rtl else "Ravaan AI Command Palette"),
            bg=p.bg_surface, fg=p.fg, font=get_ui_font(size=11, bold=True, rtl=rtl),
        )
        title_lbl.pack(side=lead)
        self._bind_drag(hdr)
        self._bind_drag(title_lbl)

        _ex, char_n, word_n = summarize_source_preview(self._input_text)
        badge_txt = f"{word_n} کلمه ({char_n})" if rtl else f"{word_n}w · {char_n}c"
        FluentBadge(hdr, text=badge_txt, palette=p, parent_bg=p.bg_surface, rtl=rtl).pack(side=lead, padx=10)
        self._pill(hdr, "", "ghost", rtl, 26, 40, self.hide, icon="close").pack(side=trail)
        self._diff_btn = self._pill(hdr, t("ai.diff_btn", "مقایسه" if rtl else "Diff"), "ghost", rtl, 26, 74, self._toggle_diff)
        self._diff_btn.pack(side=trail, padx=6)

    def _build_source_and_presets(self, parent: tk.Frame, p: Palette, rtl: bool) -> None:
        excerpt, _c, _w = summarize_source_preview(self._input_text, max_chars=74)
        strip = tk.Frame(parent, bg=p.bg_elevated, highlightthickness=1, highlightbackground=p.border_subtle, padx=10, pady=6)
        strip.pack(fill=tk.X, pady=(0, 10))
        prefix = t("ai.source_label", "متن انتخابی:" if rtl else "Source:")
        tk.Label(
            strip, text=f"{prefix}  {excerpt}", bg=p.bg_elevated, fg=p.subtext,
            font=get_ui_font(size=8, rtl=rtl), anchor="e" if rtl else "w", justify="right" if rtl else "left",
        ).pack(fill=tk.X)

        self._chip_buttons, side = {}, ("right" if rtl else "left")
        wrap = tk.Frame(parent, bg=p.bg_surface)
        wrap.pack(fill=tk.X, pady=(0, 10))
        for spec_row in (AI_PRESET_SPECS[:4], AI_PRESET_SPECS[4:]):
            rfrm = tk.Frame(wrap, bg=p.bg_surface)
            rfrm.pack(fill=tk.X, pady=2)
            for aid, label_fa, label_en in spec_row:
                lbl = t(f"ai.preset_{aid}", label_fa if rtl else label_en)
                cw = max(84, len(lbl) * (6 if rtl else 7) + 28)
                chip = self._pill(rfrm, lbl, "secondary", rtl, 28, cw, lambda a=aid: self._trigger_action(a))
                chip.pack(side=side, padx=3)
                self._chip_buttons[aid] = chip

    def _build_custom_and_output(self, parent: tk.Frame, p: Palette, rtl: bool) -> None:
        bar = tk.Frame(parent, bg=p.bg_surface)
        bar.pack(fill=tk.X, pady=(0, 10))
        inp_side, btn_side = ("right", "left") if rtl else ("left", "right")
        self._ent_custom = FluentEntry(
            bar, placeholder=t("ai.custom_placeholder", "دستور دلخواه خود را بنویسید..." if rtl else "Write a custom AI instruction..."),
            palette=p, rtl=rtl, leading_icon="sparkle", clearable=True,
        )
        self._ent_custom.pack(side=inp_side, fill=tk.X, expand=True, padx=(8, 0) if rtl else (0, 8))
        self._ent_custom.entry.bind("<Return>", self._on_custom_entry_return)
        self._pill(bar, t("ai.run_btn", "اجرا" if rtl else "Run"), "primary", rtl, 30, 88, lambda: self._trigger_action("custom"), icon="sparkle").pack(side=btn_side)

        status_row = tk.Frame(parent, bg=p.bg_surface)
        status_row.pack(fill=tk.X, pady=(0, 4))
        self._status_var = tk.StringVar(value=t("ai.ready", "آماده — یک پیش‌تنظیم یا دستور دلخواه انتخاب کنید" if rtl else "Ready — choose a preset or enter custom prompt"))
        tk.Label(status_row, textvariable=self._status_var, bg=p.bg_surface, fg=p.subtext, font=get_ui_font(size=8, rtl=rtl), anchor="e" if rtl else "w").pack(side="right" if rtl else "left", fill=tk.X, expand=True)
        self._stop_btn = self._pill(status_row, t("ai.stop_btn", "توقف" if rtl else "Stop"), "danger", rtl, 22, 64, self._cancel_stream)

        self._shimmer_canvas = tk.Canvas(parent, height=3, bg=p.bg_interactive, highlightthickness=0, bd=0)
        self._shimmer_canvas.pack(fill=tk.X, pady=(0, 6))

        out_box = tk.Frame(parent, bg=p.bg_interactive, highlightthickness=1, highlightbackground=p.border_subtle, padx=8, pady=6)
        out_box.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        sb = ttk.Scrollbar(out_box, orient="vertical")
        self._txt_output = tk.Text(
            out_box, bg=p.bg_interactive, fg=p.fg, insertbackground=p.fg,
            selectbackground=p.highlight, selectforeground=p.highlight_fg,
            font=get_ui_font(size=10, rtl=rtl), height=7, wrap=tk.WORD, bd=0, relief="flat", highlightthickness=0, yscrollcommand=sb.set,
        )
        sb.configure(command=self._txt_output.yview)
        sb.pack(side="left" if rtl else "right", fill=tk.Y)
        self._txt_output.pack(side="right" if rtl else "left", fill=tk.BOTH, expand=True)
        is_dark = p.name in ("dark", "high_contrast")
        self._txt_output.tag_configure("diff_del", background="#4c2329" if is_dark else "#fde8ea", foreground="#ff9ea8" if is_dark else "#a61d24", overstrike=True)
        self._txt_output.tag_configure("diff_ins", background="#1c3d2d" if is_dark else "#e2f6ea", foreground="#7ee2a8" if is_dark else "#0f5132")

    def _build_footer(self, parent: tk.Frame, p: Palette, rtl: bool) -> None:
        footer = tk.Frame(parent, bg=p.bg_surface)
        footer.pack(fill=tk.X)
        prim_side, trail_side = ("right", "left") if rtl else ("left", "right")
        self._pill(footer, t("ai.replace_btn", "جایگزینی (Enter)" if rtl else "Replace (Enter)"), "primary", rtl, 32, 150, self._do_replace, icon="check").pack(side=prim_side)
        self._pill(footer, t("ai.copy_btn", "کپی" if rtl else "Copy"), "secondary", rtl, 32, 88, self._do_copy, icon="copy").pack(side=prim_side, padx=6)
        self._pill(footer, t("ai.regen_btn", "تولید مجدد" if rtl else "Regenerate"), "secondary", rtl, 32, 116, self._regenerate, icon="replace").pack(side=prim_side)
        self._pill(footer, t("ai.close_btn", "بستن (Esc)" if rtl else "Close (Esc)"), "ghost", rtl, 32, 102, self.hide, icon="close").pack(side=trail_side)

    def _bind_drag(self, widget: tk.Misc) -> None:
        widget.bind("<ButtonPress-1>", lambda e: setattr(self, "_drag_origin", (e.x_root - self._top.winfo_x(), e.y_root - self._top.winfo_y())) if self._top else None)
        widget.bind("<B1-Motion>", self._on_drag)

    def _on_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._top is not None and self._drag_origin is not None:
            self._top.geometry(f"+{event.x_root - self._drag_origin[0]}+{event.y_root - self._drag_origin[1]}")

    def _on_custom_entry_return(self, _e: tk.Event) -> str:  # type: ignore[type-arg]
        self._trigger_action("custom")
        return "break"

    def _on_root_return(self, event: tk.Event) -> str | None:  # type: ignore[type-arg]
        if self._ent_custom is not None and event.widget == self._ent_custom.entry:
            return None
        self._do_replace()
        return "break"

    def _cancel_stream(self) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()
        self._stop_shimmer()
        self._streaming = False
        if self._stop_btn is not None:
            self._stop_btn.pack_forget()
        if self._status_var is not None:
            self._status_var.set(t("ai.cancelled", "تولید متوقف شد." if is_rtl() else "Generation stopped."))

    def _trigger_action(self, action: str) -> None:
        custom_inst = ""
        if action == "custom" and self._ent_custom is not None:
            custom_inst = self._ent_custom.get().strip()
            if not custom_inst:
                self._ent_custom.entry.focus_set()
                return
        if self._cancel_event is not None:
            self._cancel_event.set()
        cancel_ev = threading.Event()
        self._cancel_event, self._last_action, self._last_custom = cancel_ev, action, custom_inst
        self._streaming, self._latest_output = True, ""
        for aid, btn in self._chip_buttons.items():
            btn.configure(variant="primary" if aid == action else "secondary")
        if self._txt_output is not None:
            self._txt_output.delete("1.0", tk.END)
        if self._status_var is not None:
            self._status_var.set(t("ai.streaming", "در حال نوشتن پاسخ..." if is_rtl() else "Generating response..."))
        if self._stop_btn is not None:
            self._stop_btn.pack(side="left" if is_rtl() else "right")
        self._start_shimmer()

        def _bg_call() -> None:
            try:
                if self.stream_callback is not None:
                    chunks: list[str] = []
                    for piece in self.stream_callback(action, self._input_text, custom_inst, cancel_ev):
                        if self._closed or cancel_ev.is_set():
                            break
                        chunks.append(piece)
                        self._schedule_ui(lambda p_txt=piece: self._append_stream_chunk(p_txt))
                    final_txt = "".join(chunks).strip()
                    self._schedule_ui(lambda: self._finish_stream(final_txt, ok=True, cancelled=cancel_ev.is_set()))
                else:
                    res = self.process_callback(action, self._input_text, custom_inst)
                    if not (self._closed or cancel_ev.is_set()):
                        self._schedule_ui(lambda: self._finish_stream(res, ok=True, cancelled=False))
            except Exception as exc:  # noqa: BLE001
                err_msg = str(exc)
                self._schedule_ui(lambda: self._finish_stream(err_msg, ok=False, cancelled=False))

        threading.Thread(target=_bg_call, daemon=True).start()

    def _schedule_ui(self, fn: Callable[[], None]) -> None:
        if self._closed or self._top is None:
            return
        try:
            if self._top.winfo_exists():
                self._top.after(0, fn)
        except Exception:
            pass

    def _append_stream_chunk(self, chunk: str) -> None:
        if self._closed or self._txt_output is None:
            return
        self._latest_output += chunk
        if not self._diff_mode:
            self._txt_output.insert(tk.END, chunk)
            self._txt_output.see(tk.END)

    def _finish_stream(self, text: str, *, ok: bool, cancelled: bool) -> None:
        if self._closed:
            return
        self._streaming = False
        self._stop_shimmer()
        if self._stop_btn is not None:
            self._stop_btn.pack_forget()
        if ok:
            self._latest_output = text or self._latest_output
            self._render_output_view()
            if self._status_var is not None:
                key = "ai.cancelled" if cancelled else "ai.done"
                fb = ("متوقف شد." if cancelled else "تکمیل شد.") if is_rtl() else ("Stopped." if cancelled else "Done.")
                self._status_var.set(t(key, fb))
        else:
            if self._txt_output is not None:
                self._txt_output.delete("1.0", tk.END)
                self._txt_output.insert(tk.END, text)
            if self._status_var is not None:
                self._status_var.set(f"{t('ai.error_prefix', 'خطا:' if is_rtl() else 'Error:')} {text}")

    def _toggle_diff(self) -> None:
        self._diff_mode = not self._diff_mode
        if self._diff_btn is not None:
            self._diff_btn.configure(variant="primary" if self._diff_mode else "ghost")
        if not self._streaming:
            self._render_output_view()

    def _render_output_view(self) -> None:
        if self._txt_output is None:
            return
        self._txt_output.delete("1.0", tk.END)
        out = self._latest_output
        if self._diff_mode and out:
            for op, span in compute_word_diff(self._input_text.strip(), out.strip()):
                self._txt_output.insert(tk.END, span) if op == "equal" else self._txt_output.insert(tk.END, span, "diff_del" if op == "del" else "diff_ins")
        elif out:
            self._txt_output.insert(tk.END, out)

    def _start_shimmer(self) -> None:
        self._shimmer_pos = 0.0
        self._tick_shimmer()

    def _stop_shimmer(self) -> None:
        if self._shimmer_job is not None and self._top is not None:
            try:
                self._top.after_cancel(self._shimmer_job)
            except Exception:
                pass
            self._shimmer_job = None
        if self._shimmer_canvas is not None:
            try:
                self._shimmer_canvas.delete("all")
            except Exception:
                pass

    def _tick_shimmer(self) -> None:
        if not self._streaming or self._closed or self._shimmer_canvas is None or self._top is None:
            return
        c, w = self._shimmer_canvas, max(120, int(self._shimmer_canvas.winfo_width() or 500))
        seg = max(60, w // 4)
        x1 = int((self._shimmer_pos % 1.0) * (w + seg)) - seg
        c.delete("all")
        c.create_rectangle(max(0, x1), 0, min(w, x1 + seg), 3, fill=self._palette.accent, outline="")
        self._shimmer_pos += 0.055
        try:
            self._shimmer_job = self._top.after(35, self._tick_shimmer)
        except Exception:
            self._shimmer_job = None

    def _regenerate(self) -> None:
        self._trigger_action(self._last_action or "rewrite")

    def _current_clean_output(self) -> str:
        if self._diff_mode:
            return self._latest_output.strip()
        return self._txt_output.get("1.0", tk.END).strip() if self._txt_output is not None else self._latest_output.strip()

    def _do_replace(self) -> None:
        text = self._current_clean_output()
        if text:
            self.hide()
            self.on_replace(text)

    def _do_copy(self) -> None:
        text = self._current_clean_output()
        if text:
            self.hide()
            self.on_copy(text)

    def hide(self) -> None:
        """Close the AI popup safely and cancel any active stream."""
        self._closed, self._streaming = True, False
        if self._cancel_event is not None:
            self._cancel_event.set()
            self._cancel_event = None
        self._stop_shimmer()
        self._sparkle_photo = None
        if self._top is not None:
            try:
                if self._top.winfo_exists():
                    self._top.destroy()
            except Exception:
                pass
            self._top = None
