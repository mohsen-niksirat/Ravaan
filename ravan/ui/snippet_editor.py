"""Snippet Editor Window (Tkinter) — multi-line templates, live preview, JSON import/export, and placeholder helpers."""

from __future__ import annotations

import copy
import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, messagebox, ttk

from ravan.core.config import Snippet
from ravan.core.snippet import (
    parse_cursor_placeholder,
    render_template,
    snippets_from_json,
    snippets_to_json,
)

_PLACEHOLDERS = [
    ("+ $0 (Cursor)", "$0"), ("+ {{shamsi}}", "{{shamsi}}"),
    ("+ {{tarikh}}", "{{tarikh}}"), ("+ {{time}}", "{{time}}"),
    ("+ {{weekday}}", "{{weekday}}"), ("+ {{uuid}}", "{{uuid}}"),
    ("+ {{calc:...}}", "{{calc: 100 * 1.09}}"),
]


class SnippetEditorWindow:
    """Dedicated GUI for managing text expansion snippets."""

    def __init__(
        self,
        snippets: list[Snippet],
        on_saved: Callable[[list[Snippet]], None],
    ) -> None:
        self.snippets: list[Snippet] = copy.deepcopy(snippets)
        self.on_saved = on_saved
        self._open = False
        self._built = False
        self._root: tk.Toplevel | None = None
        self._selected_index: int | None = None

        # Widgets
        self._tree: ttk.Treeview | None = None
        self._filter_var: tk.StringVar | None = None
        self._trigger_var: tk.StringVar | None = None
        self._text_editor: tk.Text | None = None
        self._preview_text: tk.Text | None = None

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
        self._root.title("Ravan — Snippet Editor (مدیریت متن‌های آماده)")
        self._root.geometry("820x560")
        self._root.minsize(720, 480)
        self._root.protocol("WM_DELETE_WINDOW", self._close)

        main_frm = ttk.Frame(self._root, padding=10)
        main_frm.pack(fill="both", expand=True)

        paned = ttk.PanedWindow(main_frm, orient="horizontal")
        paned.pack(fill="both", expand=True, pady=(0, 10))

        # ── LEFT PANE: Snippet List & Search ──
        left_frm = ttk.Frame(paned, padding=5)
        paned.add(left_frm, weight=1)

        search_bar = ttk.Frame(left_frm)
        search_bar.pack(fill="x", pady=(0, 6))
        ttk.Label(search_bar, text="Search:").pack(side="left", padx=(0, 4))
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._refresh_list())
        ttk.Entry(search_bar, textvariable=self._filter_var).pack(
            side="left", fill="x", expand=True
        )

        tree_frame = ttk.Frame(left_frm)
        tree_frame.pack(fill="both", expand=True)

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical")
        self._tree = ttk.Treeview(
            tree_frame,
            columns=("trigger", "preview"),
            show="headings",
            selectmode="browse",
            yscrollcommand=tree_scroll.set,
        )
        tree_scroll.config(command=self._tree.yview)
        tree_scroll.pack(side="right", fill="y")
        self._tree.pack(side="left", fill="both", expand=True)

        self._tree.heading("trigger", text="Trigger", anchor="w")
        self._tree.heading("preview", text="Preview", anchor="w")
        self._tree.column("trigger", width=100, stretch=False)
        self._tree.column("preview", width=200, stretch=True)
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        list_btns = ttk.Frame(left_frm)
        list_btns.pack(fill="x", pady=(6, 0))
        for txt, cmd, px in [
            ("+ New", self._add_snippet, (0, 4)),
            ("- Delete", self._delete_snippet, 4),
            ("Duplicate", self._duplicate_snippet, 4),
        ]:
            ttk.Button(list_btns, text=txt, command=cmd).pack(side="left", padx=px)

        # ── RIGHT PANE: Multi-line Editor & Placeholders ──
        right_frm = ttk.Frame(paned, padding=5)
        paned.add(right_frm, weight=2)

        trig_frm = ttk.Frame(right_frm)
        trig_frm.pack(fill="x", pady=(0, 6))
        ttk.Label(trig_frm, text="Trigger word:", font=("Segoe UI", 9, "bold")).pack(
            side="left", padx=(0, 8)
        )
        self._trigger_var = tk.StringVar()
        self._trigger_var.trace_add("write", lambda *_: self._on_editor_modified())
        ttk.Entry(trig_frm, textvariable=self._trigger_var, width=24).pack(side="left")
        ttk.Label(trig_frm, text="e.g. @@, /sig, fn", foreground="gray").pack(
            side="left", padx=8
        )

        ttk.Label(
            right_frm,
            text="Replacement template (supports multiple lines & placeholders):",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(4, 2))

        ed_frm = ttk.Frame(right_frm)
        ed_frm.pack(fill="both", expand=True)
        ed_scroll = ttk.Scrollbar(ed_frm, orient="vertical")
        self._text_editor = tk.Text(
            ed_frm,
            wrap="word",
            height=8,
            font=("Consolas", 10),
            yscrollcommand=ed_scroll.set,
        )
        ed_scroll.config(command=self._text_editor.yview)
        ed_scroll.pack(side="right", fill="y")
        self._text_editor.pack(side="left", fill="both", expand=True)
        self._text_editor.bind("<KeyRelease>", lambda *_: self._on_editor_modified())

        # Placeholder Quick Insertion Toolbar
        helper_box = ttk.LabelFrame(right_frm, text="Insert Placeholders", padding=6)
        helper_box.pack(fill="x", pady=(6, 6))
        h_btns = ttk.Frame(helper_box)
        h_btns.pack(fill="x")

        def add_ph(text: str) -> None:
            if self._text_editor is not None:
                self._text_editor.insert(tk.INSERT, text)
                self._text_editor.focus_set()
                self._on_editor_modified()

        for label, val in _PLACEHOLDERS:
            ttk.Button(h_btns, text=label, command=lambda v=val: add_ph(v)).pack(
                side="left", padx=2
            )

        preview_box = ttk.LabelFrame(right_frm, text="Live Output Preview", padding=6)
        preview_box.pack(fill="x", pady=(0, 6))
        self._preview_text = tk.Text(
            preview_box,
            wrap="word",
            height=3,
            state="disabled",
            background="#f8f9fa",
            foreground="#212529",
            font=("Segoe UI", 9),
        )
        self._preview_text.pack(fill="x", expand=True)

        ttk.Button(
            right_frm, text="Apply Changes to Selected", command=self._save_current_to_list
        ).pack(anchor="e")

        # ── BOTTOM TOOLBAR ──
        bot_bar = ttk.Frame(main_frm)
        bot_bar.pack(fill="x", pady=(6, 0))
        for txt, cmd, side, px in [
            ("Import JSON...", self._import_json, "left", (0, 6)),
            ("Export JSON...", self._export_json, "left", 6),
            ("Save & Close", self._save_all_and_close, "right", 6),
            ("Cancel", self._close, "right", (6, 0)),
        ]:
            ttk.Button(bot_bar, text=txt, command=cmd).pack(side=side, padx=px)

        self._refresh_list()
        if self.snippets:
            self._select_index(0)

        self._center()

    def _center(self) -> None:
        if self._root is None:
            return
        self._root.update_idletasks()
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        x = (self._root.winfo_screenwidth() - w) // 2
        y = (self._root.winfo_screenheight() - h) // 3
        self._root.geometry(f"+{x}+{y}")

    def _refresh_list(self) -> None:
        if self._tree is None or self._filter_var is None:
            return
        filter_str = self._filter_var.get().strip().lower()
        self._tree.delete(*self._tree.get_children())
        for idx, s in enumerate(self.snippets):
            if filter_str and filter_str not in s.trigger.lower() and filter_str not in s.replacement.lower():
                continue
            first_line = s.replacement.splitlines()[0] if s.replacement.splitlines() else ""
            if len(first_line) > 40:
                first_line = first_line[:37] + "..."
            self._tree.insert("", "end", iid=str(idx), values=(s.trigger, first_line))

    def _load_snippet_to_editor(self, idx: int) -> None:
        s = self.snippets[idx]
        if self._trigger_var:
            self._trigger_var.set(s.trigger)
        if self._text_editor:
            self._text_editor.delete("1.0", tk.END)
            self._text_editor.insert("1.0", s.replacement)
        self._update_preview()

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

    def _update_preview(self) -> None:
        if self._text_editor is None or self._preview_text is None:
            return
        raw = self._text_editor.get("1.0", tk.END).rstrip("\n")
        rendered = render_template(raw)
        clean_text, cursor_offset = parse_cursor_placeholder(rendered)
        cursor_info = f" [Caret |< {cursor_offset} chars]" if cursor_offset is not None else ""
        self._preview_text.config(state="normal")
        self._preview_text.delete("1.0", tk.END)
        self._preview_text.insert("1.0", f"{clean_text}{cursor_info}")
        self._preview_text.config(state="disabled")

    def _save_current_to_list(self) -> None:
        if self._trigger_var is None or self._text_editor is None:
            return
        trig = self._trigger_var.get().strip()
        repl = self._text_editor.get("1.0", tk.END).rstrip("\n")
        if not trig:
            messagebox.showwarning("Ravan", "Trigger cannot be empty", parent=self._root)
            return

        if self._selected_index is not None and 0 <= self._selected_index < len(self.snippets):
            self.snippets[self._selected_index] = Snippet(trigger=trig, replacement=repl)
        else:
            self.snippets.append(Snippet(trigger=trig, replacement=repl))
            self._selected_index = len(self.snippets) - 1

        self._refresh_list()
        self._select_index(self._selected_index)

    def _add_snippet(self) -> None:
        self.snippets.append(
            Snippet(trigger="new_trigger", replacement="New replacement text")
        )
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
            else:
                if self._trigger_var:
                    self._trigger_var.set("")
                if self._text_editor:
                    self._text_editor.delete("1.0", tk.END)
                self._update_preview()

    def _duplicate_snippet(self) -> None:
        if self._selected_index is not None and 0 <= self._selected_index < len(self.snippets):
            cur = self.snippets[self._selected_index]
            dup = Snippet(trigger=f"{cur.trigger}_copy", replacement=cur.replacement)
            self.snippets.insert(self._selected_index + 1, dup)
            self._refresh_list()
            self._select_index(self._selected_index + 1)

    def _import_json(self) -> None:
        path = filedialog.askopenfilename(
            parent=self._root,
            title="Import Snippets JSON",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                imported = snippets_from_json(f.read())
            if not imported:
                messagebox.showinfo("Ravan", "No valid snippets found in file.", parent=self._root)
                return

            ans = messagebox.askyesnocancel(
                "Import Snippets",
                f"Found {len(imported)} snippets.\n\n"
                "Click 'Yes' to Merge with existing snippets.\n"
                "Click 'No' to Replace all existing snippets.\n"
                "Click 'Cancel' to abort.",
                parent=self._root,
            )
            if ans is None:
                return
            if ans:
                by_trig = {s.trigger: s for s in self.snippets}
                for s in imported:
                    by_trig[s.trigger] = s
                self.snippets = list(by_trig.values())
            else:
                self.snippets = imported

            self._refresh_list()
            if self.snippets:
                self._select_index(0)
            messagebox.showinfo("Ravan", f"Successfully imported {len(imported)} snippets.", parent=self._root)
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Import Error", f"Failed to import snippets:\n{ex}", parent=self._root)

    def _sync_current(self) -> None:
        if self._selected_index is not None and self._trigger_var and self._text_editor:
            trig = self._trigger_var.get().strip()
            if trig:
                repl = self._text_editor.get("1.0", tk.END).rstrip("\n")
                self.snippets[self._selected_index] = Snippet(trigger=trig, replacement=repl)

    def _export_json(self) -> None:
        self._sync_current()
        path = filedialog.asksaveasfilename(
            parent=self._root,
            title="Export Snippets to JSON",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(snippets_to_json(self.snippets))
            messagebox.showinfo("Ravan", f"Exported {len(self.snippets)} snippets successfully.", parent=self._root)
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Export Error", f"Failed to export snippets:\n{ex}", parent=self._root)

    def _save_all_and_close(self) -> None:
        self._sync_current()
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
