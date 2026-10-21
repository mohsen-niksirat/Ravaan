"""Snippet Editor Window (Tkinter) — multi-line templates, live preview, JSON import/export, and placeholder helpers."""

from __future__ import annotations

import copy
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from ravan.core.config import Snippet
from ravan.core.i18n import t
from ravan.core.snippet import (
    parse_cursor_placeholder,
    preview_regex_expansion,
    render_template,
    validate_regex_trigger,
)
from ravan.ui.snippet_editor_io import export_snippets_dialog, import_snippets_dialog

_PLACEHOLDERS = [
    ("+ $0", "$0"), ("+ {{shamsi}}", "{{shamsi}}"), ("+ {{tarikh}}", "{{tarikh}}"),
    ("+ {{time}}", "{{time}}"), ("+ {{weekday}}", "{{weekday}}"), ("+ {{uuid}}", "{{uuid}}"),
    ("+ {{calc:...}}", "{{calc: 100 * 1.09}}"),
]


class SnippetEditorWindow:
    """Dedicated GUI for managing text expansion snippets."""

    def __init__(self, snippets: list[Snippet], on_saved: Callable[[list[Snippet]], None]) -> None:
        self.snippets: list[Snippet] = copy.deepcopy(snippets)
        self.on_saved = on_saved
        self._open = self._built = False
        self._root = self._selected_index = self._tree = None
        self._filter_var = self._trigger_var = self._test_input_var = None
        self._test_status_lbl = self._text_editor = self._preview_text = None

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
        self._root.geometry("840x580")
        self._root.minsize(740, 500)
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
        ttk.Label(search_bar, text=t("snippets_editor.search", "Search:")).pack(side="left", padx=(0, 4))
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._refresh_list())
        ttk.Entry(search_bar, textvariable=self._filter_var).pack(side="left", fill="x", expand=True)

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

        self._tree.heading("trigger", text=t("snippets_editor.col_trigger", "Trigger"), anchor="w")
        self._tree.heading("preview", text=t("snippets_editor.col_preview", "Preview"), anchor="w")
        self._tree.column("trigger", width=120, stretch=False)
        self._tree.column("preview", width=180, stretch=True)
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        list_btns = ttk.Frame(left_frm)
        list_btns.pack(fill="x", pady=(6, 0))
        for txt, cmd, px in [
            (t("snippets_editor.btn_new", "+ New"), self._add_snippet, (0, 4)),
            (t("snippets_editor.btn_delete", "- Delete"), self._delete_snippet, 4),
            (t("snippets_editor.btn_duplicate", "Duplicate"), self._duplicate_snippet, 4),
        ]:
            ttk.Button(list_btns, text=txt, command=cmd).pack(side="left", padx=px)

        # ── RIGHT PANE: Multi-line Editor, Placeholders & Regex Test ──
        right_frm = ttk.Frame(paned, padding=5)
        paned.add(right_frm, weight=2)

        trig_frm = ttk.Frame(right_frm)
        trig_frm.pack(fill="x", pady=(0, 6))
        ttk.Label(trig_frm, text=t("snippets_editor.trigger_label", "Trigger word:"), font=("Segoe UI", 9, "bold")).pack(
            side="left", padx=(0, 8)
        )
        self._trigger_var = tk.StringVar()
        self._trigger_var.trace_add("write", lambda *_: self._on_editor_modified())
        ttk.Entry(trig_frm, textvariable=self._trigger_var, width=24).pack(side="left")
        ttk.Label(trig_frm, text=t("snippets_editor.trigger_hint", "e.g. @@, /sig, re:;d(\\d+)"), foreground="gray").pack(
            side="left", padx=8
        )

        ttk.Label(
            right_frm,
            text=t("snippets_editor.template_label", "Replacement template (supports multiple lines & placeholders):"),
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(4, 2))

        ed_frm = ttk.Frame(right_frm)
        ed_frm.pack(fill="both", expand=True)
        ed_scroll = ttk.Scrollbar(ed_frm, orient="vertical")
        self._text_editor = tk.Text(
            ed_frm, wrap="word", height=7, font=("Consolas", 10), yscrollcommand=ed_scroll.set
        )
        ed_scroll.config(command=self._text_editor.yview)
        ed_scroll.pack(side="right", fill="y")
        self._text_editor.pack(side="left", fill="both", expand=True)
        self._text_editor.bind("<KeyRelease>", lambda *_: self._on_editor_modified())

        # Placeholder Toolbar
        helper_box = ttk.LabelFrame(right_frm, text=t("snippets_editor.insert_placeholders", "Insert Placeholders"), padding=4)
        helper_box.pack(fill="x", pady=(4, 4))
        h_btns = ttk.Frame(helper_box)
        h_btns.pack(fill="x")

        def add_ph(text: str) -> None:
            if self._text_editor is not None:
                self._text_editor.insert(tk.INSERT, text)
                self._text_editor.focus_set()
                self._on_editor_modified()

        for label, val in _PLACEHOLDERS:
            ttk.Button(h_btns, text=label, command=lambda v=val: add_ph(v)).pack(side="left", padx=2)

        # Live Regex / Trigger Test Box
        test_box = ttk.LabelFrame(right_frm, text=t("snippets_editor.regex_test_label", "Live Trigger Test"), padding=4)
        test_box.pack(fill="x", pady=(0, 4))
        t_row = ttk.Frame(test_box)
        t_row.pack(fill="x")
        ttk.Label(t_row, text=t("snippets_editor.sample_input_label", "Test Input:")).pack(side="left", padx=(0, 4))
        self._test_input_var = tk.StringVar()
        self._test_input_var.trace_add("write", lambda *_: self._update_test_preview())
        ttk.Entry(t_row, textvariable=self._test_input_var, width=18).pack(side="left", fill="x", expand=True)
        self._test_status_lbl = ttk.Label(test_box, text="", font=("Segoe UI", 9))
        self._test_status_lbl.pack(anchor="w", pady=(2, 0))

        preview_box = ttk.LabelFrame(right_frm, text=t("snippets_editor.live_preview", "Live Output Preview"), padding=4)
        preview_box.pack(fill="x", pady=(0, 4))
        self._preview_text = tk.Text(
            preview_box, wrap="word", height=2, state="disabled", background="#f8f9fa", foreground="#212529", font=("Segoe UI", 9)
        )
        self._preview_text.pack(fill="x", expand=True)

        ttk.Button(
            right_frm, text=t("snippets_editor.btn_apply", "Apply Changes to Selected"), command=self._save_current_to_list
        ).pack(anchor="e")

        # ── BOTTOM TOOLBAR ──
        bot_bar = ttk.Frame(main_frm)
        bot_bar.pack(fill="x", pady=(6, 0))
        for txt, cmd, side, px in [
            (t("snippets_editor.btn_import", "Import JSON…"), self._import_json, "left", (0, 6)),
            (t("snippets_editor.btn_export", "Export JSON…"), self._export_json, "left", 6),
            (t("snippets_editor.btn_save_close", "Save & Close"), self._save_all_and_close, "right", 6),
            (t("snippets_editor.btn_cancel", "Cancel"), self._close, "right", (6, 0)),
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
        w, h = self._root.winfo_width(), self._root.winfo_height()
        x = (self._root.winfo_screenwidth() - w) // 2
        y = (self._root.winfo_screenheight() - h) // 3
        self._root.geometry(f"+{x}+{y}")

    def _refresh_list(self) -> None:
        if self._tree is None or self._filter_var is None:
            return
        filter_str = self._filter_var.get().strip().lower()
        self._tree.delete(*self._tree.get_children())
        badge = t("snippets_editor.regex_badge", "[Regex] ")
        for idx, s in enumerate(self.snippets):
            if filter_str and filter_str not in s.trigger.lower() and filter_str not in s.replacement.lower():
                continue
            is_reg = s.trigger.startswith("re:") or getattr(s, "is_regex", False)
            display_trig = f"{badge}{s.trigger}" if is_reg else s.trigger
            first_line = s.replacement.splitlines()[0] if s.replacement.splitlines() else ""
            if len(first_line) > 35:
                first_line = first_line[:32] + "..."
            self._tree.insert("", "end", iid=str(idx), values=(display_trig, first_line))

    def _load_snippet_to_editor(self, idx: int) -> None:
        s = self.snippets[idx]
        if self._trigger_var:
            self._trigger_var.set(s.trigger)
        if self._text_editor:
            self._text_editor.delete("1.0", tk.END)
            self._text_editor.insert("1.0", s.replacement)
        if self._test_input_var:
            # Set intelligent default sample
            if s.trigger.startswith("re:;d"):
                self._test_input_var.set(";d25")
            elif not s.trigger.startswith("re:"):
                self._test_input_var.set(s.trigger)
            else:
                self._test_input_var.set("")
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
        raw = self._text_editor.get("1.0", tk.END).rstrip("\n")
        rendered = render_template(raw)
        clean_text, cursor_offset = parse_cursor_placeholder(rendered)
        cursor_info = f" [Caret |< {cursor_offset} chars]" if cursor_offset is not None else ""
        self._preview_text.config(state="normal")
        self._preview_text.delete("1.0", tk.END)
        self._preview_text.insert("1.0", f"{clean_text}{cursor_info}")
        self._preview_text.config(state="disabled")

    def _update_test_preview(self) -> None:
        if not self._test_status_lbl or not self._trigger_var or not self._text_editor:
            return
        trig, repl = self._trigger_var.get().strip(), self._text_editor.get("1.0", tk.END).rstrip("\n")
        sample = self._test_input_var.get().strip() if self._test_input_var else ""
        if not trig or not sample:
            self._test_status_lbl.config(text="", foreground="gray")
            return
        if trig.startswith("re:"):
            ok, res = preview_regex_expansion(trig, repl, sample)
            color = "#2b8a3e" if ok else ("gray" if res == "No match" else "#c92a2a")
            txt = t("snippets_editor.regex_test_matched", "Matched: {result}", result=res) if ok else (t("snippets_editor.regex_test_no_match", "No match") if res == "No match" else res)
            self._test_status_lbl.config(text=txt, foreground=color)
        else:
            matched = (sample == trig)
            res = render_template(repl) if matched else ""
            txt = t("snippets_editor.regex_test_matched", "Matched: {result}", result=res) if matched else t("snippets_editor.regex_test_no_match", "No match")
            self._test_status_lbl.config(text=txt, foreground="#2b8a3e" if matched else "gray")

    def _validate_trigger(self, trig: str) -> bool:
        if not trig:
            messagebox.showwarning(t("app_name", "Ravaan"), t("snippets_editor.empty_trigger_warn", "Trigger cannot be empty"), parent=self._root)
            return False
        if trig.startswith("re:"):
            is_valid, err = validate_regex_trigger(trig)
            if not is_valid:
                messagebox.showerror(t("snippets_editor.regex_error_title", "Regex Error"), t("snippets_editor.regex_error_msg", "Invalid regex:\n{err}", err=err), parent=self._root)
                return False
        return True

    def _save_current_to_list(self) -> None:
        if self._trigger_var is None or self._text_editor is None:
            return
        trig = self._trigger_var.get().strip()
        repl = self._text_editor.get("1.0", tk.END).rstrip("\n")
        if not self._validate_trigger(trig):
            return

        is_reg = trig.startswith("re:")
        snip = Snippet(trigger=trig, replacement=repl, is_regex=is_reg)
        if self._selected_index is not None and 0 <= self._selected_index < len(self.snippets):
            self.snippets[self._selected_index] = snip
        else:
            self.snippets.append(snip)
            self._selected_index = len(self.snippets) - 1

        self._refresh_list()
        self._select_index(self._selected_index)

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
            else:
                if self._trigger_var:
                    self._trigger_var.set("")
                if self._text_editor:
                    self._text_editor.delete("1.0", tk.END)
                self._update_preview()
                self._update_test_preview()

    def _duplicate_snippet(self) -> None:
        if self._selected_index is not None and 0 <= self._selected_index < len(self.snippets):
            cur = self.snippets[self._selected_index]
            dup = Snippet(trigger=f"{cur.trigger}_copy", replacement=cur.replacement, is_regex=getattr(cur, "is_regex", False))
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

    def _sync_current(self) -> None:
        if self._selected_index is not None and self._trigger_var and self._text_editor:
            trig = self._trigger_var.get().strip()
            if trig:
                repl = self._text_editor.get("1.0", tk.END).rstrip("\n")
                is_reg = trig.startswith("re:")
                self.snippets[self._selected_index] = Snippet(trigger=trig, replacement=repl, is_regex=is_reg)

    def _export_json(self) -> None:
        self._sync_current()
        export_snippets_dialog(self._root, self.snippets)

    def _save_all_and_close(self) -> None:
        self._sync_current()
        for s in self.snippets:
            if s.trigger.startswith("re:"):
                valid, err = validate_regex_trigger(s.trigger)
                if not valid:
                    messagebox.showerror(
                        t("snippets_editor.regex_error_title", "Regex Validation Error"),
                        t("snippets_editor.regex_error_msg", "Invalid or unsafe regex pattern:\n{err}", err=err),
                        parent=self._root,
                    )
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
