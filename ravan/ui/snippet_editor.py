"""Snippet Editor Window (Tkinter) — multi-line templates, image snippets, per-app groups, and live preview."""

from __future__ import annotations

import copy
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from ravan.core.config import Snippet
from ravan.core.config_types import SnippetGroup
from ravan.core.i18n import t
from ravan.core.snippet import parse_cursor_placeholder, render_template
from ravan.ui.snippet_editor_io import (
    build_placeholder_toolbar,
    eval_live_test,
    export_snippets_dialog,
    import_snippets_dialog,
    validate_snippet_entry,
)
from ravan.ui.snippet_groups_ui import SnippetGroupSelector, pick_image_file
from ravan.ui.theme import (
    apply_theme_to_ttk,
    apply_window_decorations,
    get_active_palette,
)


class SnippetEditorWindow:
    """Dedicated GUI for managing text & image snippets with per-app groups."""

    def __init__(
        self,
        snippets: list[Snippet],
        on_saved: Callable[[list[Snippet]], None],
        groups: list[SnippetGroup] | None = None,
    ) -> None:
        self.snippets: list[Snippet] = copy.deepcopy(snippets)
        self.on_saved = on_saved
        self.groups: list[SnippetGroup] = list(groups or [])
        self._open = self._built = False
        self._root = self._selected_index = self._tree = None
        self._filter_var = self._trigger_var = self._test_input_var = self._image_path_var = None
        self._type_var: tk.StringVar | None = None
        self._test_status_lbl = self._text_editor = self._preview_text = None
        self._text_pane = self._image_pane = self._group_selector = None

    @property
    def open(self) -> bool:
        return self._open

    def show(self) -> None:
        self._open = True

    def tick(self) -> None:
        if not self._open:
            return
        if not self._built:
            self._build()
            self._built = True
        if self._root is None:
            return
        try:
            self._root.update_idletasks()
            self._root.update()
        except (tk.TclError, RuntimeError):
            pass

    def _build(self) -> None:
        self._root = tk.Toplevel()
        self._root.title(t("snippets_editor.title", "Ravaan — Snippet Editor"))
        self._root.geometry("880x620")
        self._root.minsize(780, 520)
        self._root.protocol("WM_DELETE_WINDOW", self._close)
        palette = get_active_palette()
        apply_window_decorations(self._root, palette)
        apply_theme_to_ttk(self._root, palette)

        main_frm = ttk.Frame(self._root, padding=10)
        main_frm.pack(fill="both", expand=True)
        paned = ttk.PanedWindow(main_frm, orient="horizontal")
        paned.pack(fill="both", expand=True, pady=(0, 8))

        # ── LEFT PANE: Snippet List & Search ──
        left_frm = ttk.Frame(paned, padding=4)
        paned.add(left_frm, weight=1)

        search_bar = ttk.Frame(left_frm)
        search_bar.pack(fill="x", pady=(0, 6))
        ttk.Label(search_bar, text=t("snippets_editor.search", "Search:")).pack(side="left", padx=(0, 4))
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._refresh_list())
        ttk.Entry(search_bar, textvariable=self._filter_var).pack(side="left", fill="x", expand=True)

        tree_frame = ttk.Frame(left_frm)
        tree_frame.pack(fill="both", expand=True)
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical")
        self._tree = ttk.Treeview(
            tree_frame, columns=("trigger", "preview"), show="headings", selectmode="browse", yscrollcommand=tree_scroll.set
        )
        tree_scroll.config(command=self._tree.yview)
        tree_scroll.pack(side="right", fill="y")
        self._tree.pack(side="left", fill="both", expand=True)
        self._tree.heading("trigger", text=t("snippets_editor.col_trigger", "Trigger"), anchor="w")
        self._tree.heading("preview", text=t("snippets_editor.col_preview", "Preview"), anchor="w")
        self._tree.column("trigger", width=130, stretch=False)
        self._tree.column("preview", width=170, stretch=True)
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        list_btns = ttk.Frame(left_frm)
        list_btns.pack(fill="x", pady=(6, 0))
        for txt, cmd, px in [(t("snippets_editor.btn_new", "+ New"), self._add_snippet, (0, 4)), (t("snippets_editor.btn_delete", "- Delete"), self._delete_snippet, 4), (t("snippets_editor.btn_duplicate", "Duplicate"), self._duplicate_snippet, 4)]:
            ttk.Button(list_btns, text=txt, command=cmd).pack(side="left", padx=px)

        # ── RIGHT PANE: Details, Body Selector, Groups & Preview ──
        right_frm = ttk.Frame(paned, padding=6)
        paned.add(right_frm, weight=2)

        top_row = ttk.Frame(right_frm)
        top_row.pack(fill="x", pady=(0, 6))
        ttk.Label(top_row, text=t("snippets_editor.trigger_label", "Trigger:"), font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self._trigger_var = tk.StringVar()
        self._trigger_var.trace_add("write", lambda *_: self._on_editor_modified())
        ttk.Entry(top_row, textvariable=self._trigger_var, width=16).pack(side="left", padx=(0, 10))

        ttk.Label(top_row, text=t("snippets_editor.body_type", "Type:"), font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self._type_var = tk.StringVar(value="text")
        self._type_var.trace_add("write", lambda *_: self._on_type_changed())
        ttk.Combobox(top_row, textvariable=self._type_var, values=["text", "image"], state="readonly", width=8).pack(side="left", padx=(0, 8))

        # Text Replacement Pane
        self._text_pane = ttk.Frame(right_frm)
        self._text_pane.pack(fill="both", expand=True)
        ttk.Label(self._text_pane, text=t("snippets_editor.template_label", "Replacement template:"), font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 2))

        ed_frm = ttk.Frame(self._text_pane)
        ed_frm.pack(fill="both", expand=True)
        ed_scroll = ttk.Scrollbar(ed_frm, orient="vertical")
        self._text_editor = tk.Text(ed_frm, wrap="word", height=5, font=("Consolas", 10), yscrollcommand=ed_scroll.set)
        ed_scroll.config(command=self._text_editor.yview)
        ed_scroll.pack(side="right", fill="y")
        self._text_editor.pack(side="left", fill="both", expand=True)
        self._text_editor.bind("<KeyRelease>", lambda *_: self._on_editor_modified())

        build_placeholder_toolbar(self._text_pane, lambda: self._text_editor, self._on_editor_modified).pack(fill="x", pady=(2, 2))

        test_box = ttk.LabelFrame(self._text_pane, text=t("snippets_editor.regex_test_label", "Live Trigger Test"), padding=2)
        test_box.pack(fill="x", pady=(0, 2))
        t_row = ttk.Frame(test_box)
        t_row.pack(fill="x")
        ttk.Label(t_row, text=t("snippets_editor.sample_input_label", "Test Input:")).pack(side="left", padx=(0, 4))
        self._test_input_var = tk.StringVar()
        self._test_input_var.trace_add("write", lambda *_: self._update_test_preview())
        ttk.Entry(t_row, textvariable=self._test_input_var, width=16).pack(side="left", fill="x", expand=True)
        self._test_status_lbl = ttk.Label(test_box, text="", font=("Segoe UI", 8))
        self._test_status_lbl.pack(anchor="w")

        prev_box = ttk.LabelFrame(self._text_pane, text=t("snippets_editor.live_preview", "Live Output Preview"), padding=2)
        prev_box.pack(fill="x", pady=(0, 2))
        self._preview_text = tk.Text(prev_box, wrap="word", height=2, state="disabled", background="#f8f9fa", font=("Segoe UI", 9))
        self._preview_text.pack(fill="x", expand=True)

        # Image Snippet Pane
        self._image_pane = ttk.LabelFrame(right_frm, text=t("snippets_editor.type_image", "Image (Clipboard)"), padding=8)
        img_row = ttk.Frame(self._image_pane)
        img_row.pack(fill="x", pady=4)
        ttk.Label(img_row, text=t("snippets_editor.image_path_label", "Image file path:")).pack(side="left", padx=(0, 6))
        self._image_path_var = tk.StringVar()
        self._image_path_var.trace_add("write", lambda *_: self._on_editor_modified())
        ttk.Entry(img_row, textvariable=self._image_path_var).pack(side="left", fill="x", expand=True, padx=(0, 6))

        def browse_img() -> None:
            picked = pick_image_file(self._root)
            if picked and self._image_path_var:
                self._image_path_var.set(picked)

        ttk.Button(img_row, text=t("snippets_editor.btn_browse", "Browse…"), command=browse_img).pack(side="left")

        # Groups assignment
        self._group_selector = SnippetGroupSelector(right_frm, self.groups)
        self._group_selector.pack(fill="x", pady=(4, 4))

        ttk.Button(right_frm, text=t("snippets_editor.btn_apply", "Apply Changes to Selected"), command=self._save_current_to_list).pack(anchor="e", pady=(2, 0))

        # ── BOTTOM TOOLBAR ──
        bot_bar = ttk.Frame(main_frm)
        bot_bar.pack(fill="x", pady=(6, 0))
        for txt, cmd, side, px in [
            (t("snippets_editor.btn_import", "Import JSON…"), self._import_json, "left", (0, 4)),
            (t("snippets_editor.btn_export", "Export JSON…"), self._export_json, "left", 4),
            (t("packages.import_btn", "📦 Import Package…"), self._import_pack, "left", 4),
            (t("packages.export_btn", "📦 Export Package…"), self._export_pack, "left", 4),
            (t("snippets_editor.btn_cancel", "Cancel"), self._close, "right", (6, 0)),
        ]:
            ttk.Button(bot_bar, text=txt, command=cmd).pack(side=side, padx=px)

        ttk.Button(
            bot_bar,
            text=t("snippets_editor.btn_save_close", "Save & Close"),
            style="Accent.TButton",
            command=self._save_all_and_close,
        ).pack(side="right", padx=6)

        self._refresh_list()
        if self.snippets:
            self._select_index(0)
        self._center()

    def _center(self) -> None:
        if self._root is None:
            return
        self._root.update_idletasks()
        w, h = self._root.winfo_width(), self._root.winfo_height()
        self._root.geometry(f"+{(self._root.winfo_screenwidth() - w) // 2}+{(self._root.winfo_screenheight() - h) // 3}")

    def _on_type_changed(self) -> None:
        if not self._text_pane or not self._image_pane or not self._type_var:
            return
        is_img = self._type_var.get() == "image"
        if is_img:
            self._text_pane.pack_forget()
            self._image_pane.pack(fill="x", pady=(4, 4), before=self._group_selector)
        else:
            self._image_pane.pack_forget()
            self._text_pane.pack(fill="both", expand=True, before=self._group_selector)

    def _refresh_list(self) -> None:
        if self._tree is None or self._filter_var is None:
            return
        filter_str = self._filter_var.get().strip().lower()
        self._tree.delete(*self._tree.get_children())
        reg_b = t("snippets_editor.regex_badge", "[Regex] ")
        for idx, s in enumerate(self.snippets):
            if filter_str and filter_str not in s.trigger.lower() and filter_str not in s.replacement.lower():
                continue
            is_reg = s.trigger.startswith("re:") or getattr(s, "is_regex", False)
            is_img = getattr(s, "is_image", False) or s.replacement.startswith("image:")
            prefix = "[Img] " if is_img else (reg_b if is_reg else "")
            display_trig = f"{prefix}{s.trigger}"
            first_line = s.replacement.splitlines()[0] if s.replacement.splitlines() else ""
            if len(first_line) > 30:
                first_line = first_line[:27] + "..."
            if getattr(s, "groups", None):
                first_line += f" ({', '.join(s.groups)})"
            self._tree.insert("", "end", iid=str(idx), values=(display_trig, first_line))

    def _load_snippet_to_editor(self, idx: int) -> None:
        s = self.snippets[idx]
        if self._trigger_var:
            self._trigger_var.set(s.trigger)
        is_img = getattr(s, "is_image", False) or s.replacement.startswith("image:")
        if self._type_var:
            self._type_var.set("image" if is_img else "text")
        if is_img and self._image_path_var:
            self._image_path_var.set(s.replacement[6:].strip() if s.replacement.startswith("image:") else s.replacement.strip())
        elif self._text_editor:
            self._text_editor.delete("1.0", tk.END)
            self._text_editor.insert("1.0", s.replacement)
        if self._group_selector:
            self._group_selector.set_selected(getattr(s, "groups", []))
        if self._test_input_var:
            self._test_input_var.set(";d25" if s.trigger.startswith("re:;d") else ("" if s.trigger.startswith("re:") else s.trigger))
        self._on_type_changed()
        self._update_preview()
        self._update_test_preview()

    def _select_index(self, idx: int) -> None:
        if self._tree and 0 <= idx < len(self.snippets):
            self._selected_index = idx
            self._tree.selection_set(str(idx))
            self._load_snippet_to_editor(idx)

    def _on_tree_select(self, _event: object = None) -> None:
        if self._tree and (sel := self._tree.selection()):
            self._selected_index = int(sel[0])
            self._load_snippet_to_editor(self._selected_index)

    def _on_editor_modified(self) -> None:
        self._update_preview()
        self._update_test_preview()

    def _update_preview(self) -> None:
        if self._text_editor is None or self._preview_text is None:
            return
        clean, off = parse_cursor_placeholder(render_template(self._text_editor.get("1.0", tk.END).rstrip("\n")))
        info = f" [Caret |< {off} chars]" if off is not None else ""
        self._preview_text.config(state="normal")
        self._preview_text.delete("1.0", tk.END)
        self._preview_text.insert("1.0", f"{clean}{info}")
        self._preview_text.config(state="disabled")

    def _update_test_preview(self) -> None:
        if not self._test_status_lbl or not self._trigger_var or not self._text_editor:
            return
        trig = self._trigger_var.get().strip()
        repl = self._text_editor.get("1.0", tk.END).rstrip("\n")
        sample = self._test_input_var.get().strip() if self._test_input_var else ""
        _, txt, color = eval_live_test(trig, repl, sample)
        self._test_status_lbl.config(text=txt, foreground=color)

    def _save_current_to_list(self) -> bool:
        if self._trigger_var is None:
            return False
        trig = self._trigger_var.get().strip()
        is_img = bool(self._type_var and self._type_var.get() == "image")
        repl = self._image_path_var.get().strip() if is_img and self._image_path_var else (self._text_editor.get("1.0", tk.END).rstrip("\n") if self._text_editor else "")
        if is_img and not repl.startswith("image:"):
            repl = f"image:{repl}"
        if not validate_snippet_entry(trig, repl, is_image=is_img, parent=self._root):
            return False

        grps = self._group_selector.get_selected() if self._group_selector else []
        snip = Snippet(trigger=trig, replacement=repl, is_regex=trig.startswith("re:"), is_image=is_img, groups=grps)
        if self._selected_index is not None and 0 <= self._selected_index < len(self.snippets):
            self.snippets[self._selected_index] = snip
        else:
            self.snippets.append(snip)
            self._selected_index = len(self.snippets) - 1
        self._refresh_list()
        self._select_index(self._selected_index)
        return True

    def _add_snippet(self) -> None:
        self.snippets.append(Snippet(trigger="new_trigger", replacement="New replacement text"))
        self._refresh_list()
        self._select_index(len(self.snippets) - 1)
        if self._trigger_var:
            self._trigger_var.set("")
        if self._text_editor:
            self._text_editor.focus_set()

    def _delete_snippet(self) -> None:
        if self._selected_index is not None and 0 <= self._selected_index < len(self.snippets):
            del self.snippets[self._selected_index]
            self._selected_index = None
            self._refresh_list()
            if self.snippets:
                self._select_index(0)

    def _duplicate_snippet(self) -> None:
        if self._selected_index is not None and 0 <= self._selected_index < len(self.snippets):
            c = self.snippets[self._selected_index]
            dup = Snippet(f"{c.trigger}_copy", c.replacement, getattr(c, "enabled", True), getattr(c, "is_regex", False), getattr(c, "app_filter", ""), getattr(c, "is_image", False), list(getattr(c, "groups", [])))
            self.snippets.insert(self._selected_index + 1, dup)
            self._refresh_list()
            self._select_index(self._selected_index + 1)

    def _import_json(self) -> None:
        res = import_snippets_dialog(self._root, self.snippets)
        if res is not None:
            self.snippets = res
            self._refresh_list()
            if self.snippets:
                self._select_index(0)

    def _export_json(self) -> None:
        self._save_current_to_list()
        export_snippets_dialog(self._root, self.snippets)

    def _import_pack(self) -> None:
        from ravan.ui.package_dialog import open_package_import_dialog

        def on_imported(snips: list[Snippet], grps: list[SnippetGroup]) -> None:
            self.snippets = snips
            if grps:
                self.groups = grps
            self._refresh_list()
            if self.snippets:
                self._select_index(0)

        open_package_import_dialog(self._root, self.snippets, self.groups, on_imported)

    def _export_pack(self) -> None:
        from ravan.ui.package_dialog import open_package_export_dialog

        self._save_current_to_list()
        open_package_export_dialog(self._root, self.snippets, self.groups)

    def _save_all_and_close(self) -> None:
        if self._trigger_var and self._trigger_var.get().strip():
            if not self._save_current_to_list():
                return
        for s in self.snippets:
            is_img = getattr(s, "is_image", False) or s.replacement.startswith("image:")
            if not validate_snippet_entry(s.trigger, s.replacement, is_image=is_img, parent=self._root):
                return
        self.on_saved(self.snippets)
        self._close()

    def _close(self) -> None:
        self._open = False
        if self._root is not None:
            try:
                self._root.destroy()
            except Exception:  # noqa: BLE001
                pass
            self._root = None
        self._built = False
