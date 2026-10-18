"""Save dialog for recorded macro snippets (M23)."""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from ravan.core.config import Snippet
from ravan.core.i18n import is_rtl, t
from ravan.core.macro import serialize_macro

log = logging.getLogger(__name__)


class MacroSaveDialog:
    """Dialog to name trigger, set timing option, and save a recorded macro."""

    def __init__(
        self,
        parent: tk.Tk | None,
        events: list[dict[str, Any]],
        existing_snippets: list[Snippet],
        on_save: Callable[[Snippet], None],
    ) -> None:
        self.events = events
        self.existing_snippets = existing_snippets
        self.on_save = on_save
        self._root: tk.Toplevel | None = None
        self._parent = parent

    def show(self) -> None:
        rtl = is_rtl()
        align = "e" if rtl else "w"

        top = tk.Toplevel(self._parent)
        self._root = top
        top.title(t("macro.dialog_title", "Save Keystroke Macro"))
        top.geometry("460x280")
        top.resizable(False, False)
        top.attributes("-topmost", True)

        # Center dialog
        top.update_idletasks()
        try:
            sw = top.winfo_screenwidth()
            sh = top.winfo_screenheight()
            top.geometry(f"+{(sw - 460) // 2}+{(sh - 280) // 2}")
        except Exception:
            pass

        frm = ttk.Frame(top, padding=16)
        frm.pack(fill="both", expand=True)

        # Header with event count
        count = len(self.events)
        ttk.Label(
            frm,
            text=t("macro.header", "Macro Recorded ({count} keystrokes)", count=count),
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor=align, pady=(0, 8))

        # Trigger field
        ttk.Label(frm, text=t("macro.trigger_label", "Snippet Trigger (e.g. //m1):")).pack(
            anchor=align, pady=(4, 2)
        )

        # Suggest default trigger
        default_trigger = "//m1"
        existing_triggers = {s.trigger for s in self.existing_snippets}
        idx = 1
        while default_trigger in existing_triggers:
            idx += 1
            default_trigger = f"//m{idx}"

        self._trigger_var = tk.StringVar(value=default_trigger)
        entry = ttk.Entry(frm, textvariable=self._trigger_var, width=32)
        entry.pack(anchor=align, pady=(0, 8))
        entry.focus_set()
        entry.select_range(0, "end")

        # Preserve timings checkbox
        self._timings_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frm,
            text=t("macro.preserve_timings", "Preserve playback delays / timings"),
            variable=self._timings_var,
        ).pack(anchor=align, pady=(4, 8))

        # Security / Elevated app warning box
        warn_box = tk.Label(
            frm,
            text=t(
                "macro.elevated_warning",
                "⚠️ Notice: Some games and elevated/admin applications block synthetic keystroke injection.",
            ),
            wraplength=410,
            justify="right" if rtl else "left",
            foreground="#b86200",
            font=("Segoe UI", 8),
        )
        warn_box.pack(anchor=align, pady=(4, 12))

        # Button row
        btn_frm = ttk.Frame(frm)
        btn_frm.pack(fill="x", side="bottom")

        def _do_save() -> None:
            trigger = self._trigger_var.get().strip()
            if not trigger:
                entry.focus_set()
                return
            macro_str = serialize_macro(
                self.events, preserve_timing=self._timings_var.get()
            )
            snippet = Snippet(trigger=trigger, replacement=macro_str, enabled=True)
            self.on_save(snippet)
            top.destroy()

        save_btn = ttk.Button(
            btn_frm, text=t("macro.save_btn", "Save Macro"), command=_do_save
        )
        cancel_btn = ttk.Button(
            btn_frm, text=t("common.cancel", "Cancel"), command=top.destroy
        )

        if rtl:
            save_btn.pack(side="left", padx=(0, 6))
            cancel_btn.pack(side="left")
        else:
            save_btn.pack(side="right", padx=(6, 0))
            cancel_btn.pack(side="right")

        top.bind("<Return>", lambda _e: _do_save())
        top.bind("<Escape>", lambda _e: top.destroy())
