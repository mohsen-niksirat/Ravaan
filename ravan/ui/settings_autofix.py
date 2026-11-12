"""Auto-Fix settings tab and recent corrections manager."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.config import hotkey_to_text
from ravan.core.i18n import is_rtl, t
from ravan.ui.settings_builder import _get_win_palette, _make_section_banner


def build_autofix_section(win: Any, parent: ttk.Frame, start_row: int, pad: dict[str, int]) -> int:
    """Build the Settings tab for Automatic Wrong-Layout Correction."""
    rtl = is_rtl()
    palette = _get_win_palette(win)
    side = "right" if rtl else "left"

    sub = (
        "تشخیص و اصلاح خودکار تایپ با کیبورد اشتباه (مثلاً sghl ← سلام) همراه با تغییر خودکار زبان ویندوز"
        if rtl
        else "Automatically detect and convert words typed in the wrong keyboard layout (e.g. sghl → سلام)"
    )
    banner = _make_section_banner(
        parent,
        "⚡",
        t("settings.tab_autofix", "Auto-Fix"),
        sub,
        palette,
        rtl,
    )
    banner.pack(fill="x", pady=(0, 8))

    # 1. Mode selector
    mode_frame = ttk.LabelFrame(
        parent,
        text=f"  {t('settings.autofix_mode_title', 'Automatic Layout Correction Mode')}  ",
        padding=12,
    )
    mode_frame.pack(fill="x", pady=(0, 8))

    initial_af_mode = getattr(win.cfg, "autofix_mode", "safe")
    win._autofix_master_var = tk.BooleanVar(value=initial_af_mode != "off")
    win._autofix_mode_var = tk.StringVar(value=initial_af_mode)

    master_cb = ttk.Checkbutton(
        mode_frame,
        text=t("settings.autofix_master_enable", "Enable automatic wrong-layout correction (sghl → سلام)"),
        variable=win._autofix_master_var,
    )
    master_cb.pack(anchor="w" if not rtl else "e", pady=(0, 6))

    rb_container = ttk.Frame(mode_frame)
    rb_container.pack(fill="x", padx=(18, 0) if not rtl else (0, 18))

    modes = [
        ("off", t("settings.autofix_off", "Off — Disabled")),
        ("safe", t("settings.autofix_safe", "Safe (Default) — Fix only dictionary words")),
        ("aggressive", t("settings.autofix_aggressive", "Aggressive — Fix multi-word runs & context")),
    ]
    for val, lbl in modes:
        rb = ttk.Radiobutton(
            rb_container,
            text=lbl,
            value=val,
            variable=win._autofix_mode_var,
        )
        rb.pack(anchor="w" if not rtl else "e", pady=2)

    _syncing_af = False

    def _sync_af_from_master(*_):
        nonlocal _syncing_af
        if _syncing_af:
            return
        _syncing_af = True
        try:
            if win._autofix_master_var.get():
                if win._autofix_mode_var.get() == "off":
                    win._autofix_mode_var.set("safe")
            else:
                win._autofix_mode_var.set("off")
        finally:
            _syncing_af = False

    def _sync_af_from_mode(*_):
        nonlocal _syncing_af
        if _syncing_af:
            return
        _syncing_af = True
        try:
            m = win._autofix_mode_var.get()
            win._autofix_master_var.set(m != "off")
        finally:
            _syncing_af = False

    win._autofix_master_var.trace_add("write", _sync_af_from_master)
    win._autofix_mode_var.trace_add("write", _sync_af_from_mode)

    from ravan.ui.tooltip import ToolTip

    ex_autofix = t(
        "settings.autofix_example",
        "Example: Typing 'sghl ' in English layout auto-converts to 'سلام '",
    )
    ex_lbl = ttk.Label(
        mode_frame,
        text=f"↳ {ex_autofix}",
        style="Sub.TLabel",
    )
    ex_lbl.pack(anchor="w" if not rtl else "e", padx=10, pady=(4, 2))
    ToolTip(ex_lbl, ex_autofix)

    # 2. Auto layout switch
    layout_frame = ttk.LabelFrame(
        parent,
        text=f"  {t('settings.auto_layout_title', 'Windows Keyboard Layout Switching')}  ",
        padding=12,
    )
    layout_frame.pack(fill="x", pady=(0, 8))

    win._auto_layout_switch_var = tk.BooleanVar(value=bool(getattr(win.cfg, "auto_layout_switch", False)))
    cb_layout = ttk.Checkbutton(
        layout_frame,
        text=t("settings.auto_layout_enable", "Switch active Windows keyboard layout when wrong layout is detected"),
        variable=win._auto_layout_switch_var,
    )
    cb_layout.pack(anchor="w" if not rtl else "e", pady=2)

    sub_frame = ttk.Frame(layout_frame)
    sub_frame.pack(fill="x", pady=6)
    ttk.Label(sub_frame, text=t("settings.auto_layout_mode_label", "Action:")).pack(
        side=side, padx=(0, 6) if not rtl else (6, 0)
    )

    win._auto_layout_mode_var = tk.StringVar(value=getattr(win.cfg, "auto_layout_mode", "fix_only"))
    mode_combo = ttk.Combobox(
        sub_frame,
        textvariable=win._auto_layout_mode_var,
        values=["fix_only", "switch_only", "fix_and_switch"],
        state="readonly",
        width=20,
    )
    mode_combo.pack(side=side)

    # 3. Global Undo Hotkey
    undo_frame = ttk.LabelFrame(
        parent,
        text=f"  {t('settings.global_undo_title', 'Global Undo Hotkey')}  ",
        padding=12,
    )
    undo_frame.pack(fill="x", pady=(0, 8))

    default_undo = getattr(win.cfg, "global_undo_hotkey", None)
    win._global_undo_var = tk.StringVar(
        value=hotkey_to_text(default_undo) if default_undo else "Ctrl+Shift+Pause"
    )
    u_row = ttk.Frame(undo_frame)
    u_row.pack(fill="x")
    ttk.Label(u_row, text=t("settings.undo_shortcut_label", "Undo correction (up to 50 steps):")).pack(
        side=side, padx=(0, 6) if not rtl else (6, 0)
    )
    ttk.Entry(u_row, textvariable=win._global_undo_var, width=22, justify="center").pack(side=side)

    # 4. Recent Corrections & Blacklist
    corr_frame = ttk.LabelFrame(
        parent,
        text=f"  {t('settings.recent_corrections_title', 'Recent Corrections & Blacklist')}  ",
        padding=12,
    )
    corr_frame.pack(fill="both", expand=True, pady=(0, 8))

    tree_cols = ("original", "fixed", "status")
    tree = ttk.Treeview(corr_frame, columns=tree_cols, show="headings", height=5)
    tree.heading("original", text=t("settings.col_original", "Typed Word"))
    tree.heading("fixed", text=t("settings.col_fixed", "Auto-Fixed"))
    tree.heading("status", text=t("settings.col_status", "Status"))
    tree.column("original", width=130)
    tree.column("fixed", width=130)
    tree.column("status", width=100)
    tree.pack(fill="both", expand=True, pady=(0, 8))

    win._autofix_tree = tree

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

    bottom_frame = ttk.Frame(parent)
    bottom_frame.pack(fill="x", pady=(4, 4))
    ttk.Button(
        bottom_frame,
        text=t("settings.reset_defaults", "↺ Reset Defaults"),
        command=lambda: win._reset_tab_defaults("autofix"),
    ).pack(side="left" if rtl else "right")

    return start_row + 1
