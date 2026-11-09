"""Per-tab default reset handler for SettingsWindow."""

from __future__ import annotations

from tkinter import messagebox
from typing import Any

from ravan.core.config import DEFAULT_EXCLUDED_APPS, Config, hotkey_to_text
from ravan.core.i18n import t


def reset_tab_defaults(win: Any, tab_name: str) -> None:
    """Reset configuration fields for the specified tab to defaults after confirmation."""
    if not messagebox.askyesno(
        t("settings.reset_title", "Reset Tab Defaults"),
        t(
            "settings.reset_confirm",
            "Reset all settings in this tab to their default values?",
        ),
        parent=getattr(win, "_root", None),
    ):
        return

    d = Config()
    if tab_name == "general":
        if hasattr(win, "_ui_language_var"):
            win._ui_language_var.set(t("settings.lang_auto", "Auto (follow Windows)"))
        if hasattr(win, "_startup_var"):
            win._startup_var.set(d.launch_at_startup)
        if hasattr(win, "_sound_var"):
            win._sound_var.set(d.sound_feedback_enabled)
        if hasattr(win, "_cliphist_var"):
            win._cliphist_var.set(d.clipboard_history_enabled)
        if hasattr(win, "_calc_var"):
            win._calc_var.set(d.inline_calc_enabled)
        if hasattr(win, "_zwnj_var"):
            win._zwnj_var.set(d.auto_zwnj_enabled)
        if hasattr(win, "_shift_space_var"):
            win._shift_space_var.set(d.shift_space_zwnj)
        if hasattr(win, "_punct_spacing_var"):
            win._punct_spacing_var.set(d.fix_punctuation_spacing)
        if hasattr(win, "_hints_var"):
            win._hints_var.set(d.enable_feature_hints)
        if hasattr(win, "_theme_mode_var"):
            win._theme_mode_var.set(d.theme_mode)
        if hasattr(win, "_translit_var"):
            win._translit_var.set(d.translit_enabled)
        if hasattr(win, "_show_lang_on_click_var"):
            win._show_lang_on_click_var.set(d.show_lang_on_click)
        if hasattr(win, "_lang_placement_var"):
            placement_map = getattr(win, "_lang_placement_map", {})
            code_to_label = {v: k for k, v in placement_map.items()}
            default_lbl = code_to_label.get(d.lang_indicator_placement)
            if default_lbl:
                win._lang_placement_var.set(default_lbl)
            if hasattr(win, "cfg") and callable(getattr(win, "on_lang_placement_changed", None)):
                win.on_lang_placement_changed()
    elif tab_name == "prediction":
        if hasattr(win, "_prediction_var"):
            win._prediction_var.set(d.prediction_enabled)
        if hasattr(win, "_learning_enabled_var"):
            win._learning_enabled_var.set(d.learning_enabled)
        if hasattr(win, "_prediction_auto_space_var"):
            win._prediction_auto_space_var.set(d.prediction_auto_space)
        if hasattr(win, "_suggestion_accept_enter_var"):
            win._suggestion_accept_enter_var.set(d.suggestion_accept_enter)
        if hasattr(win, "_autocorrect_var"):
            win._autocorrect_var.set(d.autocorrect_enabled)
        if hasattr(win, "_autocorrect_mode_var"):
            win._autocorrect_mode_var.set(d.autocorrect_mode)
        if hasattr(win, "_digits_var"):
            win._digits_var.set(d.quickpick_digits)
        if hasattr(win, "_prediction_ui_style_var"):
            win._prediction_ui_style_var.set(d.prediction_ui_style)
        if hasattr(win, "_prediction_layout_var"):
            win._prediction_layout_var.set(d.prediction_layout)
        if hasattr(win, "_prediction_layout_display_var"):
            win._prediction_layout_display_var.set(
                t("settings.layout_vertical", "زیر هم (عمودی — پیش‌فرض)")
            )
        if hasattr(win, "_prediction_use_custom_colors_var"):
            win._prediction_use_custom_colors_var.set(d.prediction_use_custom_colors)
        for field_name, default_col in (
            ("prediction_custom_bg", d.prediction_custom_bg),
            ("prediction_custom_fg", d.prediction_custom_fg),
            ("prediction_custom_accent", d.prediction_custom_accent),
            ("prediction_custom_border", d.prediction_custom_border),
            ("prediction_custom_highlight", d.prediction_custom_highlight),
        ):
            var = getattr(win, f"_{field_name}_var", None)
            if var is not None:
                var.set(default_col)
            btn = getattr(win, f"_{field_name}_btn", None)
            if btn is not None:
                try:
                    btn.config(bg=default_col, activebackground=default_col)
                except Exception:
                    pass
        if hasattr(win, "_prediction_font_size_var"):
            win._prediction_font_size_var.set(d.prediction_font_size)
        if hasattr(win, "_prediction_opacity_var"):
            win._prediction_opacity_var.set(int(d.prediction_opacity * 100))
        if hasattr(win, "_overlay_custom_pos_var"):
            win._overlay_custom_pos_var.set(d.overlay_custom_pos)
        if hasattr(win, "_en_dict_var"):
            win._en_dict_var.set(d.english_dict_enabled)
        if hasattr(win, "_fa_dict_var"):
            win._fa_dict_var.set(d.persian_dict_enabled)
        if hasattr(win, "_debounce_var"):
            win._debounce_var.set(d.prediction_debounce_ms)
        if hasattr(win, "_maxcand_var"):
            win._maxcand_var.set(d.prediction_max_candidates)
        if hasattr(win, "_minlen_var"):
            win._minlen_var.set(d.min_prefix_len)
        if hasattr(win, "cfg"):
            win.cfg.prediction_ui_style = d.prediction_ui_style
            win.cfg.prediction_layout = d.prediction_layout
            win.cfg.prediction_use_custom_colors = d.prediction_use_custom_colors
            win.cfg.prediction_custom_bg = d.prediction_custom_bg
            win.cfg.prediction_custom_fg = d.prediction_custom_fg
            win.cfg.prediction_custom_accent = d.prediction_custom_accent
            win.cfg.prediction_custom_border = d.prediction_custom_border
            win.cfg.prediction_custom_highlight = d.prediction_custom_highlight
            if callable(getattr(win, "_render_style_preview", None)):
                win._render_style_preview()
            if getattr(win, "on_saved", None):
                win.on_saved(win.cfg)
    elif tab_name == "hotkeys":
        if hasattr(win, "_convert_var"):
            win._convert_var.set(hotkey_to_text(d.convert_hotkey))
        if hasattr(win, "_convert_scope_var"):
            win._convert_scope_var.set(d.convert_scope)
            if hasattr(win, "_convert_scope_display_var"):
                inv_map = {
                    "sentence": t("settings.convert_scope_sentence", "Last sentence / phrase (Default)"),
                    "word": t("settings.convert_scope_word", "Last word only"),
                }
                win._convert_scope_display_var.set(inv_map.get(d.convert_scope, inv_map["sentence"]))
        if hasattr(win, "_lang_var"):
            win._lang_var.set(hotkey_to_text(d.lang_indicator_hotkey))
        if hasattr(win, "_clip_var"):
            win._clip_var.set(hotkey_to_text(d.clipboard_history_hotkey))
        if hasattr(win, "_norm_var"):
            win._norm_var.set(hotkey_to_text(d.normalize_hotkey))
        if hasattr(win, "_case_var"):
            win._case_var.set(hotkey_to_text(d.case_hotkey))
        if hasattr(win, "_undo_var"):
            win._undo_var.set(hotkey_to_text(d.undo_autocorrect_hotkey))
        if hasattr(win, "_stats_var"):
            win._stats_var.set(hotkey_to_text(d.quick_stats_hotkey))
        if hasattr(win, "_pause_var"):
            win._pause_var.set(hotkey_to_text(d.pause_hotkey))
        if hasattr(win, "_translit_hotkey_var"):
            win._translit_hotkey_var.set(hotkey_to_text(d.translit_hotkey))
    elif tab_name == "autofix":
        if hasattr(win, "_autofix_mode_var"):
            win._autofix_mode_var.set(d.autofix_mode)
        if hasattr(win, "_autofix_master_var"):
            win._autofix_master_var.set(d.autofix_mode != "off")
        if hasattr(win, "_auto_layout_switch_var"):
            win._auto_layout_switch_var.set(d.auto_layout_switch)
        if hasattr(win, "_auto_layout_mode_var"):
            win._auto_layout_mode_var.set(d.auto_layout_mode)
        if hasattr(win, "_global_undo_var"):
            win._global_undo_var.set(hotkey_to_text(d.global_undo_hotkey) if d.global_undo_hotkey else "")
    elif tab_name == "exclusions":
        if hasattr(win, "_excl_text"):
            win._excl_text.delete("1.0", "end")
            win._excl_text.insert("1.0", "\n".join(DEFAULT_EXCLUDED_APPS) + "\n")
    elif tab_name == "snippets":
        win._managed_snippets = []
        win._update_snip_display()
    elif tab_name == "sync":
        if hasattr(win, "_sync_backend_var"):
            win._sync_backend_var.set(d.sync_backend)
        if hasattr(win, "_gist_token_var"):
            win._gist_token_var.set(d.gist_token)
        if hasattr(win, "_gist_id_var"):
            win._gist_id_var.set(d.gist_id)
        if hasattr(win, "_webdav_url_var"):
            win._webdav_url_var.set(d.webdav_url)
        if hasattr(win, "_webdav_username_var"):
            win._webdav_username_var.set(d.webdav_username)
        if hasattr(win, "_webdav_password_var"):
            win._webdav_password_var.set(d.webdav_password)
        if hasattr(win, "_cloud_sync_var"):
            win._cloud_sync_var.set(d.cloud_sync_enabled)
        if hasattr(win, "_sync_learning_var"):
            win._sync_learning_var.set(d.sync_learning_profile)
        if hasattr(win, "_sync_interval_var"):
            win._sync_interval_var.set(str(d.sync_interval_min))
        if hasattr(win, "_sync_status_var"):
            win._sync_status_var.set("")
