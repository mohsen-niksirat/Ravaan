"""UI dialog for configuring metadata, selecting snippets/groups, and exporting a .ravaanpack."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ravan.core.config import Snippet
from ravan.core.config_types import SnippetGroup
from ravan.core.i18n import is_rtl, t
from ravan.core.package import export_package

log = logging.getLogger(__name__)


class PackageExportDialog:
    """Dialog to configure metadata, select items, and export a .ravaanpack."""

    def __init__(
        self,
        parent: tk.Widget | None,
        snippets: list[Snippet],
        groups: list[SnippetGroup],
    ) -> None:
        self.parent = parent
        self.snippets = snippets
        self.groups = groups
        self._root: tk.Toplevel | None = None

        self.name_var = tk.StringVar(value="Ravaan Snippets")
        self.author_var = tk.StringVar(value="")
        self.desc_en_var = tk.StringVar(value="")
        self.desc_fa_var = tk.StringVar(value="")
        self.snippet_vars: list[tuple[Snippet, tk.BooleanVar]] = [
            (s, tk.BooleanVar(value=True)) for s in snippets
        ]
        self.group_vars: list[tuple[SnippetGroup, tk.BooleanVar]] = [
            (g, tk.BooleanVar(value=True)) for g in groups
        ]

    def show(self) -> None:
        rtl = is_rtl()
        align = "e" if rtl else "w"
        pack_side = "right" if rtl else "left"

        top = tk.Toplevel(self.parent)
        self._root = top
        top.title(t("packages.export_title", "Export Ravaan Snippet Package"))
        top.geometry("540x540")
        top.minsize(460, 460)
        top.attributes("-topmost", True)

        frm = ttk.Frame(top, padding=12)
        frm.pack(fill="both", expand=True)

        # Metadata inputs
        grid_frm = ttk.Frame(frm)
        grid_frm.pack(fill="x", pady=(0, 8))

        fields = [
            ("packages.export_name", "Package Name:", self.name_var),
            ("packages.export_author", "Author:", self.author_var),
            ("packages.export_desc_en", "Description (English):", self.desc_en_var),
            ("packages.export_desc_fa", "Description (Persian):", self.desc_fa_var),
        ]
        for idx, (k, def_txt, f_var) in enumerate(fields):
            ttk.Label(grid_frm, text=t(k, def_txt)).grid(
                row=idx, column=0, sticky=align, pady=2, padx=4
            )
            ttk.Entry(grid_frm, textvariable=f_var, width=32).grid(
                row=idx, column=1, sticky="we", pady=2
            )
        grid_frm.columnconfigure(1, weight=1)

        # Snippet checklist frame
        ttk.Label(
            frm,
            text=t("packages.select_snippets", "Select snippets to include:"),
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor=align, pady=(4, 2))

        snip_box = ttk.Frame(frm)
        snip_box.pack(fill="both", expand=True, pady=(0, 6))

        canvas = tk.Canvas(snip_box, highlightthickness=0, height=120)
        snip_scroll = ttk.Scrollbar(snip_box, orient="vertical", command=canvas.yview)
        scroll_frm = ttk.Frame(canvas)

        scroll_frm.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frm, anchor="nw")
        canvas.configure(yscrollcommand=snip_scroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        snip_scroll.pack(side="right", fill="y")

        for s, s_var in self.snippet_vars:
            trig = s.trigger
            tag = " [Img]" if s.is_image else (" [Re]" if s.is_regex else "")
            cb = ttk.Checkbutton(scroll_frm, text=f"{trig}{tag}", variable=s_var)
            cb.pack(anchor=align, padx=2, pady=1)

        # Select all / none bar
        sel_bar = ttk.Frame(frm)
        sel_bar.pack(fill="x", pady=(0, 8))

        def _set_all(val: bool) -> None:
            for _, v in self.snippet_vars:
                v.set(val)

        ttk.Button(
            sel_bar, text=t("packages.select_all", "Select All"), command=lambda: _set_all(True)
        ).pack(side=pack_side, padx=2)
        ttk.Button(
            sel_bar,
            text=t("packages.deselect_all", "Deselect All"),
            command=lambda: _set_all(False),
        ).pack(side=pack_side, padx=2)

        # Bottom export button
        btn_bar = ttk.Frame(frm)
        btn_bar.pack(fill="x", pady=(4, 0))

        def _do_export() -> None:
            chosen = [s for s, var in self.snippet_vars if var.get()]
            if not chosen:
                messagebox.showwarning(
                    t("app_name", "Ravaan"),
                    "Please select at least one snippet to export.",
                    parent=top,
                )
                return

            dest = filedialog.asksaveasfilename(
                parent=top,
                title=t("packages.export_title", "Export Ravaan Snippet Package"),
                defaultextension=".ravaanpack",
                initialfile=f"{self.name_var.get().strip().lower().replace(' ', '-')}.ravaanpack",
                filetypes=[("Ravaan Packages", "*.ravaanpack"), ("All Files", "*.*")],
            )
            if not dest:
                return

            chosen_groups = [g for g, var in self.group_vars if var.get()]
            try:
                export_package(
                    snippets=chosen,
                    output_path=dest,
                    name=self.name_var.get().strip() or "Ravaan Snippets",
                    author=self.author_var.get().strip(),
                    description_en=self.desc_en_var.get().strip(),
                    description_fa=self.desc_fa_var.get().strip(),
                    groups=chosen_groups,
                )
                messagebox.showinfo(
                    t("app_name", "Ravaan"),
                    t(
                        "packages.export_success",
                        "Package '{name}' exported successfully ({count} snippets).",
                        name=self.name_var.get().strip(),
                        count=len(chosen),
                    ),
                    parent=top,
                )
                top.destroy()
            except Exception as ex:  # noqa: BLE001
                messagebox.showerror(
                    t("notifications.error_title", "Ravaan Error"),
                    f"Export failed: {ex}",
                    parent=top,
                )

        ttk.Button(
            btn_bar,
            text=t("packages.btn_export_action", "Export .ravaanpack"),
            command=_do_export,
        ).pack(side=pack_side, padx=(0, 6) if not rtl else (6, 0))

        ttk.Button(
            btn_bar,
            text=t("common.cancel", "Cancel"),
            command=top.destroy,
        ).pack(side=pack_side)


def open_package_export_dialog(
    parent: tk.Widget | None,
    snippets: list[Snippet],
    groups: list[SnippetGroup],
) -> None:
    """Open package export dialog."""
    dlg = PackageExportDialog(parent, snippets, groups)
    dlg.show()
