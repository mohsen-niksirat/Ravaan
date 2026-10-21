"""UI components for Snippets 3.0: Image picker and per-app snippet groups management."""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, messagebox, simpledialog, ttk

from ravan.core.config import Config
from ravan.core.config_types import SnippetGroup
from ravan.core.i18n import is_rtl, t
from ravan.core.snippet_groups import validate_image_path

log = logging.getLogger(__name__)

__all__ = [
    "SnippetGroupSelector",
    "build_groups_manager_frame",
    "pick_image_file",
    "validate_and_alert_image",
]


def pick_image_file(parent: tk.Widget | None = None) -> str | None:
    """Prompt user to choose an image file for an image snippet."""
    res = filedialog.askopenfilename(
        parent=parent,
        title=t("snippets_editor.pick_image_title", "Select Snippet Image"),
        filetypes=[
            (
                t("snippets_editor.image_types", "Image Files"),
                "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp",
            ),
            (t("snippets_editor.all_files", "All Files"), "*.*"),
        ],
    )
    return str(res).strip() if res else None


def validate_and_alert_image(path: str, parent: tk.Widget | None = None) -> bool:
    """Validate image path exists and has valid format; shows error dialog if invalid."""
    ok, err = validate_image_path(path)
    if not ok:
        messagebox.showerror(
            t("app_name", "Ravaan"),
            t("snippets_editor.invalid_image_err", "The selected image file is missing or invalid:\n{err}", err=err),
            parent=parent,
        )
        return False
    return True


