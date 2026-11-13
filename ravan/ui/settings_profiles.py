"""Per-App Smart Profiles section for SettingsWindow."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from ravan.core.i18n import is_rtl, t
from ravan.core.profiles import (
    PRESET_OVERRIDES,
    PROFILE_BOOL_FIELDS,
    VALID_PROFILE_LAYOUTS,
    VALID_PROFILE_PRESETS,
    normalize_exe_key,
    sanitize_app_profiles,
)
from ravan.ui.settings_builder import _get_win_palette, _make_card, _make_section_banner

_TRISTATE_VALUES = ("inherit", "on", "off")


def _bool_to_state(val: bool | None) -> str:
    if val is True:
        return "on"
    if val is False:
        return "off"
    return "inherit"


def _state_to_bool(state: str) -> bool | None:
    s = (state or "inherit").strip().lower()
    if s == "on":
        return True
    if s == "off":
        return False
    return None


def _fmt_flag(val: bool | None) -> str:
    if val is True:
        return "✓ On"
    if val is False:
        return "✕ Off"
    return "— Global"


def build_profiles_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, int]) -> int:
    """Build the Per-App Smart Profiles configuration tab."""
    rtl = is_rtl()
    palette = _get_win_palette(win)
    align = "e" if rtl else "w"
    side = "right" if rtl else "left"
    frm.columnconfigure(0, weight=1)

    sub = (
        "تنظیم رفتار هوشمند روان بر اساس برنامه فعال (مثلاً غیرفعال‌سازی نیم‌فاصله در VS Code و فعال‌سازی در Word/تلگرام)"
        if rtl
        else "Customize Ravaan automation per application (e.g. disable formatting in code editors, optimize chat & formal apps)"
    )
    banner = _make_section_banner(
        frm,
        "🎯",
        t("settings.tab_profiles", "App Profiles"),
        sub,
        palette,
        rtl,
    )
    banner.pack(fill="x", pady=(0, 8))

    win._managed_app_profiles = sanitize_app_profiles(getattr(win.cfg, "app_profiles", {}))

    master_card = _make_card(frm, t("settings.profiles_master_title", "Profile Engine"), padding=10)
    master_card.pack(fill="x", pady=(0, 8))
    win._app_profiles_enabled_var = tk.BooleanVar(
        value=bool(getattr(win.cfg, "app_profiles_enabled", True))
    )
    ttk.Checkbutton(
        master_card,
        text=t(
            "settings.profiles_enable",
            "Enable Per-App Smart Profiles (includes automatic IDE/terminal safety defaults)",
        ),
        variable=win._app_profiles_enabled_var,
    ).pack(anchor=align)

    # Configured rules table
    list_card = _make_card(frm, t("settings.profiles_list_title", "Configured App Rules"), padding=10)
    list_card.pack(fill="both", expand=True, pady=(0, 8))

    cols = ("exe", "preset", "zwnj", "ortho", "punct", "pred", "toolbar", "layout")
    tree = ttk.Treeview(list_card, columns=cols, show="headings", height=5)
    headers = {
        "exe": t("settings.prof_col_exe", "App (.exe)"),
        "preset": t("settings.prof_col_preset", "Preset"),
        "zwnj": t("settings.prof_col_zwnj", "ZWNJ"),
        "ortho": t("settings.prof_col_ortho", "Ortho"),
        "punct": t("settings.prof_col_punct", "Punct"),
        "pred": t("settings.prof_col_pred", "Predict"),
        "toolbar": t("settings.prof_col_toolbar", "Toolbar"),
        "layout": t("settings.prof_col_layout", "Layout"),
    }
    widths = {"exe": 125, "preset": 70, "zwnj": 65, "ortho": 65, "punct": 65, "pred": 65, "toolbar": 65, "layout": 65}
    for col in cols:
        tree.heading(col, text=headers[col])
        tree.column(col, width=widths[col], anchor="center" if col != "exe" else "w")
    tree.pack(fill="both", expand=True, pady=(0, 6))
    win._profiles_tree = tree

    # Editor card
    edit_card = _make_card(frm, t("settings.profiles_editor_title", "Add / Edit App Profile"), padding=10)
    edit_card.pack(fill="x", pady=(0, 8))

    win._profile_exe_var = tk.StringVar(value="")
    win._profile_preset_var = tk.StringVar(value="code")
    win._profile_layout_var = tk.StringVar(value="none")
    win._profile_bool_vars: dict[str, tk.StringVar] = {
        fname: tk.StringVar(value="inherit") for fname in PROFILE_BOOL_FIELDS
    }

    row1 = ttk.Frame(edit_card)
    row1.pack(fill="x", pady=(0, 6))
    ttk.Label(row1, text=t("settings.prof_exe_label", "Executable:")).pack(side=side, padx=(0, 6))
    ttk.Entry(row1, textvariable=win._profile_exe_var, width=22).pack(side=side, padx=(0, 10))
    ttk.Label(row1, text=t("settings.prof_preset_label", "Preset:")).pack(side=side, padx=(0, 6))
    preset_cb = ttk.Combobox(
        row1,
        textvariable=win._profile_preset_var,
        values=list(VALID_PROFILE_PRESETS),
        state="readonly",
        width=12,
    )
    preset_cb.pack(side=side, padx=(0, 10))

    ttk.Label(row1, text=t("settings.prof_layout_label", "Auto Layout:")).pack(side=side, padx=(0, 6))
    ttk.Combobox(
        row1,
        textvariable=win._profile_layout_var,
        values=list(VALID_PROFILE_LAYOUTS),
        state="readonly",
        width=8,
    ).pack(side=side)

    def _apply_preset_to_editor(_e: Any = None) -> None:
        preset = win._profile_preset_var.get().strip().lower()
        ov = PRESET_OVERRIDES.get(preset)
        if not ov:
            return
        for fname in PROFILE_BOOL_FIELDS:
            win._profile_bool_vars[fname].set(_bool_to_state(ov.get(fname)))
        win._profile_layout_var.set(str(ov.get("preferred_layout", "none")))

    preset_cb.bind("<<ComboboxSelected>>", _apply_preset_to_editor)

    grid_frm = ttk.Frame(edit_card)
    grid_frm.pack(fill="x", pady=(2, 6))
    labels_map = {
        "auto_zwnj": t("settings.prof_flag_zwnj", "Auto-ZWNJ"),
        "orthography_guard": t("settings.prof_flag_ortho", "Orthography Guard"),
        "smart_punctuation": t("settings.prof_flag_punct", "Smart Punctuation"),
        "prediction_enabled": t("settings.prof_flag_pred", "Word Prediction"),
        "autofix_enabled": t("settings.prof_flag_autofix", "Auto-Fix Layout"),
        "selection_toolbar": t("settings.prof_flag_toolbar", "Selection Toolbar"),
    }
    for idx, fname in enumerate(PROFILE_BOOL_FIELDS):
        r, c = divmod(idx, 3)
        cell = ttk.Frame(grid_frm)
        cell.grid(row=r, column=c, sticky="ew", padx=6, pady=3)
        grid_frm.columnconfigure(c, weight=1)
        ttk.Label(cell, text=labels_map[fname], width=17).pack(side="left")
        ttk.Combobox(
            cell,
            textvariable=win._profile_bool_vars[fname],
            values=list(_TRISTATE_VALUES),
            state="readonly",
            width=9,
        ).pack(side="left")

    def _refresh_tree() -> None:
        for item in tree.get_children():
            tree.delete(item)
        for exe, cfg_map in sorted(win._managed_app_profiles.items()):
            tree.insert(
                "",
                "end",
                values=(
                    exe,
                    cfg_map.get("preset", "custom"),
                    _fmt_flag(cfg_map.get("auto_zwnj")),
                    _fmt_flag(cfg_map.get("orthography_guard")),
                    _fmt_flag(cfg_map.get("smart_punctuation")),
                    _fmt_flag(cfg_map.get("prediction_enabled")),
                    _fmt_flag(cfg_map.get("selection_toolbar")),
                    cfg_map.get("preferred_layout", "none"),
                ),
            )

    win._refresh_profiles_tree = _refresh_tree

    def _on_select(_e: Any = None) -> None:
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        if not vals:
            return
        exe = str(vals[0])
        entry = win._managed_app_profiles.get(exe)
        if not entry:
            return
        win._profile_exe_var.set(exe)
        win._profile_preset_var.set(entry.get("preset", "custom"))
        win._profile_layout_var.set(entry.get("preferred_layout", "none"))
        for fname in PROFILE_BOOL_FIELDS:
            win._profile_bool_vars[fname].set(_bool_to_state(entry.get(fname)))

    tree.bind("<<TreeviewSelect>>", _on_select)

    def _add_or_update() -> None:
        exe = normalize_exe_key(win._profile_exe_var.get())
        if not exe:
            messagebox.showwarning("Ravaan", t("settings.prof_exe_required", "Enter an executable name (e.g. code.exe)."), parent=win._root)
            return
        entry: dict[str, Any] = {
            "preset": win._profile_preset_var.get().strip().lower() or "custom",
            "preferred_layout": win._profile_layout_var.get().strip().lower() or "none",
        }
        for fname in PROFILE_BOOL_FIELDS:
            entry[fname] = _state_to_bool(win._profile_bool_vars[fname].get())
        win._managed_app_profiles[exe] = entry
        _refresh_tree()
        for iid in tree.get_children():
            vals = tree.item(iid, "values")
            if vals and str(vals[0]) == exe:
                try:
                    tree.selection_set(iid)
                except Exception:
                    pass
                break

    def _remove_selected() -> None:
        sel = tree.selection()
        vals = tree.item(sel[0], "values") if sel else ()
        target = str(vals[0]) if vals else normalize_exe_key(win._profile_exe_var.get())
        if target and target in win._managed_app_profiles:
            del win._managed_app_profiles[target]
            _refresh_tree()

    def _fill_quick(exe_sample: str, preset_name: str) -> None:
        win._profile_exe_var.set(exe_sample)
        win._profile_preset_var.set(preset_name)
        _apply_preset_to_editor()

    btn_bar = ttk.Frame(edit_card)
    btn_bar.pack(fill="x", pady=(4, 0))
    ttk.Button(btn_bar, text=t("settings.prof_btn_apply", "✓ Save / Update Rule"), command=_add_or_update).pack(
        side=side, padx=3
    )
    ttk.Button(btn_bar, text=t("settings.prof_btn_remove", "🗑️ Remove Rule"), command=_remove_selected).pack(
        side=side, padx=3
    )
    ttk.Button(btn_bar, text="VS Code (code)", command=lambda: _fill_quick("code.exe", "code")).pack(
        side=side, padx=3
    )
    ttk.Button(btn_bar, text="Telegram (chat)", command=lambda: _fill_quick("telegram.exe", "chat")).pack(
        side=side, padx=3
    )
    ttk.Button(btn_bar, text="Word (formal)", command=lambda: _fill_quick("winword.exe", "formal")).pack(
        side=side, padx=3
    )

    _refresh_tree()

    bottom = ttk.Frame(frm)
    bottom.pack(fill="x", pady=(4, 4))
    ttk.Button(
        bottom,
        text=t("settings.reset_tab_btn", "↺ Reset tab defaults"),
        command=lambda: win._reset_tab_defaults("profiles"),
    ).pack(side=side)
    return start_row + 1
