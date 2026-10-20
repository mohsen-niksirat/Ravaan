"""Factory for creating and configuring the system tray icon for RavanApp."""

from __future__ import annotations

from typing import Any

from ravan.ui.tray import TrayIcon


def create_app_tray(app: Any) -> TrayIcon:
    """Instantiate and configure TrayIcon for RavanApp."""
    return TrayIcon(
        on_quit=lambda: app._ui_queue.put(("quit", None)),
        on_show_lang=lambda: app._ui_queue.put(("show_lang", None)),
        on_settings=lambda: app._ui_queue.put(("settings", None)),
        on_snippets=lambda: app._ui_queue.put(("snippets", None)),
        on_diagnostics=lambda: app._ui_queue.put(("diagnostics", None)),
        on_toggle_prediction=lambda val: app._ui_queue.put(("set_prediction", val)),
        is_prediction_enabled=lambda: app.cfg.prediction_enabled,
        on_update_found=lambda info: app._ui_queue.put(("show_update", info)),
        on_toggle_power_mode=lambda: app._ui_queue.put(("toggle_power_mode", None)),
        is_power_mode_active=lambda: getattr(app, "power_mode_active", False),
        on_record_macro=lambda: app._ui_queue.put(("start_macro_recording", None)),
        on_toggle_autocorrect=lambda val: app._ui_queue.put(("set_autocorrect", val)),
        is_autocorrect_enabled=lambda: app.cfg.autocorrect_enabled,
        on_toggle_auto_zwnj=lambda val: app._ui_queue.put(("set_auto_zwnj", val)),
        is_auto_zwnj_enabled=lambda: app.cfg.auto_zwnj_enabled,
        on_toggle_pause=lambda: app._ui_queue.put(("toggle_pause", None)),
        is_paused=lambda: getattr(app, "is_paused", False),
        on_toggle_translit=lambda: app._ui_queue.put(("toggle_translit", None)),
        is_translit_enabled=lambda: bool(getattr(app.cfg, "translit_enabled", False)),
        on_clean_clipboard=lambda: app._ui_queue.put(("clean_clipboard", None)),
        on_quick_tips=lambda: app._ui_queue.put(("quick_tips", None)),
    )
