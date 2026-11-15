"""Fluent 2 interactive controls: Toggle Switches, Pill Buttons, Segmented Controls, and Inputs."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from functools import lru_cache
from typing import Any

from PIL import Image, ImageDraw, ImageTk

from ravan.ui.theme_palettes import Palette, get_active_palette, get_dpi_scale, get_ui_font
from ravan.ui.widgets.icons import get_icon
from ravan.ui.widgets.surface import _rgba, render_rounded_surface


@lru_cache(maxsize=256)
def render_toggle_switch_image(
    is_on: bool, hovered: bool, width: int = 40, height: int = 22,
    accent_hex: str = "#8ab4f8", off_bg_hex: str = "#1e1f22", border_hex: str = "#5f6368",
    thumb_on_hex: str = "#202124", thumb_off_hex: str = "#9aa0a6", parent_bg_hex: str = "#292b2f", rtl: bool = False,
) -> Image.Image:
    """Render a 2x-supersampled anti-aliased pill toggle switch with circular thumb."""
    w, h = max(32, int(width)), max(18, int(height))
    sw, sh = w * 2, h * 2
    img = Image.new("RGBA", (sw, sh), _rgba(parent_bg_hex, 255))
    draw = ImageDraw.Draw(img)
    r = (sh - 4) // 2

    if is_on:
        draw.rounded_rectangle([2, 2, sw - 3, sh - 3], radius=r, fill=_rgba(accent_hex, 255 if not hovered else 230))
        thumb_c, thumb_r, on_left = _rgba(thumb_on_hex, 255), int(sh * (0.30 if not hovered else 0.33)), rtl
    else:
        outline_c = _rgba(accent_hex if hovered else border_hex, 255)
        draw.rounded_rectangle([2, 2, sw - 3, sh - 3], radius=r, fill=_rgba(off_bg_hex, 255), outline=outline_c, width=3)
        thumb_c, thumb_r, on_left = _rgba(thumb_off_hex, 255), int(sh * (0.25 if not hovered else 0.28)), not rtl

    cy = sh // 2
    cx = (sh // 2 + 2) if on_left else (sw - sh // 2 - 2)
    draw.ellipse([cx - thumb_r, cy - thumb_r, cx + thumb_r, cy + thumb_r], fill=thumb_c)
    return img.resize((w, h), Image.Resampling.LANCZOS)


class FluentToggleSwitch(tk.Frame):
    """Fluent 2 pill toggle switch bound two-way to a `tk.BooleanVar`."""

    def __init__(
        self, parent: tk.Misc, text: str = "", variable: tk.BooleanVar | None = None,
        command: Callable[[], Any] | None = None, subtitle: str = "",
        palette: Palette | None = None, rtl: bool = False, bg_override: str | None = None,
    ) -> None:
        pal = palette or get_active_palette("auto")
        bg_col = bg_override or pal.bg_surface
        super().__init__(parent, bg=bg_col, bd=0, highlightthickness=0)
        self.palette, self.rtl, self._bg_col, self.command = pal, rtl, bg_col, command
        self.variable = variable if variable is not None else tk.BooleanVar(master=self, value=False)
        self._hovered = False
        self._photo: ImageTk.PhotoImage | None = None

        row_frm = tk.Frame(self, bg=bg_col)
        row_frm.pack(fill="x", expand=True)
        lead_side = "right" if rtl else "left"
        anchor, justify = ("e", "right") if rtl else ("w", "left")

        self._sw_canvas = tk.Canvas(row_frm, width=40, height=22, bg=bg_col, bd=0, highlightthickness=0, cursor="hand2")
        self._sw_canvas.pack(side=lead_side, padx=(8, 0) if rtl else (0, 10), pady=2)
        self._lbl = tk.Label(row_frm, text=text, bg=bg_col, fg=pal.fg, font=get_ui_font(size=9, bold=False, rtl=rtl), anchor=anchor, justify=justify, cursor="hand2")
        self._lbl.pack(side=lead_side, fill="x", expand=True)

        if subtitle:
            tk.Label(self, text=subtitle, bg=bg_col, fg=pal.subtext, font=get_ui_font(size=8, rtl=rtl), anchor=anchor, justify=justify).pack(fill="x", anchor=anchor, padx=(0, 48) if rtl else (50, 0), pady=(0, 2))

        for w in (self._sw_canvas, self._lbl):
            w.bind("<Button-1>", self._on_click)
            w.bind("<Enter>", lambda _e: self._set_hover(True))
            w.bind("<Leave>", lambda _e: self._set_hover(False))
        self.variable.trace_add("write", lambda *_: self._redraw())
        self._redraw()

    def _on_click(self, _event: Any = None) -> str:
        self.variable.set(not bool(self.variable.get()))
        if callable(self.command):
            self.command()
        return "break"

    def _set_hover(self, state: bool) -> None:
        self._hovered = state
        self._redraw()

    def _redraw(self) -> None:
        if not self._sw_canvas.winfo_exists():
            return
        pil_img = render_toggle_switch_image(
            is_on=bool(self.variable.get()), hovered=self._hovered, width=40, height=22,
            accent_hex=self.palette.highlight, off_bg_hex=self.palette.bg_interactive,
            border_hex=self.palette.subtext, thumb_on_hex=self.palette.highlight_fg,
            thumb_off_hex=self.palette.subtext, parent_bg_hex=self._bg_col, rtl=self.rtl,
        )
        try:
            self._photo = ImageTk.PhotoImage(pil_img, master=self._sw_canvas)
            self._sw_canvas.delete("all")
            self._sw_canvas.create_image(20, 11, image=self._photo)
        except Exception:
            pass


class FluentPillButton(tk.Canvas):
    """2x-AA Pillow-rendered pill button with primary, secondary, ghost, and danger variants."""

    def __init__(
        self, parent: tk.Misc, text: str = "", command: Callable[[], Any] | None = None,
        variant: str = "secondary", icon: str | None = None, palette: Palette | None = None,
        rtl: bool = False, parent_bg: str | None = None, width: int | None = None, height: int = 30, state: str = "normal",
    ) -> None:
        pal = palette or get_active_palette("auto")
        self.palette, self.rtl = pal, rtl
        self._text, self._command, self._variant, self._icon_name, self._state = text, command, variant, icon, state
        self._hovered = self._pressed = self._focused = False
        self._parent_bg = parent_bg or pal.bg_surface
        self._photo: ImageTk.PhotoImage | None = None
        self._icon_photo: ImageTk.PhotoImage | None = None

        est_w = width or max(74, len(text) * 7 + (24 if icon else 0) + 28)
        super().__init__(parent, width=est_w, height=height, bg=self._parent_bg, bd=0, highlightthickness=0, takefocus=1, cursor="hand2" if state != "disabled" else "arrow")
        self._req_w, self._req_h = est_w, height

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<FocusIn>", lambda _e: self._set_focus(True))
        self.bind("<FocusOut>", lambda _e: self._set_focus(False))
        self.bind("<Return>", lambda _e: self.invoke())
        self.bind("<space>", lambda _e: self.invoke())
        self.bind("<Configure>", lambda e: self._redraw(e.width, e.height))
        self._redraw(est_w, height)

    def invoke(self) -> Any:
        return self._command() if (self._state != "disabled" and callable(self._command)) else None

    def configure(self, cnf: dict[str, Any] | None = None, **kw: Any) -> Any:  # type: ignore[override]
        opts = {**(cnf or {}), **kw}
        needs_redraw = False
        if "state" in opts:
            self._state = str(opts.pop("state"))
            super().configure(cursor="hand2" if self._state != "disabled" else "arrow")
            needs_redraw = True
        if "text" in opts:
            self._text = str(opts.pop("text"))
            needs_redraw = True
        if "command" in opts:
            self._command = opts.pop("command")
        if "variant" in opts:
            self._variant = str(opts.pop("variant"))
            needs_redraw = True
        for k in ("bg", "fg", "activebackground", "activeforeground", "font", "highlightbackground"):
            opts.pop(k, None)
        res = super().configure(**opts) if opts else None
        if needs_redraw:
            self._refresh()
        return res

    config = configure

    def _refresh(self) -> None:
        self._redraw(self.winfo_width() or self._req_w, self.winfo_height() or self._req_h)

    def _on_enter(self, _e: Any = None) -> None:
        if self._state != "disabled":
            self._hovered = True
            self._refresh()

    def _on_leave(self, _e: Any = None) -> None:
        self._hovered = self._pressed = False
        self._refresh()

    def _on_press(self, _e: Any = None) -> None:
        if self._state != "disabled":
            self._pressed = True
            self._refresh()

    def _on_release(self, _e: Any = None) -> None:
        was_pressed = self._pressed
        self._pressed = False
        self._refresh()
        if was_pressed and self._hovered and self._state != "disabled":
            self.invoke()

    def _set_focus(self, focused: bool) -> None:
        self._focused = focused
        self._refresh()

    def _resolve_colors(self) -> tuple[str, str, str]:
        p = self.palette
        if self._state == "disabled":
            return p.bg_interactive, p.subtext, p.border_subtle
        if self._variant == "primary":
            fill = p.accent_hover if (self._hovered or self._pressed) else p.highlight
            return fill, p.highlight_fg, (p.border_focus if self._focused else fill)
        if self._variant == "danger":
            return (p.danger if self._hovered else p.button_bg), ("#ffffff" if self._hovered else p.danger), p.danger
        if self._variant == "ghost":
            return (p.button_hover if self._hovered else self._parent_bg), p.fg, (p.border_focus if self._focused else "")
        fill = p.button_hover if (self._hovered or self._pressed) else p.button_bg
        return fill, p.fg, (p.border_focus if self._focused else p.border_subtle)

    def _redraw(self, w: int, h: int) -> None:
        if not self.winfo_exists():
            return
        w, h = max(40, int(w)), max(22, int(h))
        fill_hex, fg_hex, border_hex = self._resolve_colors()
        self.delete("all")
        pil_img = render_rounded_surface(w, h, radius=min(10, h // 2), fill_hex=fill_hex, border_hex=border_hex, bg_hex=self._parent_bg)
        try:
            self._photo = ImageTk.PhotoImage(pil_img, master=self)
            self.create_image(w // 2, h // 2, image=self._photo)
        except Exception:
            pass

        cx, cy = w // 2, h // 2
        font_spec = get_ui_font(size=9, bold=self._variant == "primary", rtl=self.rtl)
        if self._icon_name:
            self._icon_photo = get_icon(self._icon_name, size=14, color=fg_hex, dpi=get_dpi_scale(self), master=self)
            if self._icon_photo is not None and self._text:
                self.create_image((w - 18) if self.rtl else 18, cy, image=self._icon_photo)
                self.create_text(cx + (-10 if self.rtl else 10), cy, text=self._text, fill=fg_hex, font=font_spec)
                return
            if self._icon_photo is not None:
                self.create_image(cx, cy, image=self._icon_photo)
                return
        self.create_text(cx, cy, text=self._text, fill=fg_hex, font=font_spec)


class FluentSegmentedControl(tk.Frame):
    """Pill segmented selector bound to a `tk.StringVar`."""

    def __init__(
        self, parent: tk.Misc, options: list[tuple[str, str]], variable: tk.StringVar | None = None,
        command: Callable[[str], Any] | None = None, palette: Palette | None = None, rtl: bool = False,
    ) -> None:
        pal = palette or get_active_palette("auto")
        super().__init__(parent, bg=pal.bg_interactive, bd=0, highlightthickness=1, highlightbackground=pal.border_subtle, padx=2, pady=2)
        self.palette, self.rtl, self.options, self.command = pal, rtl, options, command
        self.variable = variable or tk.StringVar(master=self, value=options[0][0] if options else "")
        self._buttons: dict[str, FluentPillButton] = {}

        for val, label in (list(reversed(options)) if rtl else list(options)):
            btn = FluentPillButton(
                self, text=label, variant="primary" if self.variable.get() == val else "ghost",
                palette=pal, rtl=rtl, parent_bg=pal.bg_interactive, height=26, command=lambda v=val: self._select(v),
            )
            btn.pack(side="left", padx=1)
            self._buttons[val] = btn
        self.variable.trace_add("write", lambda *_: self._sync())

    def _select(self, val: str) -> None:
        self.variable.set(val)
        if callable(self.command):
            self.command(val)

    def _sync(self) -> None:
        cur = self.variable.get()
        for val, btn in self._buttons.items():
            btn.configure(variant="primary" if val == cur else "ghost")


class FluentEntry(tk.Frame):
    """Rounded Fluent input container with proper placeholder lifecycle that clears cleanly on focus."""

    def __init__(
        self, parent: tk.Misc, textvariable: tk.StringVar | None = None, placeholder: str = "",
        width: int = 26, palette: Palette | None = None, rtl: bool = False,
        leading_icon: str | None = None, clearable: bool = False, password: bool = False,
    ) -> None:
        pal = palette or get_active_palette("auto")
        super().__init__(parent, bg=pal.bg_interactive, bd=0, highlightthickness=1, highlightbackground=pal.border_subtle, highlightcolor=pal.border_focus, padx=8, pady=4)
        self.palette, self.rtl, self.placeholder = pal, rtl, placeholder
        self._showing_placeholder = self._password_visible = self._internal_sync = False
        self._password, self._ext_var = password, textvariable
        side, opp_side = ("right", "left") if rtl else ("left", "right")
        dpi = get_dpi_scale(self)

        if leading_icon:
            self._lead_photo = get_icon(leading_icon, size=14, color=pal.subtext, dpi=dpi, master=self)
            if self._lead_photo is not None:
                tk.Label(self, image=self._lead_photo, bg=pal.bg_interactive, bd=0).pack(side=side, padx=(4, 0) if rtl else (0, 6))

        self.entry = tk.Entry(
            self, width=width, bg=pal.bg_interactive, fg=pal.fg, insertbackground=pal.fg,
            selectbackground=pal.highlight, selectforeground=pal.highlight_fg, bd=0, relief="flat",
            highlightthickness=0, font=get_ui_font(size=9, rtl=rtl), justify="right" if rtl else "left", show="•" if password else "",
        )
        self.entry.pack(side=side, fill="x", expand=True)

        if clearable:
            self._clr_photo = get_icon("close", size=12, color=pal.subtext, dpi=dpi, master=self)
            clr_btn = tk.Label(self, image=self._clr_photo if self._clr_photo else None, text="" if self._clr_photo else "✕", bg=pal.bg_interactive, fg=pal.subtext, cursor="hand2", padx=2)
            clr_btn.pack(side=opp_side, padx=(0, 2) if rtl else (2, 0))
            clr_btn.bind("<Button-1>", lambda _e: self.clear())

        if password:
            self._eye_photo = get_icon("eye", size=14, color=pal.subtext, dpi=dpi, master=self)
            self._eye_btn = tk.Label(self, image=self._eye_photo if self._eye_photo else None, text="" if self._eye_photo else "👁", bg=pal.bg_interactive, fg=pal.subtext, cursor="hand2", padx=2)
            self._eye_btn.pack(side=opp_side, padx=2)
            self._eye_btn.bind("<Button-1>", lambda _e: self.toggle_password())

        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<KeyRelease>", self._on_key_release)

        if self._ext_var is not None:
            init_val = self._ext_var.get()
            if init_val:
                self.entry.insert(0, init_val)
            else:
                self._show_placeholder()
            self._ext_var.trace_add("write", self._on_ext_var_changed)
        else:
            self._show_placeholder()

    def _show_placeholder(self) -> None:
        if not self.placeholder:
            return
        self._showing_placeholder = True
        self.entry.configure(fg=self.palette.subtext, show="")
        self.entry.delete(0, tk.END)
        self.entry.insert(0, self.placeholder)

    def _hide_placeholder(self) -> None:
        if self._showing_placeholder:
            self._showing_placeholder = False
            self.entry.delete(0, tk.END)
            self.entry.configure(fg=self.palette.fg, show="" if (not self._password or self._password_visible) else "•")

    def _on_focus_in(self, _e: Any = None) -> None:
        self.configure(highlightbackground=self.palette.border_focus)
        self._hide_placeholder()

    def _on_focus_out(self, _e: Any = None) -> None:
        self.configure(highlightbackground=self.palette.border_subtle)
        if not self.entry.get():
            self._show_placeholder()

    def _on_key_release(self, _e: Any = None) -> None:
        if self._ext_var is not None and not self._showing_placeholder:
            self._internal_sync = True
            try:
                self._ext_var.set(self.entry.get())
            finally:
                self._internal_sync = False

    def _on_ext_var_changed(self, *_args: Any) -> None:
        if self._internal_sync or self._ext_var is None:
            return
        val = self._ext_var.get()
        if not val:
            if self.focus_get() != self.entry:
                self._show_placeholder()
            else:
                self._showing_placeholder = False
                self.entry.delete(0, tk.END)
        else:
            self._hide_placeholder()
            self.entry.delete(0, tk.END)
            self.entry.insert(0, val)

    def get(self) -> str:
        """Return actual user input, never the placeholder string."""
        return "" if self._showing_placeholder else self.entry.get()

    def set(self, value: str) -> None:
        if self._ext_var is not None:
            self._ext_var.set(value)
        elif value:
            self._hide_placeholder()
            self.entry.delete(0, tk.END)
            self.entry.insert(0, value)
        else:
            self.entry.delete(0, tk.END)
            self._show_placeholder()

    def clear(self) -> None:
        self.set("")

    def toggle_password(self) -> None:
        if self._password:
            self._password_visible = not self._password_visible
            if not self._showing_placeholder:
                self.entry.configure(show="" if self._password_visible else "•")
