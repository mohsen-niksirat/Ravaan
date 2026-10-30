"""UI dialogs for inspecting, verifying cryptographic integrity, and importing .ravaanpack packages."""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ravan.core.config import Snippet
from ravan.core.config_types import SnippetGroup
from ravan.core.i18n import is_rtl, t
from ravan.core.package import (
    PackageIntegrityError,
    detect_package_collisions,
    extract_package_groups,
    import_package,
)
from ravan.ui.package_export_dialog import (  # noqa: F401
    PackageExportDialog,
    open_package_export_dialog,
)
from ravan.ui.theme import (
    apply_theme_to_ttk,
    apply_window_decorations,
    get_active_palette,
)

log = logging.getLogger(__name__)


class PackagePreviewDialog:
    """Dialog to inspect, verify cryptographic integrity, review, and import a .ravaanpack."""

    def __init__(
        self,
        parent: tk.Widget | None,
        package_path: str | Path,
        existing_snippets: list[Snippet],
        on_confirm: Callable[[list[Snippet], list[SnippetGroup]], None],
    ) -> None:
        self.parent = parent
        self.package_path = Path(package_path)
        self.existing_snippets = existing_snippets
        self.on_confirm = on_confirm
        self._root: tk.Toplevel | None = None
        self.replace_var = tk.BooleanVar(value=False)

    def show(self) -> None:
        try:
            manifest, collisions = detect_package_collisions(
                self.package_path, self.existing_snippets
            )
        except PackageIntegrityError as err:
            messagebox.showerror(
                t("app_name", "Ravaan"),
                t(
                    "packages.integrity_error",
                    "Package integrity verification failed!\nThe package contents have been tampered with or corrupted:\n{err}",
                    err=err,
                ),
                parent=self.parent,
            )
            return
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror(
                t("notifications.error_title", "Ravaan Error"),
                f"Failed to inspect package:\n{ex}",
                parent=self.parent,
            )
            return

        rtl = is_rtl()
        align = "e" if rtl else "w"
        pack_side = "right" if rtl else "left"

        top = tk.Toplevel(self.parent)
        self._root = top
        top.title(t("packages.import_title", "Import Ravaan Snippet Package"))
        top.geometry("560x520")
        top.minsize(480, 420)
        top.attributes("-topmost", True)
        palette = get_active_palette()
        apply_window_decorations(top, palette)
        apply_theme_to_ttk(top, palette)

        frm = ttk.Frame(top, padding=12)
        frm.pack(fill="both", expand=True)

        # Header: Name, Version & Author
        pkg_name = manifest.get("name") or manifest.get("title") or self.package_path.name
        author = manifest.get("author", "")
        author_str = f" — {author}" if author else ""
        ttk.Label(
            frm,
            text=f"📦 {pkg_name}{author_str}",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=align, pady=(0, 4))

        # Description
        desc = (
            (manifest.get("description_fa") or manifest.get("description", ""))
            if rtl
            else (manifest.get("description_en") or manifest.get("description", ""))
        )
        if desc:
            ttk.Label(frm, text=desc, wraplength=520).pack(anchor=align, pady=(0, 6))

        # Integrity badge
        ttk.Label(
            frm,
            text=t("packages.integrity_verified", "✓ Integrity verified (SHA-256)"),
            foreground="#2b8a3e",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor=align, pady=(0, 6))

        # Snippets treeview preview
        snips = manifest.get("snippets", [])
        ttk.Label(
            frm,
            text=t("packages.preview_header", "Snippets Included in Package:"),
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor=align, pady=(2, 2))

        tree_frame = ttk.Frame(frm)
        tree_frame.pack(fill="both", expand=True, pady=(0, 8))

        cols = ("trigger", "type", "replacement")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=7)
        tree.heading("trigger", text=t("snippets_editor.col_trigger", "Trigger"))
        tree.heading("type", text=t("snippets_editor.body_type", "Type"))
        tree.heading("replacement", text=t("snippets_editor.col_preview", "Preview"))

        tree.column("trigger", width=120)
        tree.column("type", width=80)
        tree.column("replacement", width=300)

        for s in snips:
            trig = s.get("trigger", "")
            is_img = s.get("is_image", False)
            is_reg = s.get("is_regex", False)
            repl = s.get("replacement", "")
            t_label = "Image" if is_img else ("Regex" if is_reg else "Text")
            preview_txt = (Path(repl).name if is_img else repl).replace("\n", " ")
            tree.insert("", "end", values=(trig, t_label, preview_txt[:60]))

        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)

        # Collisions section
        if collisions:
            col_box = ttk.LabelFrame(frm, padding=6)
            col_box.pack(fill="x", pady=(0, 8))
            ttk.Label(
                col_box,
                text=t(
                    "packages.collisions_warning",
                    "⚠️ {count} trigger collision(s) detected with your existing snippets.",
                    count=len(collisions),
                ),
                foreground="#e67700",
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor=align)

            col_str = ", ".join(collisions[:6]) + ("…" if len(collisions) > 6 else "")
            ttk.Label(col_box, text=col_str, foreground="#868e96").pack(anchor=align, pady=(2, 4))

            ttk.Checkbutton(
                col_box,
                text=t(
                    "packages.replace_checkbox",
                    "Replace existing snippets on collision",
                ),
                variable=self.replace_var,
            ).pack(anchor=align)

        # Bottom buttons
        btn_bar = ttk.Frame(frm)
        btn_bar.pack(fill="x", pady=(4, 0))

        def _do_import() -> None:
            try:
                imported_snips = import_package(
                    self.package_path,
                    replace_existing=self.replace_var.get(),
                    existing_snippets=self.existing_snippets,
                )
                imported_groups = extract_package_groups(manifest)
                self.on_confirm(imported_snips, imported_groups)
                messagebox.showinfo(
                    t("app_name", "Ravaan"),
                    t(
                        "packages.import_success",
                        "Successfully imported {count} snippets from package '{name}'.",
                        count=len(snips),
                        name=pkg_name,
                    ),
                    parent=top,
                )
                top.destroy()
            except Exception as ex:  # noqa: BLE001
                messagebox.showerror(
                    t("notifications.error_title", "Ravaan Error"),
                    f"Import failed: {ex}",
                    parent=top,
                )

        ttk.Button(
            btn_bar,
            text=t("packages.btn_import_action", "Import Package"),
            command=_do_import,
        ).pack(side=pack_side, padx=(0, 6) if not rtl else (6, 0))

        ttk.Button(
            btn_bar,
            text=t("common.cancel", "Cancel"),
            command=top.destroy,
        ).pack(side=pack_side)


def open_package_import_dialog(
    parent: tk.Widget | None,
    current_snippets: list[Snippet],
    current_groups: list[SnippetGroup],
    on_imported: Callable[[list[Snippet], list[SnippetGroup]], None],
) -> None:
    """Prompt user for a .ravaanpack file and launch verification preview dialog."""
    path = filedialog.askopenfilename(
        parent=parent,
        title=t("packages.import_title", "Import Ravaan Snippet Package"),
        filetypes=[("Ravaan Packages", "*.ravaanpack"), ("All Files", "*.*")],
    )
    if not path:
        return

    dlg = PackagePreviewDialog(parent, path, current_snippets, on_imported)
    dlg.show()
