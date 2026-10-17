"""UI section builder functions for SettingsWindow."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.config import hotkey_to_text


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
        if sym.startswith("F") and sym[1:].isdigit():
            key = sym
        elif len(sym) == 1:
            key = sym
        else:
            key = sym
        var.set("+".join([*mods, key]))
        return "break"

    entry.bind("<KeyPress>", on_key)


def build_hotkeys_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    row = start_row
    ttk.Label(frm, text="Hotkeys (Press key combination to capture)", font=("Segoe UI", 11, "bold")).grid(
        row=row, column=0, columnspan=3, sticky="w", pady=(0, 6)
    )
    row += 1

    entries_spec = [
        ("Convert last word:", "_convert_var", win.cfg.convert_hotkey, "e.g. F12 or Ctrl+Shift+C"),
        ("Show language chip:", "_lang_var", win.cfg.lang_indicator_hotkey, "e.g. Alt+L"),
        ("Clipboard history:", "_clip_var", win.cfg.clipboard_history_hotkey, "e.g. Alt+V"),
        ("Normalize text:", "_norm_var", win.cfg.normalize_hotkey, "e.g. Ctrl+F12"),
        ("Cycle text case:", "_case_var", win.cfg.case_hotkey, "e.g. Shift+F12"),
        ("Undo autocorrect:", "_undo_var", win.cfg.undo_autocorrect_hotkey, "e.g. Ctrl+Shift+Z"),
        ("Quick text stats:", "_stats_var", getattr(win.cfg, "quick_stats_hotkey", None) or win.cfg.quick_stats_hotkey, "e.g. Alt+S"),
    ]



    for label_text, var_attr, hotkey_spec, hint in entries_spec:
        ttk.Label(frm, text=label_text).grid(row=row, column=0, sticky="w", **pad)
        var = tk.StringVar(value=hotkey_to_text(hotkey_spec))
        setattr(win, var_attr, var)
        entry = ttk.Entry(frm, textvariable=var, width=22)
        entry.grid(row=row, column=1, sticky="w", **pad)
        _bind_live_capture(entry, var)
        ttk.Label(frm, text=hint, foreground="gray").grid(row=row, column=2, sticky="w", **pad)
        row += 1

    return row


def build_general_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    from ravan.platform.startup import is_startup_enabled

    row = start_row
    ttk.Label(frm, text="General Options", font=("Segoe UI", 11, "bold")).grid(
        row=row, column=0, columnspan=3, sticky="w", pady=(0, 6)
    )
    row += 1

    win._startup_var = tk.BooleanVar(value=is_startup_enabled())
    ttk.Checkbutton(frm, text="Launch at Windows startup", variable=win._startup_var).grid(
        row=row, column=0, columnspan=3, sticky="w", **pad
    )
    row += 1

    win._sound_var = tk.BooleanVar(value=win.cfg.sound_feedback_enabled)
    ttk.Checkbutton(frm, text="Audio feedback on keyboard layout switch", variable=win._sound_var).grid(
        row=row, column=0, columnspan=3, sticky="w", **pad
    )
    row += 1

    win._cliphist_var = tk.BooleanVar(value=win.cfg.clipboard_history_enabled)
    ttk.Checkbutton(frm, text="Enable clipboard history (Alt+V, up to 50 items)", variable=win._cliphist_var).grid(
        row=row, column=0, columnspan=3, sticky="w", **pad
    )
    row += 1

    win._calc_var = tk.BooleanVar(value=win.cfg.inline_calc_enabled)
    ttk.Checkbutton(frm, text="Enable inline calculator on '=' trigger (e.g. 1200*1.09=)", variable=win._calc_var).grid(
        row=row, column=0, columnspan=3, sticky="w", **pad
    )
    row += 1

    win._zwnj_var = tk.BooleanVar(value=win.cfg.auto_zwnj_enabled)
    ttk.Checkbutton(frm, text="Smart Persian half-space (auto ZWNJ for می/نمی and ها/های/تر)", variable=win._zwnj_var).grid(
        row=row, column=0, columnspan=3, sticky="w", **pad
    )
    row += 1

    win._shift_space_var = tk.BooleanVar(value=win.cfg.shift_space_zwnj)
    ttk.Checkbutton(frm, text="Shift+Space inserts half-space (ZWNJ)", variable=win._shift_space_var).grid(
        row=row, column=0, columnspan=3, sticky="w", **pad
    )
    row += 1

    win._punct_spacing_var = tk.BooleanVar(value=win.cfg.fix_punctuation_spacing)
    ttk.Checkbutton(frm, text="Fix Persian spacing before punctuation (e.g. کتاب . -> کتاب.)", variable=win._punct_spacing_var).grid(
        row=row, column=0, columnspan=3, sticky="w", **pad
    )
    row += 1

    # Theme selection
    ttk.Label(frm, text="Theme:").grid(row=row, column=0, sticky="w", **pad)
    win._theme_mode_var = tk.StringVar(value=getattr(win.cfg, "theme_mode", "auto"))
    theme_box = ttk.Combobox(
        frm, textvariable=win._theme_mode_var, values=["auto", "dark", "light"], state="readonly", width=12
    )
    theme_box.grid(row=row, column=1, sticky="w", **pad)
    row += 2
    return row


def build_prediction_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    row = start_row
    ttk.Label(frm, text="Prediction & Autocorrect", font=("Segoe UI", 11, "bold")).grid(
        row=row, column=0, columnspan=3, sticky="w", pady=(0, 6)
    )
    row += 1

    win._prediction_var = tk.BooleanVar(value=win.cfg.prediction_enabled)
    ttk.Checkbutton(frm, text="Enable word prediction suggestions", variable=win._prediction_var).grid(
        row=row, column=0, columnspan=3, sticky="w", **pad
    )
    row += 1

    win._autocorrect_var = tk.BooleanVar(value=win.cfg.autocorrect_enabled)
    ttk.Checkbutton(frm, text="Enable autocorrect on word boundary", variable=win._autocorrect_var).grid(
        row=row, column=0, columnspan=3, sticky="w", **pad
    )
    row += 1

    ttk.Label(frm, text="Autocorrect mode:").grid(row=row, column=0, sticky="w", **pad)
    win._autocorrect_mode_var = tk.StringVar(value=getattr(win.cfg, "autocorrect_mode", "safe"))
    mode_box = ttk.Combobox(
        frm, textvariable=win._autocorrect_mode_var, values=["safe", "normal", "off"], state="readonly", width=12
    )
    mode_box.grid(row=row, column=1, sticky="w", **pad)
    row += 1

    win._digits_var = tk.BooleanVar(value=win.cfg.quickpick_digits)
    ttk.Checkbutton(frm, text="Digits 1–5 quick-pick in popup", variable=win._digits_var).grid(
        row=row, column=0, columnspan=3, sticky="w", **pad
    )
    row += 1

    win._en_dict_var = tk.BooleanVar(value=win.cfg.english_dict_enabled)
    ttk.Checkbutton(frm, text="English dictionary", variable=win._en_dict_var).grid(
        row=row, column=0, columnspan=3, sticky="w", **pad
    )
    row += 1

    win._fa_dict_var = tk.BooleanVar(value=win.cfg.persian_dict_enabled)
    ttk.Checkbutton(frm, text="Persian dictionary", variable=win._fa_dict_var).grid(
        row=row, column=0, columnspan=3, sticky="w", **pad
    )
    row += 1

    ttk.Label(frm, text="Debounce (ms):").grid(row=row, column=0, sticky="w", **pad)
    win._debounce_var = tk.IntVar(value=win.cfg.prediction_debounce_ms)
    ttk.Spinbox(frm, from_=0, to=500, increment=10, textvariable=win._debounce_var, width=8).grid(
        row=row, column=1, sticky="w", **pad
    )
    row += 1

    ttk.Label(frm, text="Max suggestions:").grid(row=row, column=0, sticky="w", **pad)
    win._maxcand_var = tk.IntVar(value=win.cfg.prediction_max_candidates)
    ttk.Spinbox(frm, from_=1, to=9, increment=1, textvariable=win._maxcand_var, width=8).grid(
        row=row, column=1, sticky="w", **pad
    )
    row += 1

    ttk.Label(frm, text="Min prefix length:").grid(row=row, column=0, sticky="w", **pad)
    win._minlen_var = tk.IntVar(value=win.cfg.min_prefix_len)
    ttk.Spinbox(frm, from_=1, to=6, increment=1, textvariable=win._minlen_var, width=8).grid(
        row=row, column=1, sticky="w", **pad
    )
    row += 1

    from ravan.core.user_dict import load_user_words

    ttk.Label(frm, text="Custom words / names (one per line):", font=("Segoe UI", 9, "bold")).grid(
        row=row, column=0, columnspan=3, sticky="w", pady=(4, 2)
    )
    row += 1
    win._user_words_text = tk.Text(frm, width=40, height=3)
    win._user_words_text.insert("1.0", "\n".join(load_user_words()))
    win._user_words_text.grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 2
    return row


def build_exclusions_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    row = start_row
    ttk.Label(frm, text="Excluded apps (one per line)", font=("Segoe UI", 11, "bold")).grid(
        row=row, column=0, columnspan=3, sticky="w", pady=(0, 6)
    )
    row += 1
    win._excl_text = tk.Text(frm, width=40, height=5)
    win._excl_text.insert("1.0", "\n".join(win.cfg.excluded_apps))
    win._excl_text.grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 1

    excl_tools = ttk.Frame(frm)
    excl_tools.grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 2

    win._detected_app_var = tk.StringVar(value="Active app: —")
    ttk.Label(excl_tools, textvariable=win._detected_app_var, foreground="#444444").pack(
        side="left", padx=(0, 8)
    )
    ttk.Button(excl_tools, text="Detect Active App", command=win._detect_active_app).pack(
        side="left", padx=3
    )
    win._add_detected_btn = ttk.Button(
        excl_tools, text="+ Add to Exclusions", command=win._add_detected_to_exclusions, state="disabled"
    )
    win._add_detected_btn.pack(side="left", padx=3)
    ttk.Button(excl_tools, text="Pick Window…", command=win._open_window_picker).pack(
        side="left", padx=3
    )
    return row


def build_snippets_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    row = start_row
    snip_hdr = ttk.Frame(frm)
    snip_hdr.grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 6))
    ttk.Label(snip_hdr, text="Snippets", font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 10))
    ttk.Button(snip_hdr, text="Open Snippet Editor…", command=win._open_snippet_editor).pack(side="left")
    row += 1
    win._snip_text = tk.Text(frm, width=40, height=6)
    win._update_snip_display()
    win._snip_text.grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 2
    return row


def build_sync_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    row = start_row
    ttk.Label(
        frm,
        text="Cloud Sync via GitHub Gist (همگام‌سازی ابری)",
        font=("Segoe UI", 11, "bold"),
    ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 4))
    row += 1

    ttk.Label(
        frm,
        text="Sync your user words and snippets securely across PCs via a GitHub Gist.",
        foreground="#444444",
    ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 8))
    row += 1

    ttk.Label(frm, text="Gist Personal Access Token:").grid(row=row, column=0, sticky="w", **pad)
    win._gist_token_var = tk.StringVar(value=getattr(win.cfg, "gist_token", ""))
    token_entry = ttk.Entry(frm, textvariable=win._gist_token_var, width=28, show="*")
    token_entry.grid(row=row, column=1, sticky="w", **pad)

    def toggle_show_token() -> None:
        if token_entry.cget("show") == "*":
            token_entry.config(show="")
        else:
            token_entry.config(show="*")

    ttk.Button(frm, text="Show/Hide", command=toggle_show_token, width=9).grid(
        row=row, column=2, sticky="w", **pad
    )
    row += 1

    ttk.Label(frm, text="Gist ID:").grid(row=row, column=0, sticky="w", **pad)
    win._gist_id_var = tk.StringVar(value=getattr(win.cfg, "gist_id", ""))
    ttk.Entry(frm, textvariable=win._gist_id_var, width=28).grid(
        row=row, column=1, sticky="w", **pad
    )
    ttk.Label(frm, text="Found in gist URL", foreground="gray").grid(
        row=row, column=2, sticky="w", **pad
    )
    row += 1

    win._cloud_sync_var = tk.BooleanVar(value=getattr(win.cfg, "cloud_sync_enabled", False))
    ttk.Checkbutton(
        frm,
        text="Enable automatic background sync",
        variable=win._cloud_sync_var,
    ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 1

    sync_btn_bar = ttk.Frame(frm)
    sync_btn_bar.grid(row=row, column=0, columnspan=3, sticky="w", pady=(8, 4))
    ttk.Button(sync_btn_bar, text="⬆ Push to Gist", command=win._sync_push).pack(
        side="left", padx=(0, 6)
    )
    ttk.Button(sync_btn_bar, text="⬇ Pull from Gist", command=win._sync_pull).pack(
        side="left", padx=6
    )
    row += 1

    win._last_sync_label_var = tk.StringVar(
        value=f"Last sync: {getattr(win.cfg, 'last_sync_time', '') or 'Never'}"
    )
    ttk.Label(frm, textvariable=win._last_sync_label_var, foreground="#555555").grid(
        row=row, column=0, columnspan=3, sticky="w", **pad
    )
    row += 1

    win._sync_status_var = tk.StringVar(value="")
    ttk.Label(frm, textvariable=win._sync_status_var, font=("Segoe UI", 9, "bold")).grid(
        row=row, column=0, columnspan=3, sticky="w", **pad
    )
    row += 1

    return row


def build_about_section(frm: ttk.Frame) -> None:

    ttk.Label(frm, text="Ravaan (روان)", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(6, 2))
    ttk.Label(frm, text="Windows typing assistant for bilingual Persian/English typists", font=("Segoe UI", 10)).pack(
        anchor="w", pady=(0, 8)
    )
    ttk.Label(frm, text="Version 0.4.0 — MIT License", foreground="gray").pack(anchor="w", pady=(0, 4))
    ttk.Label(frm, text="GitHub: https://github.com/mohsen-niksirat/Ravaan", foreground="#1a73e8").pack(
        anchor="w", pady=(0, 8)
    )
    ttk.Separator(frm, orient="horizontal").pack(fill="x", pady=8)
    ttk.Label(
        frm,
        text="ویژگی‌های کلیدی:\n"
        "• تبدیل هوشمند چیدمان کیبورد (F12)\n"
        "• تصحیح خودکار و پیش‌بینی واژگان\n"
        "• نیم‌فاصله هوشمند (Shift+Space و خودکار)\n"
        "• سابقه کلیپ‌بورد (Alt+V)\n"
        "• تبدیل تاریخ شمسی و محاسبات سریع",
        justify="right",
    ).pack(anchor="e", pady=4)
