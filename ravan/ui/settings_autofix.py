"""Auto-Fix settings tab and recent corrections manager."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.config import hotkey_to_text
from ravan.core.i18n import is_rtl, t


def build_autofix_section(win: Any, parent: ttk.Frame, start_row: int, pad: dict[str, int]) -> int:
    """Build the Settings tab for Automatic Wrong-Layout Correction."""
    rtl = is_rtl()
    side = "right" if rtl else "left"

    # 1. Mode selector
    mode_frame = ttk.LabelFrame(
        parent,
        text=t("settings.autofix_mode_title", "Automatic Layout Correction Mode"),
        padding=8,
    )
    mode_frame.pack(fill="x", pady=6)

    win._autofix_mode_var = tk.StringVar(value=getattr(win.cfg, "autofix_mode", "safe"))

    modes = [
        ("off", t("settings.autofix_off", "Off — Disabled")),
        ("safe", t("settings.autofix_safe", "Safe (Default) — Fix only dictionary words")),
        ("aggressive", t("settings.autofix_aggressive", "Aggressive — Fix multi-word runs & context")),
    ]
    for val, lbl in modes:
        rb = ttk.Radiobutton(
            mode_frame,
            text=lbl,
            value=val,
            variable=win._autofix_mode_var,
        )
        rb.pack(anchor="w" if not rtl else "e", pady=2)

    # 2. Auto layout switch
    layout_frame = ttk.LabelFrame(
        parent,
        text=t("settings.auto_layout_title", "Windows Keyboard Layout Switching"),
        padding=8,
    )
    layout_frame.pack(fill="x", pady=6)

    win._auto_layout_switch_var = tk.BooleanVar(value=bool(getattr(win.cfg, "auto_layout_switch", False)))
    cb_layout = ttk.Checkbutton(
        layout_frame,
        text=t("settings.auto_layout_enable", "Switch active Windows keyboard layout when wrong layout is detected"),
        variable=win._auto_layout_switch_var,
    )
    cb_layout.pack(anchor="w" if not rtl else "e", pady=2)

    sub_frame = ttk.Frame(layout_frame)
    sub_frame.pack(fill="x", pady=4)
    ttk.Label(sub_frame, text=t("settings.auto_layout_mode_label", "Action:")).pack(side=side, padx=(0, 6) if not rtl else (6, 0))

    win._auto_layout_mode_var = tk.StringVar(value=getattr(win.cfg, "auto_layout_mode", "fix_only"))
    mode_combo = ttk.Combobox(
        sub_frame,
        textvariable=win._auto_layout_mode_var,
        values=["fix_only", "switch_only", "fix_and_switch"],
        state="readonly",
        width=18,
    )
    mode_combo.pack(side=side)

    # 3. Global Undo Hotkey
    undo_frame = ttk.LabelFrame(
        parent,
        text=t("settings.global_undo_title", "Global Undo Hotkey"),
        padding=8,
    )
    undo_frame.pack(fill="x", pady=6)

    default_undo = getattr(win.cfg, "global_undo_hotkey", None)
    win._global_undo_var = tk.StringVar(
        value=hotkey_to_text(default_undo) if default_undo else "Ctrl+Shift+Pause"
    )
    u_row = ttk.Frame(undo_frame)
    u_row.pack(fill="x")
    ttk.Label(u_row, text=t("settings.undo_shortcut_label", "Undo correction (up to 50 steps):")).pack(side=side, padx=(0, 6) if not rtl else (6, 0))
    ttk.Entry(u_row, textvariable=win._global_undo_var, width=20).pack(side=side)

    # 4. Recent Corrections & Blacklist
    corr_frame = ttk.LabelFrame(
        parent,
        text=t("settings.recent_corrections_title", "Recent Corrections & Blacklist"),
        padding=8,
    )
    corr_frame.pack(fill="both", expand=True, pady=6)

    tree_cols = ("original", "fixed", "status")
    tree = ttk.Treeview(corr_frame, columns=tree_cols, show="headings", height=5)
    tree.heading("original", text=t("settings.col_original", "Typed Word"))
    tree.heading("fixed", text=t("settings.col_fixed", "Auto-Fixed"))
    tree.heading("status", text=t("settings.col_status", "Status"))
    tree.column("original", width=120)
    tree.column("fixed", width=120)
    tree.column("status", width=90)
    tree.pack(fill="both", expand=True, pady=(0, 6))

    win._autofix_tree = tree

    # Populate blacklist and sample recent records
    blacklist_set = {(p[0].lower(), p[1].lower()) for p in getattr(win.cfg, "autofix_blacklist", []) if len(p) >= 2}
    for orig, fixed in blacklist_set:
        tree.insert("", "end", values=(orig, fixed, t("settings.blacklisted", "Blacklisted")))

    btn_row = ttk.Frame(corr_frame)
    btn_row.pack(fill="x")

    def _blacklist_selected() -> None:
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        if vals and len(vals) >= 2:
            orig, fixed = vals[0].strip().lower(), vals[1].strip().lower()
            if not hasattr(win, "_managed_blacklist"):
                win._managed_blacklist = list(getattr(win.cfg, "autofix_blacklist", []))
            if [orig, fixed] not in win._managed_blacklist:
                win._managed_blacklist.append([orig, fixed])
            tree.item(sel[0], values=(orig, fixed, t("settings.blacklisted", "Blacklisted")))

    def _remove_selected() -> None:
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        if vals and len(vals) >= 2:
            orig, fixed = vals[0].strip().lower(), vals[1].strip().lower()
            if not hasattr(win, "_managed_blacklist"):
                win._managed_blacklist = list(getattr(win.cfg, "autofix_blacklist", []))
            win._managed_blacklist = [p for p in win._managed_blacklist if [p[0].lower(), p[1].lower()] != [orig, fixed]]
            tree.delete(sel[0])

    ttk.Button(
        btn_row,
        text=t("settings.btn_blacklist", "⛔ Blacklist Selected Pair"),
        command=_blacklist_selected,
    ).pack(side=side, padx=(0, 6) if not rtl else (6, 0))

    ttk.Button(
        btn_row,
        text=t("settings.btn_remove_blacklist", "✓ Remove from Blacklist"),
        command=_remove_selected,
    ).pack(side=side)

    return start_row + 1
