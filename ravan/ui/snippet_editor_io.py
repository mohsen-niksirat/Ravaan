"""JSON import, export, toolbar helpers, and validation handlers for Snippet Editor."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, messagebox, ttk

from ravan.core.config import Snippet
from ravan.core.i18n import t
from ravan.core.snippet import snippets_from_json, snippets_to_json

_PLACEHOLDERS = [
    ("+ $0", "$0"), ("+ {{shamsi}}", "{{shamsi}}"), ("+ {{tarikh}}", "{{tarikh}}"),
    ("+ {{time}}", "{{time}}"), ("+ {{weekday}}", "{{weekday}}"), ("+ {{uuid}}", "{{uuid}}"),
    ("+ {{calc:...}}", "{{calc: 100 * 1.09}}"),
]


def build_placeholder_toolbar(
    parent: ttk.Frame,
    text_editor_getter: Callable[[], tk.Text | None],
    on_modified: Callable[[], None],
) -> ttk.LabelFrame:
    """Create the insert-placeholders quick button toolbar."""
    h_box = ttk.LabelFrame(
        parent,
        text=t("snippets_editor.insert_placeholders", "Insert Placeholders"),
        padding=2,
    )
    h_btns = ttk.Frame(h_box)
    h_btns.pack(fill="x")

    def add_ph(text: str) -> None:
        ed = text_editor_getter()
        if ed is not None:
            ed.insert(tk.INSERT, text)
            ed.focus_set()
            on_modified()

    for label, val in _PLACEHOLDERS:
        ttk.Button(h_btns, text=label, command=lambda v=val: add_ph(v)).pack(side="left", padx=1)
    return h_box


def eval_live_test(trig: str, repl: str, sample: str) -> tuple[bool, str, str]:
    """Evaluate live trigger test returning (matched, display_text, hex_color)."""
    if not trig or not sample:
        return False, "", "gray"
    if trig.startswith("re:"):
        from ravan.core.snippet import preview_regex_expansion

        ok, res = preview_regex_expansion(trig, repl, sample)
        color = "#2b8a3e" if ok else ("gray" if res == "No match" else "#c92a2a")
        txt = (
            t("snippets_editor.regex_test_matched", "Matched: {result}", result=res)
            if ok
            else (t("snippets_editor.regex_test_no_match", "No match") if res == "No match" else res)
        )
        return ok, txt, color

    matched = sample == trig
    from ravan.core.snippet import render_template

    res = render_template(repl) if matched else ""
    txt = (
        t("snippets_editor.regex_test_matched", "Matched: {result}", result=res)
        if matched
        else t("snippets_editor.regex_test_no_match", "No match")
    )
    return matched, txt, "#2b8a3e" if matched else "gray"


def validate_snippet_entry(
    trig: str,
    repl: str,
    is_image: bool = False,
    parent: tk.Widget | None = None,
) -> bool:
    """Validate trigger and replacement syntax/path before applying or saving."""
    if not trig:
        messagebox.showwarning(
            t("app_name", "Ravaan"),
            t("snippets_editor.empty_trigger_warn", "Trigger cannot be empty"),
            parent=parent,
        )
        return False
    if trig.startswith("re:"):
        from ravan.core.snippet_regex import validate_regex_trigger

        is_valid, err = validate_regex_trigger(trig)
        if not is_valid:
            messagebox.showerror(
                t("snippets_editor.regex_error_title", "Regex Error"),
                t("snippets_editor.regex_error_msg", "Invalid regex:\n{err}", err=err),
                parent=parent,
            )
            return False
    if is_image or repl.startswith("image:"):
        from ravan.ui.snippet_groups_ui import validate_and_alert_image

        img_path = repl[6:].strip() if repl.startswith("image:") else repl.strip()
        if not validate_and_alert_image(img_path, parent=parent):
            return False
    return True


def import_snippets_dialog(
    parent: tk.Toplevel | None, current: list[Snippet]
) -> list[Snippet] | None:
    """Prompt user to choose a JSON file and merge/replace snippets."""
    path = filedialog.askopenfilename(
        parent=parent,
        title=t("snippets_editor.import_title", "Import Snippets"),
        filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
    )
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            imported = snippets_from_json(f.read())
        if not imported:
            messagebox.showinfo(
                t("app_name", "Ravaan"),
                t("snippets_editor.no_snippets_found", "No valid snippets found in file."),
                parent=parent,
            )
            return None

        ans = messagebox.askyesnocancel(
            t("snippets_editor.import_title", "Import Snippets"),
            t(
                "snippets_editor.import_prompt",
                "Found {count} snippets.\n\nClick 'Yes' to Merge with existing snippets.\n"
                "Click 'No' to Replace all existing snippets.\nClick 'Cancel' to abort.",
                count=len(imported),
            ),
            parent=parent,
        )
        if ans is None:
            return None
        if ans:
            by_trig = {s.trigger: s for s in current}
            for s in imported:
                by_trig[s.trigger] = s
            result = list(by_trig.values())
        else:
            result = imported

        messagebox.showinfo(
            t("app_name", "Ravaan"),
            t(
                "snippets_editor.import_success",
                "Successfully imported {count} snippets.",
                count=len(imported),
            ),
            parent=parent,
        )
        return result
    except Exception as ex:  # noqa: BLE001
        messagebox.showerror(
            t("notifications.error_title", "Ravaan Error"),
            t("snippets_editor.import_err", "Failed to import snippets:\n{ex}", ex=ex),
            parent=parent,
        )
        return None


def export_snippets_dialog(parent: tk.Toplevel | None, snippets: list[Snippet]) -> bool:
    """Prompt user to choose export destination and save snippets JSON."""
    path = filedialog.asksaveasfilename(
        parent=parent,
        title=t("snippets_editor.btn_export", "Export JSON…"),
        defaultextension=".json",
        filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
    )
    if not path:
        return False
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(snippets_to_json(snippets))
        messagebox.showinfo(
            t("app_name", "Ravaan"),
            t(
                "snippets_editor.export_success",
                "Exported {count} snippets successfully.",
                count=len(snippets),
            ),
            parent=parent,
        )
        return True
    except Exception as ex:  # noqa: BLE001
        messagebox.showerror(
            t("notifications.error_title", "Ravaan Error"),
            t("snippets_editor.export_err", "Failed to export snippets:\n{ex}", ex=ex),
            parent=parent,
        )
        return False
