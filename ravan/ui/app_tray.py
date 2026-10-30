"""Factory for creating and configuring the system tray icon for RavanApp."""

from __future__ import annotations

from typing import Any

from ravan.ui.tray import TrayIcon


def create_app_tray(app: Any) -> TrayIcon:
    """Instantiate and configure TrayIcon for RavanApp with synchronous state updates."""

    def _set_prediction(val: bool) -> None:
        app.cfg.prediction_enabled = bool(val)
        try:
            from ravan.core.config import save_config

            save_config(app.cfg)
        except Exception:
            pass
        app._ui_queue.put(("set_prediction", val))

    def _set_autocorrect(val: bool) -> None:
        app.cfg.autocorrect_enabled = bool(val)
        if hasattr(app, "predictor") and app.predictor is not None:
            app.predictor.autocorrect_mode = app.cfg.autocorrect_mode if val else "off"
        try:
            from ravan.core.config import save_config

            save_config(app.cfg)
        except Exception:
            pass
        app._ui_queue.put(("set_autocorrect", val))

    def _set_autofix(val: bool) -> None:
        app.cfg.autofix_wrong_layout = bool(val)
        if hasattr(app, "autofix") and app.autofix is not None:
            app.autofix.mode = "safe" if val else "off"
        try:
            from ravan.core.config import save_config

            save_config(app.cfg)
        except Exception:
            pass
        app._ui_queue.put(("set_autofix", val))

    def _set_auto_zwnj(val: bool) -> None:
        app.cfg.auto_zwnj_enabled = bool(val)
        try:
            from ravan.core.config import save_config

            save_config(app.cfg)
        except Exception:
            pass
        app._ui_queue.put(("set_auto_zwnj", val))

    def _toggle_translit() -> None:
        target = not bool(getattr(app.cfg, "translit_enabled", False))
        app.cfg.translit_enabled = target
        try:
            from ravan.core.config import save_config

            save_config(app.cfg)
        except Exception:
            pass
        app._ui_queue.put(("set_translit", target))

    def _toggle_power_mode() -> None:
        target = not getattr(app, "power_mode_active", False)
        app.power_mode_active = target
        if hasattr(app, "tray") and app.tray is not None:
            app.tray.set_power_mode(target)
        app._ui_queue.put(("set_power_mode", target))

    return TrayIcon(
        on_quit=lambda: app._ui_queue.put(("quit", None)),
        on_show_lang=lambda: app._ui_queue.put(("show_lang", None)),
        on_settings=lambda: app._ui_queue.put(("settings", None)),
        on_snippets=lambda: app._ui_queue.put(("snippets", None)),
        on_diagnostics=lambda: app._ui_queue.put(("diagnostics", None)),
        on_toggle_prediction=_set_prediction,
        is_prediction_enabled=lambda: app.cfg.prediction_enabled,
        on_update_found=lambda info: app._ui_queue.put(("show_update", info)),
        on_toggle_power_mode=_toggle_power_mode,
        is_power_mode_active=lambda: getattr(app, "power_mode_active", False),
        on_record_macro=lambda: app._ui_queue.put(("start_macro_recording", None)),
        on_toggle_autocorrect=_set_autocorrect,
        is_autocorrect_enabled=lambda: app.cfg.autocorrect_enabled,
        on_toggle_autofix=_set_autofix,
        is_autofix_enabled=lambda: app.cfg.autofix_wrong_layout,
        on_toggle_auto_zwnj=_set_auto_zwnj,
        is_auto_zwnj_enabled=lambda: app.cfg.auto_zwnj_enabled,
        on_toggle_pause=lambda: app._ui_queue.put(("toggle_pause", None)),
        is_paused=lambda: getattr(app, "is_paused", False),
        on_toggle_translit=_toggle_translit,
        is_translit_enabled=lambda: bool(getattr(app.cfg, "translit_enabled", False)),
        on_clean_clipboard=lambda: app._ui_queue.put(("clean_clipboard", None)),
        on_quick_tips=lambda: app._ui_queue.put(("quick_tips", None)),
    )
