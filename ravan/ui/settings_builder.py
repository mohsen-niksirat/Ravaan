"""UI section builder functions for SettingsWindow."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.config import hotkey_to_text


def build_hotkeys_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    row = start_row
    ttk.Label(frm, text="Hotkeys", font=("Segoe UI", 11, "bold")).grid(
        row=row, column=0, columnspan=3, sticky="w", pady=(0, 6)
    )
    row += 1

    ttk.Label(frm, text="Convert last word:").grid(row=row, column=0, sticky="w", **pad)
    win._convert_var = tk.StringVar(value=hotkey_to_text(win.cfg.convert_hotkey))
    ttk.Entry(frm, textvariable=win._convert_var, width=22).grid(
        row=row, column=1, sticky="w", **pad
    )
    ttk.Label(frm, text="e.g. F12  or  Ctrl+Shift+C", foreground="gray").grid(
        row=row, column=2, sticky="w", **pad
    )
    row += 1

    ttk.Label(frm, text="Show language chip:").grid(row=row, column=0, sticky="w", **pad)
    win._lang_var = tk.StringVar(value=hotkey_to_text(win.cfg.lang_indicator_hotkey))
    ttk.Entry(frm, textvariable=win._lang_var, width=22).grid(
        row=row, column=1, sticky="w", **pad
    )
    ttk.Label(frm, text="e.g. Alt+L", foreground="gray").grid(
        row=row, column=2, sticky="w", **pad
    )
    row += 1

    ttk.Label(frm, text="Clipboard history:").grid(row=row, column=0, sticky="w", **pad)
    win._clip_var = tk.StringVar(value=hotkey_to_text(win.cfg.clipboard_history_hotkey))
    ttk.Entry(frm, textvariable=win._clip_var, width=22).grid(
        row=row, column=1, sticky="w", **pad
    )
    ttk.Label(frm, text="e.g. Alt+V", foreground="gray").grid(
        row=row, column=2, sticky="w", **pad
    )
    row += 1

    ttk.Label(frm, text="Normalize text:").grid(row=row, column=0, sticky="w", **pad)
    win._norm_var = tk.StringVar(value=hotkey_to_text(win.cfg.normalize_hotkey))
    ttk.Entry(frm, textvariable=win._norm_var, width=22).grid(
        row=row, column=1, sticky="w", **pad
    )
    ttk.Label(frm, text="e.g. Ctrl+F12", foreground="gray").grid(
        row=row, column=2, sticky="w", **pad
    )
    row += 1

    ttk.Label(frm, text="Cycle text case:").grid(row=row, column=0, sticky="w", **pad)
    win._case_var = tk.StringVar(value=hotkey_to_text(win.cfg.case_hotkey))
    ttk.Entry(frm, textvariable=win._case_var, width=22).grid(
        row=row, column=1, sticky="w", **pad
    )
    ttk.Label(frm, text="e.g. Shift+F12", foreground="gray").grid(
        row=row, column=2, sticky="w", **pad
    )
    row += 1

    ttk.Label(frm, text="Undo autocorrect:").grid(row=row, column=0, sticky="w", **pad)
    win._undo_var = tk.StringVar(value=hotkey_to_text(win.cfg.undo_autocorrect_hotkey))
    ttk.Entry(frm, textvariable=win._undo_var, width=22).grid(
        row=row, column=1, sticky="w", **pad
    )
    ttk.Label(frm, text="e.g. Ctrl+Shift+Z (or Backspace)", foreground="gray").grid(
        row=row, column=2, sticky="w", **pad
    )
    row += 2
    return row


def build_features_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    row = start_row
    ttk.Label(frm, text="Features", font=("Segoe UI", 11, "bold")).grid(
        row=row, column=0, columnspan=3, sticky="w", pady=(0, 6)
    )
    row += 1

    win._prediction_var = tk.BooleanVar(value=win.cfg.prediction_enabled)
    ttk.Checkbutton(
        frm, text="Enable word prediction suggestions", variable=win._prediction_var
    ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 1

    win._autocorrect_var = tk.BooleanVar(value=win.cfg.autocorrect_enabled)
    ttk.Checkbutton(
        frm,
        text="Enable safe autocorrect on word boundary (never alters valid words)",
        variable=win._autocorrect_var,
    ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 1

    win._calc_var = tk.BooleanVar(value=win.cfg.inline_calc_enabled)
    ttk.Checkbutton(
        frm,
        text="Enable inline calculator on '=' trigger (e.g. 1200*1.09=)",
        variable=win._calc_var,
    ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 1

    win._zwnj_var = tk.BooleanVar(value=win.cfg.auto_zwnj_enabled)
    ttk.Checkbutton(
        frm,
        text="Smart Persian half-space (auto ZWNJ for می/نمی and ها/های/تر/ترین)",
        variable=win._zwnj_var,
    ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 1

    win._shift_space_var = tk.BooleanVar(value=win.cfg.shift_space_zwnj)
    ttk.Checkbutton(
        frm,
        text="Shift+Space inserts half-space (ZWNJ)",
        variable=win._shift_space_var,
    ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 1

    win._cliphist_var = tk.BooleanVar(value=win.cfg.clipboard_history_enabled)
    ttk.Checkbutton(
        frm,
        text="Enable clipboard history ring buffer (Alt+V)",
        variable=win._cliphist_var,
    ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 1

    win._digits_var = tk.BooleanVar(value=win.cfg.quickpick_digits)
    ttk.Checkbutton(
        frm, text="Digits 1–5 quick-pick in popup", variable=win._digits_var
    ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
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

    win._sound_var = tk.BooleanVar(value=win.cfg.sound_feedback_enabled)
    ttk.Checkbutton(
        frm, text="Audio feedback on keyboard layout switch", variable=win._sound_var
    ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 1

    win._punct_spacing_var = tk.BooleanVar(value=win.cfg.fix_punctuation_spacing)
    ttk.Checkbutton(
        frm,
        text="Fix Persian spacing before punctuation (e.g. کتاب . -> کتاب.)",
        variable=win._punct_spacing_var,
    ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 2
    return row


def build_tuning_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    from ravan.platform.startup import is_startup_enabled

    row = start_row
    ttk.Label(frm, text="Tuning", font=("Segoe UI", 11, "bold")).grid(
        row=row, column=0, columnspan=3, sticky="w", pady=(0, 6)
    )
    row += 1

    ttk.Label(frm, text="Debounce (ms):").grid(row=row, column=0, sticky="w", **pad)
    win._debounce_var = tk.IntVar(value=win.cfg.prediction_debounce_ms)
    ttk.Spinbox(
        frm, from_=0, to=500, increment=10, textvariable=win._debounce_var, width=8
    ).grid(row=row, column=1, sticky="w", **pad)
    row += 1

    ttk.Label(frm, text="Max candidates:").grid(row=row, column=0, sticky="w", **pad)
    win._maxcand_var = tk.IntVar(value=win.cfg.prediction_max_candidates)
    ttk.Spinbox(
        frm, from_=1, to=9, textvariable=win._maxcand_var, width=8
    ).grid(row=row, column=1, sticky="w", **pad)
    row += 1

    ttk.Label(frm, text="Min prefix length:").grid(row=row, column=0, sticky="w", **pad)
    win._minlen_var = tk.IntVar(value=win.cfg.min_prefix_len)
    ttk.Spinbox(frm, from_=1, to=6, textvariable=win._minlen_var, width=8).grid(
        row=row, column=1, sticky="w", **pad
    )
    row += 2

    # ── Startup ──
    win._startup_var = tk.BooleanVar(value=is_startup_enabled())
    ttk.Checkbutton(
        frm, text="Launch at Windows startup", variable=win._startup_var
    ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 2
    return row


def build_exclusions_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    row = start_row
    ttk.Label(frm, text="Excluded apps (one per line)", font=("Segoe UI", 11, "bold")).grid(
        row=row, column=0, columnspan=3, sticky="w", pady=(0, 6)
    )
    row += 1
    win._excl_text = tk.Text(frm, width=40, height=4)
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
    ttk.Button(
        excl_tools, text="Detect Active App", command=win._detect_active_app
    ).pack(side="left", padx=3)
    win._add_detected_btn = ttk.Button(
        excl_tools, text="+ Add to Exclusions", command=win._add_detected_to_exclusions, state="disabled"
    )
    win._add_detected_btn.pack(side="left", padx=3)
    return row


def build_snippets_and_dict_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    row = start_row
    snip_hdr = ttk.Frame(frm)
    snip_hdr.grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 6))
    ttk.Label(
        snip_hdr, text="Snippets", font=("Segoe UI", 11, "bold")
    ).pack(side="left", padx=(0, 10))
    ttk.Button(
        snip_hdr, text="Open Snippet Editor…", command=win._open_snippet_editor
    ).pack(side="left")
    row += 1
    win._snip_text = tk.Text(frm, width=40, height=4)
    win._update_snip_display()
    win._snip_text.grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 2

    from ravan.core.user_dict import load_user_words

    ttk.Label(
        frm, text="Custom words / names (one per line)",
        font=("Segoe UI", 11, "bold"),
    ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 6))
    row += 1
    win._user_words_text = tk.Text(frm, width=40, height=4)
    win._user_words_text.insert("1.0", "\n".join(load_user_words()))
    win._user_words_text.grid(row=row, column=0, columnspan=3, sticky="w", **pad)
    row += 2
    return row
