"""Interactive modal popup dialog for snippet placeholder forms (Snippets 3.0)."""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from ravan.core.i18n import t
from ravan.core.snippet_forms import FormController, FormFieldSpec
from ravan.platform import winapi as w
from ravan.ui.theme import apply_popup_window_attributes, get_active_palette, get_ui_font

log = logging.getLogger(__name__)


class QuickFormDialog:
    """Mini modal dialog prompting user for snippet placeholder values."""

    def __init__(
        self,
        parent: tk.Misc | None,
        template: str,
        fields: list[FormFieldSpec] | None = None,
        snippet_trigger: str = "",
        on_submit: Callable[[str], None] | None = None,
        theme_mode: str = "auto",
    ) -> None:
        self.parent = parent
        self.template = template
        self.snippet_trigger = snippet_trigger
        self.on_submit = on_submit
        self.theme_mode = theme_mode
        self.controller = FormController(template, snippet_trigger=snippet_trigger)
        self.fields = fields or self.controller.fields
        self._top: tk.Toplevel | None = None
        self._entries: dict[str, tk.Widget] = {}
        self._err_labels: dict[str, tk.Label] = {}
        self._target_hwnd: int | None = None
        self._first_widget: tk.Widget | None = None

    def show(self) -> None:
        if w and w.user32:
            try:
                self._target_hwnd = int(w.user32.GetForegroundWindow() or 0)
            except Exception:
                self._target_hwnd = None

        p = get_active_palette(self.theme_mode)
        top = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self._top = top
        top.title(t("form_dialog.title", "Ravaan — Fill Snippet Form"))
        top.attributes("-topmost", True)
        top.configure(bg=p.bg)
        try:
            top.attributes("-alpha", p.alpha)
        except tk.TclError:
            pass

        apply_popup_window_attributes(top, p)

        container = tk.Frame(top, bg=p.bg, padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        header_font = get_ui_font(size=10, bold=True, rtl=True)
        lbl_header = tk.Label(
            container,
            text=t("form_dialog.header", "Please fill in the snippet fields:"),
            bg=p.bg,
            fg=p.fg,
            font=header_font,
            anchor="e",
        )
        lbl_header.pack(fill=tk.X, pady=(0, 10))

        label_font = get_ui_font(size=9, bold=False, rtl=True)
        entry_font = get_ui_font(size=9, bold=False)

        widgets_in_order: list[tk.Widget] = []

        for fld in self.fields:
            field_box = tk.Frame(container, bg=p.bg)
            field_box.pack(fill=tk.X, pady=3)

            row = tk.Frame(field_box, bg=p.bg)
            row.pack(fill=tk.X)

            label_text = f"{fld.label}:"
            if fld.remember:
                label_text = f"★ {label_text}"

            lbl = tk.Label(
                row,
                text=label_text,
                bg=p.bg,
                fg=p.subtext,
                font=label_font,
                width=16,
                anchor="e",
            )
            lbl.pack(side=tk.RIGHT, padx=(6, 0))

            widget: tk.Widget
            if fld.field_type == "choice" and fld.choices:
                cb = ttk.Combobox(row, values=fld.choices, font=entry_font)
                cb.set(fld.default or fld.choices[0])
                cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
                cb.bind("<Return>", lambda _e: self._submit())
                widget = cb
            elif fld.field_type == "multiline":
                txt = tk.Text(
                    row,
                    height=3,
                    wrap="word",
                    bg=p.card_bg,
                    fg=p.fg,
                    insertbackground=p.fg,
                    font=entry_font,
                    bd=1,
                    relief=tk.SOLID,
                )
                txt.insert("1.0", fld.default)
                txt.pack(side=tk.LEFT, fill=tk.X, expand=True)
                txt.bind("<Control-Return>", lambda _e: self._submit())
                widget = txt
            else:
                ent = tk.Entry(
                    row,
                    bg=p.card_bg,
                    fg=p.fg,
                    insertbackground=p.fg,
                    font=entry_font,
                    bd=1,
                    relief=tk.SOLID,
                )
                ent.insert(0, fld.default)
                ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
                ent.bind("<Return>", lambda _e: self._submit())
                widget = ent

            err_lbl = tk.Label(
                field_box,
                text="",
                bg=p.bg,
                fg="#fa5252",
                font=get_ui_font(size=8, bold=False, rtl=True),
                anchor="e",
            )
            err_lbl.pack(fill=tk.X, pady=(1, 0))
            self._err_labels[fld.name] = err_lbl

            self._entries[fld.name] = widget
            widgets_in_order.append(widget)
            if self._first_widget is None:
                self._first_widget = widget

        # Set up Tab / Shift-Tab cycling between widgets
        for i, w_item in enumerate(widgets_in_order):
            nxt = widgets_in_order[(i + 1) % len(widgets_in_order)]
            prv = widgets_in_order[(i - 1) % len(widgets_in_order)]
            w_item.bind("<Tab>", lambda e, target=nxt: self._cycle_focus(e, target))
            w_item.bind("<Shift-Tab>", lambda e, target=prv: self._cycle_focus(e, target))

        btn_row = tk.Frame(container, bg=p.bg)
        btn_row.pack(fill=tk.X, pady=(12, 0))

        btn_ok = tk.Button(
            btn_row,
            text=t("form_dialog.btn_confirm", "Confirm & Insert (Enter)"),
            bg=p.highlight,
            fg=p.highlight_fg,
            font=get_ui_font(size=9, bold=True, rtl=True),
            padx=12,
            pady=4,
            command=self._submit,
            relief=tk.FLAT,
        )
        btn_ok.pack(side=tk.LEFT)

        btn_cancel = tk.Button(
            btn_row,
            text=t("form_dialog.btn_cancel", "Cancel (Esc)"),
            bg=p.card_bg,
            fg=p.subtext,
            font=get_ui_font(size=9, bold=False, rtl=True),
            padx=8,
            pady=4,
            command=self._cancel,
            relief=tk.FLAT,
        )
        btn_cancel.pack(side=tk.RIGHT)

        top.bind("<Escape>", lambda _e: self._cancel())

        self._center()

        if self._first_widget:
            self._first_widget.focus_set()

    def _cycle_focus(self, event: tk.Event[tk.Widget], target: tk.Widget) -> str:
        target.focus_set()
        return "break"

    def _center(self) -> None:
        if not self._top:
            return
        self._top.update_idletasks()
        w_px = max(self._top.winfo_width(), 440)
        h_px = self._top.winfo_height()
        sx = (self._top.winfo_screenwidth() - w_px) // 2
        sy = (self._top.winfo_screenheight() - h_px) // 3
        self._top.geometry(f"{w_px}x{h_px}+{sx}+{sy}")

    def _read_entries(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for name, widget in self._entries.items():
            if isinstance(widget, ttk.Combobox):
                values[name] = widget.get().strip()
            elif isinstance(widget, tk.Entry):
                values[name] = widget.get().strip()
            elif isinstance(widget, tk.Text):
                values[name] = widget.get("1.0", tk.END).rstrip("\n")
        return values

    def _submit(self) -> None:
        values = self._read_entries()
        p = get_active_palette(self.theme_mode)

        # Clear previous validation highlights
        for name, widget in self._entries.items():
            if isinstance(widget, (tk.Entry, tk.Text)):
                widget.configure(bg=p.card_bg)
            if name in self._err_labels:
                self._err_labels[name].configure(text="")

        for k, v in values.items():
            self.controller.set_value(k, v)

        is_valid, rendered_or_err = self.controller.confirm()
        if not is_valid:
            # Highlight errors
            first_focused = False
            for fld_name, err_msg in self.controller.errors.items():
                if fld_name in self._entries:
                    w_err = self._entries[fld_name]
                    if isinstance(w_err, (tk.Entry, tk.Text)):
                        w_err.configure(bg="#ffe3e3")
                    if not first_focused:
                        w_err.focus_set()
                        first_focused = True
                if fld_name in self._err_labels:
                    self._err_labels[fld_name].configure(text=err_msg)
            return

        self._restore_focus_and_close()
        if self.on_submit:
            self.on_submit(rendered_or_err)

    def _restore_focus_and_close(self) -> None:
        if self._top:
            try:
                self._top.destroy()
            except Exception:  # noqa: BLE001
                pass
            self._top = None

        if self._target_hwnd and w and w.user32:
            try:
                w.user32.SetForegroundWindow(self._target_hwnd)
            except Exception:  # noqa: BLE001
                pass

    def _cancel(self) -> None:
        self.controller.cancel()
        self._restore_focus_and_close()
