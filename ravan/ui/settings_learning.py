"""Learning Manager, Personal Corpus Import, and ZWNJ/Orthography Blacklist UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from ravan.core.i18n import is_rtl, t
from ravan.core.orthography import add_blacklist_token
from ravan.ui.settings_builder import _get_win_palette, _make_card


def _get_engine(win: Any):
    engine = getattr(win, "learning_engine", None)
    if engine is not None:
        return engine
    cached = getattr(win, "_cached_learning_engine", None)
    if cached is not None:
        return cached
    from ravan.core.learning import UserLearningEngine

    cached = UserLearningEngine(
        auto_load=True,
        learning_enabled=bool(getattr(win.cfg, "learning_enabled", True)),
    )
    win._cached_learning_engine = cached
    return cached


def build_learning_and_exceptions_card(
    win: Any,
    parent_frm: ttk.Frame,
    row: int,
    pad: dict[str, int],
) -> int:
    """Build Learning Manager, Corpus Import, and ZWNJ/Orthography Blacklist inside Prediction tab."""
    rtl = is_rtl()
    palette = _get_win_palette(win)
    align = "e" if rtl else "w"
    side = "right" if rtl else "left"

    title = (
        "🧠 مدیریت واژگان یادگرفته‌شده، آموزش از متن و استثناهای نیم‌فاصله/املا"
        if rtl
        else "🧠 Learning Manager, Corpus Import & ZWNJ Blacklist"
    )
    card = _make_card(parent_frm, title, padding=12)
    card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    card.columnconfigure(0, weight=1)
    row += 1

    # 1. Search + stats header
    top_bar = ttk.Frame(card)
    top_bar.pack(fill="x", pady=(0, 6))

    win._learning_search_var = tk.StringVar(value="")
    win._learning_stats_var = tk.StringVar(value="")

    ttk.Label(top_bar, text=t("settings.learn_filter", "Filter:")).pack(side=side, padx=(0, 6))
    search_entry = ttk.Entry(top_bar, textvariable=win._learning_search_var, width=22)
    search_entry.pack(side=side, padx=(0, 8))
    ttk.Label(top_bar, textvariable=win._learning_stats_var, style="Sub.TLabel").pack(side=side, padx=4)

    # 2. Learned words table
    tree = ttk.Treeview(card, columns=("word", "weight"), show="headings", height=5)
    tree.heading("word", text=t("settings.learn_col_word", "Learned Word"))
    tree.heading("weight", text=t("settings.learn_col_weight", "Frequency / Score"))
    tree.column("word", width=260, anchor="e" if rtl else "w")
    tree.column("weight", width=110, anchor="center")
    tree.pack(fill="x", pady=(0, 6))
    win._learning_tree = tree

    def _refresh_learned() -> None:
        try:
            eng = _get_engine(win)
            query = win._learning_search_var.get()
            items = eng.list_learned_words(query=query, limit=120)
            for item in tree.get_children():
                tree.delete(item)
            for word, score in items:
                tree.insert("", "end", values=(word, f"{score:.1f}"))
            total = len(getattr(eng, "word_counts", {}))
            win._learning_stats_var.set(
                t("settings.learn_count", "{total} words learned", total=total)
            )
        except Exception:  # noqa: BLE001
            pass

    win._refresh_learning_list = _refresh_learned
    search_entry.bind("<KeyRelease>", lambda _e: _refresh_learned())

    def _forget_selected() -> None:
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        if not vals:
            return
        word = str(vals[0])
        eng = _get_engine(win)
        if eng.forget_word(word):
            _refresh_learned()

    def _ignore_selected() -> None:
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        if not vals:
            return
        word = str(vals[0])
        eng = _get_engine(win)
        eng.exclude_word(word, cfg=win.cfg)
        _refresh_learned()

    def _import_corpus() -> None:
        path = filedialog.askopenfilename(
            parent=win._root,
            title=t("settings.import_corpus_title", "Select Personal Text Corpus (.txt)"),
            filetypes=[("Text files", "*.txt *.md"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            eng = _get_engine(win)
            stats = eng.import_corpus_file(path)
            _refresh_learned()
            messagebox.showinfo(
                "Ravaan",
                t(
                    "settings.import_corpus_done",
                    "Imported {unique} unique words ({total} tokens, {trans} phrases).",
                    unique=stats["unique_words"],
                    total=stats["words_added"],
                    trans=stats["transitions_added"],
                ),
                parent=win._root,
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ravaan", str(exc), parent=win._root)

    action_row = ttk.Frame(card)
    action_row.pack(fill="x", pady=(0, 8))
    ttk.Button(
        action_row,
        text=t("settings.learn_btn_refresh", "🔄 Refresh"),
        command=_refresh_learned,
    ).pack(side=side, padx=3)
    ttk.Button(
        action_row,
        text=t("settings.learn_btn_forget", "🗑️ Forget Selected"),
        command=_forget_selected,
    ).pack(side=side, padx=3)
    ttk.Button(
        action_row,
        text=t("settings.learn_btn_ignore", "🚫 Block Word"),
        command=_ignore_selected,
    ).pack(side=side, padx=3)
    ttk.Button(
        action_row,
        text=t("settings.learn_btn_import", "📥 Import Text Corpus (.txt)"),
        command=_import_corpus,
    ).pack(side=side, padx=3)

    # 3. Auto-Learn ZWNJ & Orthography Exclusion Blacklist
    ttk.Separator(card, orient="horizontal").pack(fill="x", pady=6)
    ttk.Label(
        card,
        text=t(
            "settings.zwnj_blacklist_label",
            "Auto-ZWNJ & Orthography Exception List (never auto-modified):",
        ),
    ).pack(anchor=align, pady=(0, 4))

    win._managed_zwnj_blacklist = list(getattr(win.cfg, "zwnj_orthography_blacklist", []))

    bl_box = tk.Listbox(
        card,
        height=3,
        bg=palette.input_bg,
        fg=palette.fg,
        selectbackground=palette.highlight,
        selectforeground=palette.highlight_fg,
        relief="flat",
        highlightthickness=1,
        highlightbackground=palette.border,
    )
    bl_box.pack(fill="x", pady=(0, 4))
    win._zwnj_bl_listbox = bl_box

    def _refresh_blacklist_box() -> None:
        bl_box.delete(0, tk.END)
        for item in win._managed_zwnj_blacklist:
            bl_box.insert(tk.END, item)

    win._refresh_zwnj_blacklist_box = _refresh_blacklist_box
    _refresh_blacklist_box()

    win._zwnj_bl_entry_var = tk.StringVar(value="")
    bl_ctrl = ttk.Frame(card)
    bl_ctrl.pack(fill="x")
    ttk.Entry(bl_ctrl, textvariable=win._zwnj_bl_entry_var, width=24).pack(side=side, padx=(0, 6))

    def _add_bl() -> None:
        tok = win._zwnj_bl_entry_var.get().strip()
        if not tok:
            return
        win._managed_zwnj_blacklist = add_blacklist_token(win._managed_zwnj_blacklist, tok)
        win._zwnj_bl_entry_var.set("")
        _refresh_blacklist_box()

    def _remove_bl() -> None:
        sel = bl_box.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(win._managed_zwnj_blacklist):
            del win._managed_zwnj_blacklist[idx]
            _refresh_blacklist_box()

    ttk.Button(bl_ctrl, text=t("settings.btn_add_exception", "+ Add Exception"), command=_add_bl).pack(
        side=side, padx=3
    )
    ttk.Button(bl_ctrl, text=t("settings.btn_remove_exception", "✓ Remove Selected"), command=_remove_bl).pack(
        side=side, padx=3
    )

    if getattr(win, "learning_engine", None) is not None:
        _refresh_learned()
    elif getattr(win, "_root", None) is not None:
        win._root.after_idle(_refresh_learned)

    return row
