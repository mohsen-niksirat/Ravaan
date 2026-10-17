"""Save action handler for SettingsWindow."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Any

from ravan.core.config import Snippet, hotkey_to_text, save_config, text_to_hotkey
from ravan.platform.startup import is_startup_enabled, set_startup


def _safe_int(var: tk.IntVar, default: int, min_val: int, max_val: int) -> int:
    try:
        val = int(var.get())
        return max(min_val, min(max_val, val))
    except (tk.TclError, ValueError, TypeError):
        return default


def save_settings_window(win: Any) -> None:
    """Validate and persist all configuration choices made in SettingsWindow."""
    hk_items = [
        (win._convert_var.get(), "convert"),
        (win._lang_var.get(), "language"),
        (win._clip_var.get(), "clipboard"),
        (win._norm_var.get(), "normalize"),
        (win._case_var.get(), "case"),
        (win._undo_var.get(), "undo"),
        (win._stats_var.get() if hasattr(win, "_stats_var") else "", "stats"),
    ]
    parsed = []
    for raw, name in hk_items:
        val = text_to_hotkey(raw)
        if raw.strip() and val is None:
            messagebox.showwarning("Ravan", f"Invalid {name} hotkey", parent=win._root)
            return
        parsed.append(val)
    convert, lang, clip, norm, case, undo, stats = parsed

    # Validate no duplicate hotkeys
    active_hotkeys = [
        hotkey_to_text(h)
        for h in [convert, lang, clip, norm, case, undo, stats]
        if h
    ]
    if len(active_hotkeys) != len(set(active_hotkeys)):
        messagebox.showwarning(
            "Ravan",
            "Duplicate hotkeys detected! Each hotkey shortcut must be unique.",
            parent=win._root,
        )
        return

    cfg = win.cfg
    if convert:
        cfg.convert_hotkey = convert
    if lang:
        cfg.lang_indicator_hotkey = lang
    if clip:
        cfg.clipboard_history_hotkey = clip
    if norm:
        cfg.normalize_hotkey = norm
    if case:
        cfg.case_hotkey = case
    if undo:
        cfg.undo_autocorrect_hotkey = undo
    if stats:
        cfg.quick_stats_hotkey = stats

    cfg.prediction_enabled = win._prediction_var.get()
    cfg.autocorrect_enabled = win._autocorrect_var.get()
    if hasattr(win, "_autocorrect_mode_var"):
        cfg.autocorrect_mode = win._autocorrect_mode_var.get()
    if hasattr(win, "_theme_mode_var"):
        cfg.theme_mode = win._theme_mode_var.get()
    cfg.fix_punctuation_spacing = win._punct_spacing_var.get()
    cfg.auto_zwnj_enabled = win._zwnj_var.get()
    cfg.shift_space_zwnj = win._shift_space_var.get()
    cfg.clipboard_history_enabled = win._cliphist_var.get()
    cfg.inline_calc_enabled = win._calc_var.get()
    cfg.quickpick_digits = win._digits_var.get()
    cfg.english_dict_enabled = win._en_dict_var.get()
    cfg.persian_dict_enabled = win._fa_dict_var.get()

    cfg.prediction_debounce_ms = _safe_int(win._debounce_var, 50, 0, 5000)
    cfg.prediction_max_candidates = _safe_int(win._maxcand_var, 5, 1, 9)
    cfg.min_prefix_len = _safe_int(win._minlen_var, 2, 1, 6)

    excl = [
        ln.strip().lower()
        for ln in win._excl_text.get("1.0", "end").splitlines()
        if ln.strip()
    ]
    cfg.excluded_apps = excl

    cur_snip_text = win._snip_text.get("1.0", "end").strip()
    if cur_snip_text == win._last_snip_text.strip():
        cfg.snippets = list(win._managed_snippets)
    else:
        snippets: list[Snippet] = []
        for ln in cur_snip_text.splitlines():
            if "=>" not in ln:
                continue
            trigger, _, repl = ln.partition("=>")
            trigger = trigger.strip()
            repl = repl.strip().replace("\\n", "\n")
            if trigger and repl:
                snippets.append(Snippet(trigger=trigger, replacement=repl))
        cfg.snippets = snippets

    if win._startup_var.get() != is_startup_enabled():
        if not set_startup(win._startup_var.get()):
            messagebox.showwarning(
                "Ravan", "Could not update startup entry", parent=win._root
            )
    cfg.launch_at_startup = win._startup_var.get()

    from ravan.core.user_dict import save_user_words

    user_words = [
        ln.strip()
        for ln in win._user_words_text.get("1.0", "end").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    save_user_words(user_words)

    if hasattr(win, "_ui_language_var"):
        val = win._ui_language_var.get()
        cfg.ui_language = "fa" if "فارسی" in val else ("en" if "English" in val else "auto")

    # Cloud Sync fields
    if hasattr(win, "_sync_backend_var"):
        cfg.sync_backend = (
            "webdav" if "webdav" in win._sync_backend_var.get().lower() else "gist"
        )
    if hasattr(win, "_gist_token_var"):
        cfg.gist_token = win._gist_token_var.get().strip()
    if hasattr(win, "_gist_id_var"):
        cfg.gist_id = win._gist_id_var.get().strip()
    if hasattr(win, "_webdav_url_var"):
        cfg.webdav_url = win._webdav_url_var.get().strip()
    if hasattr(win, "_webdav_username_var"):
        cfg.webdav_username = win._webdav_username_var.get().strip()
    if hasattr(win, "_webdav_password_var"):
        cfg.webdav_password = win._webdav_password_var.get().strip()
    if hasattr(win, "_cloud_sync_var"):
        cfg.cloud_sync_enabled = win._cloud_sync_var.get()
    if hasattr(win, "_sync_interval_var"):
        try:
            cfg.sync_interval_min = int(win._sync_interval_var.get())
        except (ValueError, TypeError):
            cfg.sync_interval_min = 0

    save_config(cfg)
    if win.on_saved:
        win.on_saved(cfg)
    win._close()
