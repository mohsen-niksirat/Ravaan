"""UI section builder functions for SettingsWindow."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.config import hotkey_to_text
from ravan.core.i18n import is_rtl, t


def _bind_live_capture(entry: ttk.Entry, var: tk.StringVar) -> None:
    def on_key(event: Any) -> str:
        if event.keysym in ("BackSpace", "Delete"):
            var.set("")
            return "break"
        if event.keysym in (
            "Control_L", "Control_R", "Alt_L", "Alt_R", "Shift_L", "Shift_R", "Win_L", "Win_R"
        ):
            return "break"
        mods = []
        if event.state & 0x0004:
            mods.append("Ctrl")
        if event.state & 0x20000 or event.state & 0x0008 or event.state & 0x0080:
            mods.append("Alt")
        if event.state & 0x0001:
            mods.append("Shift")
        sym = event.keysym.upper()
        key = sym
        var.set("+".join([*mods, key]))
        return "break"

    entry.bind("<KeyPress>", on_key)


def build_hotkeys_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    rtl = is_rtl()
    row = start_row
    align = "e" if rtl else "w"
    ttk.Label(frm, text=t("settings.tab_hotkeys", "Hotkeys"), font=("Segoe UI", 11, "bold")).grid(
        row=row, column=0, columnspan=3, sticky=align, pady=(0, 6)
    )
    row += 1

    entries_spec = [
        (t("settings.hotkey_convert", "Convert last word:"), "_convert_var", win.cfg.convert_hotkey, "e.g. Pause"),
        (t("settings.hotkey_lang", "Show language chip:"), "_lang_var", win.cfg.lang_indicator_hotkey, "e.g. Alt+L"),
        (t("settings.hotkey_clip", "Clipboard history:"), "_clip_var", win.cfg.clipboard_history_hotkey, "e.g. Alt+V"),
        (t("settings.hotkey_norm", "Normalize text:"), "_norm_var", win.cfg.normalize_hotkey, "e.g. Ctrl+F12"),
        (t("settings.hotkey_case", "Cycle text case:"), "_case_var", win.cfg.case_hotkey, "e.g. Shift+F12"),
        (t("settings.hotkey_undo", "Undo last autocorrect:"), "_undo_var", win.cfg.undo_autocorrect_hotkey, "e.g. Ctrl+Shift+Z"),
        (t("settings.hotkey_stats", "Quick text stats:"), "_stats_var", getattr(win.cfg, "quick_stats_hotkey", None) or win.cfg.quick_stats_hotkey, "e.g. Ctrl+Alt+S"),
        (t("settings.hotkey_pause", "Pause / Resume Ravaan:"), "_pause_var", getattr(win.cfg, "pause_hotkey", None) or win.cfg.pause_hotkey, "e.g. Ctrl+Alt+Pause"),
        (t("settings.hotkey_translit", "Phonetic Finglish (Experimental):"), "_translit_hotkey_var", getattr(win.cfg, "translit_hotkey", None) or win.cfg.translit_hotkey, "e.g. Ctrl+Alt+T"),
    ]

    for label_text, var_attr, hotkey_spec, hint in entries_spec:
        ttk.Label(frm, text=label_text).grid(row=row, column=0, sticky=align, **pad)
        var = tk.StringVar(value=hotkey_to_text(hotkey_spec))
        setattr(win, var_attr, var)
        entry = ttk.Entry(frm, textvariable=var, width=18, justify="left")
        entry.grid(row=row, column=1, sticky="w", **pad)
        _bind_live_capture(entry, var)
        ttk.Label(frm, text=hint, foreground="gray").grid(row=row, column=2, sticky="w", **pad)
        row += 1

    ttk.Separator(frm, orient="horizontal").grid(
        row=row, column=0, columnspan=3, sticky="we", pady=6
    )
    row += 1
    ttk.Button(
        frm,
        text=t("settings.reset_tab_btn", "↺ Reset tab defaults"),
        command=lambda: win._reset_tab_defaults("hotkeys"),
    ).grid(row=row, column=0, sticky=align, **pad)
    row += 1
    return row


def build_general_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    from ravan.platform.startup import is_startup_enabled

    rtl = is_rtl()
    row = start_row
    align = "e" if rtl else "w"
    ttk.Label(frm, text=t("settings.tab_general", "General Options"), font=("Segoe UI", 11, "bold")).grid(
        row=row, column=0, columnspan=3, sticky=align, pady=(0, 6)
    )
    row += 1

    # UI Language selection with live switch
    ttk.Label(frm, text=t("settings.ui_language", "UI Language:")).grid(
        row=row, column=0, sticky=align, **pad
    )
    cur_lang = getattr(win.cfg, "ui_language", "auto")
    display_lang = (
        t("settings.lang_fa", "فارسی")
        if cur_lang == "fa"
        else (t("settings.lang_en", "English") if cur_lang == "en" else t("settings.lang_auto", "Auto (follow Windows)"))
    )
    win._ui_language_var = tk.StringVar(value=display_lang)
    lang_box = ttk.Combobox(
        frm,
        textvariable=win._ui_language_var,
        values=[
            t("settings.lang_auto", "Auto (follow Windows)"),
            t("settings.lang_en", "English"),
            t("settings.lang_fa", "فارسی"),
        ],
        state="readonly",
        width=22,
    )
    lang_box.grid(row=row, column=1, sticky="w", **pad)
    lang_box.bind("<<ComboboxSelected>>", win._on_language_changed)
    row += 1

    win._startup_var = tk.BooleanVar(value=is_startup_enabled())
    ttk.Checkbutton(frm, text=t("settings.launch_at_startup", "Launch at Windows startup"), variable=win._startup_var).grid(
        row=row, column=0, columnspan=3, sticky=align, **pad
    )
    row += 1

    from ravan.platform.protocol import is_protocol_registered

    win._protocol_var = tk.BooleanVar(value=is_protocol_registered())
    ttk.Checkbutton(
        frm,
        text=t("settings.register_protocol", "Register 'ravan://' URL protocol handler"),
        variable=win._protocol_var,
    ).grid(row=row, column=0, columnspan=3, sticky=align, **pad)
    row += 1

    win._sound_var = tk.BooleanVar(value=win.cfg.sound_feedback_enabled)
    ttk.Checkbutton(frm, text=t("settings.sound_feedback", "Audio feedback on keyboard layout switch"), variable=win._sound_var).grid(
        row=row, column=0, columnspan=3, sticky=align, **pad
    )
    row += 1

    from ravan.ui.tooltip import ToolTip

    win._cliphist_var = tk.BooleanVar(value=win.cfg.clipboard_history_enabled)
    cb_clip = ttk.Checkbutton(frm, text=t("settings.enable_cliphist", "Enable clipboard history (Alt+V)"), variable=win._cliphist_var)
    cb_clip.grid(row=row, column=0, columnspan=3, sticky=align, **pad)
    clip_ex = t("settings.enable_cliphist_example", "Example: Press Alt+V to search and paste recent clipboard items")
    ToolTip(cb_clip, clip_ex)
    row += 1
    ttk.Label(
        frm,
        text=f"↳ {clip_ex}",
        font=("Segoe UI" if not rtl else "Vazirmatn", 8),
        foreground="gray",
    ).grid(row=row, column=0, columnspan=3, sticky=align, padx=pad.get("padx", 10) + 14, pady=(0, 3))
    row += 1

    win._calc_var = tk.BooleanVar(value=win.cfg.inline_calc_enabled)
    cb_calc = ttk.Checkbutton(frm, text=t("settings.enable_calc", "Inline calculator on '=' (1200*1.09=)"), variable=win._calc_var)
    cb_calc.grid(row=row, column=0, columnspan=3, sticky=align, **pad)
    calc_ex = t("settings.enable_calc_example", "Example: Type '2500*4=' to automatically replace with '10000'")
    ToolTip(cb_calc, calc_ex)
    row += 1
    ttk.Label(
        frm,
        text=f"↳ {calc_ex}",
        font=("Segoe UI" if not rtl else "Vazirmatn", 8),
        foreground="gray",
    ).grid(row=row, column=0, columnspan=3, sticky=align, padx=pad.get("padx", 10) + 14, pady=(0, 3))
    row += 1

    win._zwnj_var = tk.BooleanVar(value=win.cfg.auto_zwnj_enabled)
    cb_zwnj = ttk.Checkbutton(frm, text=t("settings.auto_zwnj", "Smart Persian half-space (auto ZWNJ)"), variable=win._zwnj_var)
    cb_zwnj.grid(row=row, column=0, columnspan=3, sticky=align, **pad)
    zwnj_ex = t("settings.auto_zwnj_example", "Example: Automatically converts 'می روم' to 'می‌روم'")
    ToolTip(cb_zwnj, zwnj_ex)
    row += 1
    ttk.Label(
        frm,
        text=f"↳ {zwnj_ex}",
        font=("Segoe UI" if not rtl else "Vazirmatn", 8),
        foreground="gray",
    ).grid(row=row, column=0, columnspan=3, sticky=align, padx=pad.get("padx", 10) + 14, pady=(0, 3))
    row += 1

    win._shift_space_var = tk.BooleanVar(value=win.cfg.shift_space_zwnj)
    cb_shift = ttk.Checkbutton(frm, text=t("settings.shift_space_zwnj", "Shift+Space inserts half-space (ZWNJ)"), variable=win._shift_space_var)
    cb_shift.grid(row=row, column=0, columnspan=3, sticky=align, **pad)
    shift_ex = t("settings.shift_space_zwnj_example", "Example: Press Shift+Space anywhere to insert half-space (‌)")
    ToolTip(cb_shift, shift_ex)
    row += 1
    ttk.Label(
        frm,
        text=f"↳ {shift_ex}",
        font=("Segoe UI" if not rtl else "Vazirmatn", 8),
        foreground="gray",
    ).grid(row=row, column=0, columnspan=3, sticky=align, padx=pad.get("padx", 10) + 14, pady=(0, 3))
    row += 1

    win._punct_spacing_var = tk.BooleanVar(value=win.cfg.fix_punctuation_spacing)
    cb_punct = ttk.Checkbutton(frm, text=t("settings.fix_punctuation", "Fix spaces before punctuation"), variable=win._punct_spacing_var)
    cb_punct.grid(row=row, column=0, columnspan=3, sticky=align, **pad)
    punct_ex = t("settings.fix_punctuation_example", "Example: Fixes extra spaces before punctuation (e.g. 'سلام .' → 'سلام.')")
    ToolTip(cb_punct, punct_ex)
    row += 1
    ttk.Label(
        frm,
        text=f"↳ {punct_ex}",
        font=("Segoe UI" if not rtl else "Vazirmatn", 8),
        foreground="gray",
    ).grid(row=row, column=0, columnspan=3, sticky=align, padx=pad.get("padx", 10) + 14, pady=(0, 3))
    row += 1

    win._hints_var = tk.BooleanVar(value=getattr(win.cfg, "enable_feature_hints", True))
    cb_hints = ttk.Checkbutton(frm, text=t("settings.enable_hints", "Show helpful feature tips (max once per feature)"), variable=win._hints_var)
    cb_hints.grid(row=row, column=0, columnspan=3, sticky=align, **pad)
    hints_ex = t("settings.enable_hints_example", "Example: Shows friendly tips max once per feature, dismissible forever")
    ToolTip(cb_hints, hints_ex)
    row += 1
    ttk.Label(
        frm,
        text=f"↳ {hints_ex}",
        font=("Segoe UI" if not rtl else "Vazirmatn", 8),
        foreground="gray",
    ).grid(row=row, column=0, columnspan=3, sticky=align, padx=pad.get("padx", 10) + 14, pady=(0, 3))
    row += 1

    win._translit_var = tk.BooleanVar(value=getattr(win.cfg, "translit_enabled", False))
    cb_translit = ttk.Checkbutton(frm, text=t("settings.enable_translit", "Phonetic Finglish typing (Experimental)"), variable=win._translit_var)
    cb_translit.grid(row=row, column=0, columnspan=3, sticky=align, **pad)
    translit_ex = t("settings.enable_translit_example", "Example: Type 'salam' to convert to 'سلام' phonetically with candidates popup")
    ToolTip(cb_translit, translit_ex)
    row += 1
    ttk.Label(
        frm,
        text=f"↳ {translit_ex}",
        font=("Segoe UI" if not rtl else "Vazirmatn", 8),
        foreground="gray",
    ).grid(row=row, column=0, columnspan=3, sticky=align, padx=pad.get("padx", 10) + 14, pady=(0, 3))
    row += 1

    # Theme selection
    ttk.Label(frm, text=t("settings.theme_mode", "Theme Mode:")).grid(row=row, column=0, sticky=align, **pad)
    win._theme_mode_var = tk.StringVar(value=getattr(win.cfg, "theme_mode", "auto"))
    theme_box = ttk.Combobox(
        frm,
        textvariable=win._theme_mode_var,
        values=["auto", "dark", "light", "high_contrast"],
        state="readonly",
        width=14,
    )
    theme_box.grid(row=row, column=1, sticky="w", **pad)
    row += 1

    ttk.Separator(frm, orient="horizontal").grid(
        row=row, column=0, columnspan=3, sticky="we", pady=6
    )
    row += 1
    ttk.Button(
        frm,
        text=t("settings.reset_tab_btn", "↺ Reset tab defaults"),
        command=lambda: win._reset_tab_defaults("general"),
    ).grid(row=row, column=0, sticky=align, **pad)
    row += 1
    return row


def build_prediction_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    rtl = is_rtl()
    row = start_row
    align = "e" if rtl else "w"
    ttk.Label(frm, text=t("settings.prediction_header", "Prediction & Autocorrect"), font=("Segoe UI", 11, "bold")).grid(
        row=row, column=0, columnspan=3, sticky=align, pady=(0, 6)
    )
    row += 1

    win._prediction_var = tk.BooleanVar(value=win.cfg.prediction_enabled)
    ttk.Checkbutton(frm, text=t("settings.prediction_enabled", "Enable word prediction near typing cursor"), variable=win._prediction_var).grid(
        row=row, column=0, columnspan=3, sticky=align, **pad
    )
    row += 1

    win._learning_enabled_var = tk.BooleanVar(value=getattr(win.cfg, "learning_enabled", True))
    ttk.Checkbutton(
        frm,
        text=t("settings.learning_enabled", "Enable adaptive typing learning (tracks frequent words locally)"),
        variable=win._learning_enabled_var,
    ).grid(row=row, column=0, columnspan=3, sticky=align, **pad)
    row += 1

    win._autocorrect_var = tk.BooleanVar(value=win.cfg.autocorrect_enabled)
    ttk.Checkbutton(frm, text=t("settings.autocorrect_enabled", "Enable autocorrect on word boundaries"), variable=win._autocorrect_var).grid(
        row=row, column=0, columnspan=3, sticky=align, **pad
    )
    row += 1

    ttk.Label(frm, text=t("settings.autocorrect_mode", "Autocorrect mode:")).grid(row=row, column=0, sticky=align, **pad)
    win._autocorrect_mode_var = tk.StringVar(value=getattr(win.cfg, "autocorrect_mode", "safe"))
    mode_box = ttk.Combobox(
        frm, textvariable=win._autocorrect_mode_var, values=["safe", "normal", "off"], state="readonly", width=12
    )
    mode_box.grid(row=row, column=1, sticky="w", **pad)
    row += 1

    win._digits_var = tk.BooleanVar(value=win.cfg.quickpick_digits)
    ttk.Checkbutton(frm, text=t("settings.quickpick_digits", "Digits 1–5 quick-pick in popup"), variable=win._digits_var).grid(
        row=row, column=0, columnspan=3, sticky=align, **pad
    )
    row += 1

    win._en_dict_var = tk.BooleanVar(value=win.cfg.english_dict_enabled)
    ttk.Checkbutton(frm, text=t("settings.en_dict", "English dictionary"), variable=win._en_dict_var).grid(
        row=row, column=0, columnspan=3, sticky=align, **pad
    )
    row += 1

    win._fa_dict_var = tk.BooleanVar(value=win.cfg.persian_dict_enabled)
    ttk.Checkbutton(frm, text=t("settings.fa_dict", "Persian dictionary"), variable=win._fa_dict_var).grid(
        row=row, column=0, columnspan=3, sticky=align, **pad
    )
    row += 1

    ttk.Label(frm, text=t("settings.debounce_ms", "Debounce (ms):")).grid(row=row, column=0, sticky=align, **pad)
    win._debounce_var = tk.IntVar(value=win.cfg.prediction_debounce_ms)
    ttk.Spinbox(frm, from_=0, to=500, increment=10, textvariable=win._debounce_var, width=8).grid(
        row=row, column=1, sticky="w", **pad
    )
    row += 1

    ttk.Label(frm, text=t("settings.max_candidates", "Max suggestions:")).grid(row=row, column=0, sticky=align, **pad)
    win._maxcand_var = tk.IntVar(value=win.cfg.prediction_max_candidates)
    ttk.Spinbox(frm, from_=1, to=9, increment=1, textvariable=win._maxcand_var, width=8).grid(
        row=row, column=1, sticky="w", **pad
    )
    row += 1

    ttk.Label(frm, text=t("settings.min_prefix", "Min prefix length:")).grid(row=row, column=0, sticky=align, **pad)
    win._minlen_var = tk.IntVar(value=win.cfg.min_prefix_len)
    ttk.Spinbox(frm, from_=1, to=6, increment=1, textvariable=win._minlen_var, width=8).grid(
        row=row, column=1, sticky="w", **pad
    )
    row += 1

    from ravan.core.user_dict import load_user_words

    ttk.Label(frm, text=t("settings.custom_words_label", "Custom words / names (one per line):"), font=("Segoe UI", 9, "bold")).grid(
        row=row, column=0, columnspan=3, sticky=align, pady=(4, 2)
    )
    row += 1
    win._user_words_text = tk.Text(frm, width=40, height=3)
    win._user_words_text.insert("1.0", "\n".join(load_user_words()))
    win._user_words_text.grid(row=row, column=0, columnspan=3, sticky=align, **pad)
    row += 1

    # Privacy and Data Management Controls
    data_box = ttk.Frame(frm)
    data_box.grid(row=row, column=0, columnspan=3, sticky="we", pady=(2, 4))
    row += 1

    def _do_export_data() -> None:
        from tkinter import filedialog, messagebox

        from ravan.core.learning import UserLearningEngine

        dest = filedialog.asksaveasfilename(
            parent=win._root,
            title=t("settings.export_dialog_title", "Export Learned Data"),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="ravaan_learned_data.json",
        )
        if dest:
            try:
                engine = UserLearningEngine(auto_load=True)
                engine.export_profile(target_path=dest)
                messagebox.showinfo(
                    "Ravaan",
                    t("settings.export_data_success", "Learned vocabulary and style data exported successfully!"),
                    parent=win._root,
                )
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Ravaan", str(exc), parent=win._root)

    def _do_clear_data() -> None:
        from tkinter import messagebox

        from ravan.core.learning import UserLearningEngine

        confirmed = messagebox.askyesno(
            t("settings.clear_data_confirm_title", "Clear Learned Data"),
            t("settings.clear_data_confirm_msg", "Are you sure? All learned words and style data will be reset to factory defaults."),
            parent=win._root,
        )
        if confirmed:
            try:
                engine = UserLearningEngine(auto_load=True)
                engine.clear_learned_data()
                messagebox.showinfo(
                    "Ravaan",
                    t("settings.clear_data_success", "All learned data has been cleared successfully."),
                    parent=win._root,
                )
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Ravaan", str(exc), parent=win._root)

    btn_pack_side = "right" if rtl else "left"
    ttk.Button(
        data_box,
        text=t("settings.btn_export_data", "💾 Export my data (.json)"),
        command=_do_export_data,
    ).pack(side=btn_pack_side, padx=(0, 6) if not rtl else (6, 0))

    ttk.Button(
        data_box,
        text=t("settings.btn_clear_data", "🗑️ Clear learned data"),
        command=_do_clear_data,
    ).pack(side=btn_pack_side, padx=(0, 6) if not rtl else (6, 0))

    ttk.Separator(frm, orient="horizontal").grid(
        row=row, column=0, columnspan=3, sticky="we", pady=6
    )
    row += 1
    ttk.Button(
        frm,
        text=t("settings.reset_tab_btn", "↺ Reset tab defaults"),
        command=lambda: win._reset_tab_defaults("prediction"),
    ).grid(row=row, column=0, sticky=align, **pad)
    row += 1
    return row


def build_exclusions_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    rtl = is_rtl()
    row = start_row
    align = "e" if rtl else "w"
    ttk.Label(frm, text=t("settings.excl_header", "Excluded apps (one per line)"), font=("Segoe UI", 11, "bold")).grid(
        row=row, column=0, columnspan=3, sticky=align, pady=(0, 6)
    )
    row += 1
    win._excl_text = tk.Text(frm, width=40, height=5)
    win._excl_text.insert("1.0", "\n".join(win.cfg.excluded_apps))
    win._excl_text.grid(row=row, column=0, columnspan=3, sticky=align, **pad)
    row += 1

    excl_tools = ttk.Frame(frm)
    excl_tools.grid(row=row, column=0, columnspan=3, sticky=align, **pad)
    row += 1

    pack_side = "right" if rtl else "left"
    win._detected_app_var = tk.StringVar(value=t("settings.active_app", "Active app: {app}", app="—"))
    ttk.Label(excl_tools, textvariable=win._detected_app_var, foreground="#444444").pack(
        side=pack_side, padx=(8, 0) if rtl else (0, 8)
    )
    ttk.Button(excl_tools, text=t("settings.detect_active_app", "Detect Active App"), command=win._detect_active_app).pack(
        side=pack_side, padx=3
    )
    win._add_detected_btn = ttk.Button(
        excl_tools, text=t("settings.add_to_exclusions", "+ Add to Exclusions"), command=win._add_detected_to_exclusions, state="disabled"
    )
    win._add_detected_btn.pack(side=pack_side, padx=3)
    ttk.Button(excl_tools, text=t("settings.btn_pick_window", "Pick Window…"), command=win._open_window_picker).pack(
        side=pack_side, padx=3
    )
    row += 1

    ttk.Separator(frm, orient="horizontal").grid(
        row=row, column=0, columnspan=3, sticky="we", pady=6
    )
    row += 1
    ttk.Button(
        frm,
        text=t("settings.reset_tab_btn", "↺ Reset tab defaults"),
        command=lambda: win._reset_tab_defaults("exclusions"),
    ).grid(row=row, column=0, sticky=align, **pad)
    row += 1
    return row


def build_snippets_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    rtl = is_rtl()
    row = start_row
    align = "e" if rtl else "w"
    pack_side = "right" if rtl else "left"
    snip_hdr = ttk.Frame(frm)
    snip_hdr.grid(row=row, column=0, columnspan=3, sticky=align, pady=(0, 6))
    ttk.Label(snip_hdr, text=t("settings.snippets_header", "Snippets"), font=("Segoe UI", 11, "bold")).pack(
        side=pack_side, padx=(10, 0) if rtl else (0, 10)
    )
    ttk.Button(snip_hdr, text=t("settings.snippets_editor_btn", "Open Snippet Editor…"), command=win._open_snippet_editor).pack(
        side=pack_side
    )

    def _import_pkg() -> None:
        from ravan.ui.package_dialog import open_package_import_dialog

        def _on_pkg_imported(snips: list[Any], grps: list[Any]) -> None:
            win._managed_snippets = snips
            if grps:
                win.cfg.snippet_groups = grps
            win._update_snip_display()

        open_package_import_dialog(frm, win._managed_snippets, win.cfg.snippet_groups, _on_pkg_imported)

    ttk.Button(
        snip_hdr,
        text=t("packages.import_btn", "📦 Import Package…"),
        command=_import_pkg,
    ).pack(
        side=pack_side
    )
    row += 1
    win._snip_text = tk.Text(frm, width=40, height=6)
    win._update_snip_display()
    win._snip_text.grid(row=row, column=0, columnspan=3, sticky=align, **pad)
    row += 1

    from ravan.ui.snippet_groups_ui import build_groups_manager_frame

    def _on_groups_changed(groups: list[Any]) -> None:
        from ravan.core.config import save_config

        win.cfg.snippet_groups = groups
        save_config(win.cfg)

    grp_frm = build_groups_manager_frame(frm, win.cfg, _on_groups_changed)
    grp_frm.grid(row=row, column=0, columnspan=3, sticky="we", pady=(6, 6))
    row += 1

    ttk.Separator(frm, orient="horizontal").grid(
        row=row, column=0, columnspan=3, sticky="we", pady=6
    )
    row += 1
    ttk.Button(
        frm,
        text=t("settings.reset_tab_btn", "↺ Reset tab defaults"),
        command=lambda: win._reset_tab_defaults("snippets"),
    ).grid(row=row, column=0, sticky=align, **pad)
    row += 1
    return row


def build_sync_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    """Delegate to ravan.ui.settings_sync."""
    from ravan.ui.settings_sync import build_sync_section as _build_sync

    return _build_sync(win, frm, start_row, pad)


def build_about_section(frm: ttk.Frame) -> None:
    from ravan import __version__

    rtl = is_rtl()
    anchor = "e" if rtl else "w"
    justify = "right" if rtl else "left"

    ttk.Label(frm, text=t("settings.about_title", "Ravaan (روان)"), font=("Segoe UI", 14, "bold")).pack(anchor=anchor, pady=(6, 2))
    ttk.Label(frm, text=t("settings.about_subtitle", "Windows typing assistant for bilingual Persian/English typists"), font=("Segoe UI", 10)).pack(anchor=anchor, pady=(0, 4))
    ttk.Label(frm, text=t("settings.about_version", "Version {version} — MIT License", version=__version__), foreground="gray").pack(anchor=anchor, pady=(0, 4))
    ttk.Label(frm, text=t("settings.about_github", "GitHub: https://github.com/mohsen-niksirat/Ravaan"), foreground="#1a73e8").pack(anchor=anchor, pady=(0, 4))
    ttk.Label(frm, text=t("settings.about_data_privacy", "Data & Privacy: 100% local-first, DPAPI-encrypted (see DATA.md)"), foreground="#555555").pack(anchor=anchor, pady=(0, 8))

    ttk.Separator(frm, orient="horizontal").pack(fill="x", pady=6)
    features_text = t(
        "settings.about_features",
        "Key Features:\n• Layout Conversion (Pause)\n• Word Prediction & Autocorrect\n• Smart Half-Space (ZWNJ)\n• Clipboard History (Alt+V)\n• Quick Text Stats (Ctrl+Alt+S)\n• Math & Jalali Macros\n• Snippets 2.0 & Cloud Sync\n• Data Manifest & Zero Telemetry",
    )
    ttk.Label(frm, text=features_text, justify=justify).pack(anchor=anchor, pady=4)
