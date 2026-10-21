"""JSON import and export file dialog handlers for the Snippet Editor."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

from ravan.core.config import Snippet
from ravan.core.i18n import t
from ravan.core.snippet import snippets_from_json, snippets_to_json


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
