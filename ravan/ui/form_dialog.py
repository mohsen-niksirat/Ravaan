"""Quick modal form dialog for interactive snippet placeholders."""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from ravan.core.snippet import FormField, render_form_template
from ravan.ui.theme import apply_popup_window_attributes, get_active_palette, get_ui_font

log = logging.getLogger(__name__)


class QuickFormDialog:
    """Mini modal dialog prompting user for snippet variable values."""

    def __init__(
        self,
        parent: tk.Misc | None,
        template: str,
        fields: list[FormField],
        on_submit: Callable[[str], None],
        theme_mode: str = "auto",
    ) -> None:
        self.parent = parent
        self.template = template
        self.fields = fields
        self.on_submit = on_submit
        self.theme_mode = theme_mode
        self._top: tk.Toplevel | None = None
        self._entries: dict[str, tk.Widget] = {}

    def show(self) -> None:
        p = get_active_palette(self.theme_mode)
        top = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self._top = top
        top.title("Ravaan — تکمیل فیلدهای فرم")
        top.attributes("-topmost", True)
        top.configure(bg=p.bg)
        try:
            top.attributes("-alpha", p.alpha)
        except tk.TclError:
            pass

        apply_popup_window_attributes(top, p)

        container = tk.Frame(top, bg=p.bg, padx=16, pady=16)
        container.pack(fill=tk.BOTH, expand=True)

        header_font = get_ui_font(size=11, bold=True, rtl=True)
        lbl_header = tk.Label(
            container,
            text="مقادیر فیلدهای اسنیپت را وارد کنید:",
            bg=p.bg,
            fg=p.fg,
            font=header_font,
            anchor="e",
        )
        lbl_header.pack(fill=tk.X, pady=(0, 10))

        label_font = get_ui_font(size=9, bold=False, rtl=True)
        entry_font = get_ui_font(size=10, bold=False)

        first_widget: tk.Widget | None = None

        for fld in self.fields:
            row = tk.Frame(container, bg=p.bg)
            row.pack(fill=tk.X, pady=4)

            lbl = tk.Label(
                row,
                text=f"{fld.label}:",
                bg=p.bg,
                fg=p.subtext,
                font=label_font,
                width=16,
                anchor="e",
            )
            lbl.pack(side=tk.RIGHT, padx=(6, 0))

            if fld.field_type == "choice" and fld.choices:
                cb = ttk.Combobox(row, values=fld.choices, font=entry_font)
                cb.set(fld.default or fld.choices[0])
                cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self._entries[fld.name] = cb
                if first_widget is None:
                    first_widget = cb
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
                self._entries[fld.name] = ent
                if first_widget is None:
                    first_widget = ent

        btn_row = tk.Frame(container, bg=p.bg)
        btn_row.pack(fill=tk.X, pady=(14, 0))

        btn_ok = tk.Button(
            btn_row,
            text="تأیید و درج (Enter)",
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
            text="انصراف (Esc)",
            bg=p.card_bg,
            fg=p.subtext,
            font=get_ui_font(size=9, bold=False, rtl=True),
            padx=8,
            pady=4,
            command=self._cancel,
            relief=tk.FLAT,
        )
        btn_cancel.pack(side=tk.RIGHT)

        top.bind("<Return>", lambda e: self._submit())
        top.bind("<Escape>", lambda e: self._cancel())

        if first_widget:
            first_widget.focus_set()

    def _submit(self) -> None:
        values: dict[str, str] = {}
        for name, widget in self._entries.items():
            if isinstance(widget, ttk.Combobox):
                values[name] = widget.get()
            elif isinstance(widget, tk.Entry):
                values[name] = widget.get()

        rendered = render_form_template(self.template, values)
        if self._top:
            self._top.destroy()
            self._top = None

        self.on_submit(rendered)

    def _cancel(self) -> None:
        if self._top:
            self._top.destroy()
            self._top = None