class SnippetGroupSelector(ttk.Frame):
    """Checklist frame allowing user to assign a snippet to 0..N per-app groups."""

    def __init__(
        self,
        parent: tk.Widget,
        groups: list[SnippetGroup],
        on_change: Callable[[list[str]], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.groups = groups
        self.on_change = on_change
        self._vars: dict[str, tk.BooleanVar] = {}
        self._build()

    def _build(self) -> None:
        lbl_text = t(
            "snippets_editor.groups_section",
            "App Groups (fires only in matching applications):",
        )
        ttk.Label(self, text=lbl_text, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 2))

        if not self.groups:
            ttk.Label(
                self,
                text=t("snippets_editor.no_groups_hint", "(No groups configured. Configure in Settings > Snippets)"),
                foreground="gray",
                font=("Segoe UI", 8),
            ).pack(anchor="w")
            return

        box = ttk.Frame(self)
        box.pack(fill="x", pady=(2, 2))

        for g in self.groups:
            gid = g.id or g.name
            var = tk.BooleanVar(value=False)
            self._vars[gid] = var
            var.trace_add("write", lambda *_: self._notify())
            status_hint = "" if g.enabled else f" ({t('settings.group_status_disabled', 'Disabled')})"
            cb = ttk.Checkbutton(box, text=f"{g.name}{status_hint}", variable=var)
            cb.pack(side="left", padx=(0, 10))

    def _notify(self) -> None:
        if self.on_change is not None:
            self.on_change(self.get_selected())

    def get_selected(self) -> list[str]:
        return [gid for gid, var in self._vars.items() if var.get()]

    def set_selected(self, group_refs: list[str]) -> None:
        low_refs = {r.strip().lower() for r in group_refs if r.strip()}
        for gid, var in self._vars.items():
            # Match either by group id or name
            matched = False
            for g in self.groups:
                if (g.id == gid or g.name == gid) and (g.id.lower() in low_refs or g.name.lower() in low_refs):
                    matched = True
                    break
            var.set(matched or gid.lower() in low_refs)


def build_groups_manager_frame(
    parent: ttk.Frame,
    cfg: Config,
    on_groups_changed: Callable[[list[SnippetGroup]], None],
) -> ttk.Frame:
    """Build the per-app snippet groups list manager in Settings -> Snippets."""
    rtl = is_rtl()
    container = ttk.LabelFrame(
        parent,
        text=t("settings.groups_header", "Per-App Snippet Groups"),
        padding=6,
    )

    tree_frm = ttk.Frame(container)
    tree_frm.pack(fill="both", expand=True, pady=(2, 4))

    scroll = ttk.Scrollbar(tree_frm, orient="vertical")
    tree = ttk.Treeview(
        tree_frm,
        columns=("name", "matchers", "status"),
        show="headings",
        selectmode="browse",
        height=4,
        yscrollcommand=scroll.set,
    )
    scroll.config(command=tree.yview)
    scroll.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)

    tree.heading("name", text=t("settings.group_col_name", "Group Name"), anchor="w")
    tree.heading("matchers", text=t("settings.group_col_matchers", "App / Class Matchers"), anchor="w")
    tree.heading("status", text=t("settings.group_col_status", "Status"), anchor="w")

    tree.column("name", width=120, stretch=False)
    tree.column("matchers", width=260, stretch=True)
    tree.column("status", width=80, stretch=False)

    def refresh() -> None:
        tree.delete(*tree.get_children())
        for idx, g in enumerate(cfg.snippet_groups):
            match_str = ", ".join(g.matchers) if g.matchers else "—"
            st = t("settings.group_status_active", "Active") if g.enabled else t("settings.group_status_disabled", "Disabled")
            tree.insert("", "end", iid=str(idx), values=(g.name, match_str, st))

    def on_add() -> None:
        name = simpledialog.askstring(
            t("settings.btn_add_group", "+ Add Group"),
            t("settings.group_prompt_name", "Enter group name (e.g. Browsers, Code):"),
            parent=container,
        )
        if not name or not name.strip():
            return
        matchers_str = simpledialog.askstring(
            t("settings.btn_add_group", "+ Add Group"),
            t("settings.group_prompt_matchers", "Enter application exe names or classes (comma-separated, e.g. chrome.exe, code.exe, class:Notepad):"),
            parent=container,
        )
        matchers = [m.strip() for m in (matchers_str or "").split(",") if m.strip()]
        gid = name.strip().lower().replace(" ", "_")
        cfg.snippet_groups.append(SnippetGroup(id=gid, name=name.strip(), matchers=matchers, enabled=True))
        refresh()
        on_groups_changed(cfg.snippet_groups)

    def on_edit() -> None:
        sel = tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        g = cfg.snippet_groups[idx]
        cur = ", ".join(g.matchers)
        matchers_str = simpledialog.askstring(
            t("settings.btn_edit_group", "✎ Edit Matchers"),
            t("settings.group_prompt_matchers", "Enter application exe names or classes (comma-separated, e.g. chrome.exe, code.exe, class:Notepad):"),
            initialvalue=cur,
            parent=container,
        )
        if matchers_str is not None:
            g.matchers = [m.strip() for m in matchers_str.split(",") if m.strip()]
            refresh()
            on_groups_changed(cfg.snippet_groups)

    def on_toggle() -> None:
        sel = tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        cfg.snippet_groups[idx].enabled = not cfg.snippet_groups[idx].enabled
        refresh()
        on_groups_changed(cfg.snippet_groups)

    def on_delete() -> None:
        sel = tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        del cfg.snippet_groups[idx]
        refresh()
        on_groups_changed(cfg.snippet_groups)

    btn_row = ttk.Frame(container)
    btn_row.pack(fill="x", pady=(2, 0))
    for txt, cmd in [
        (t("settings.btn_add_group", "+ Add Group"), on_add),
        (t("settings.btn_edit_group", "✎ Edit Matchers"), on_edit),
        (t("settings.btn_toggle_group", "Toggle Active"), on_toggle),
        (t("settings.btn_delete_group", "- Delete Group"), on_delete),
    ]:
        ttk.Button(btn_row, text=txt, command=cmd).pack(side="left" if not rtl else "right", padx=2)

    refresh()
    return container
