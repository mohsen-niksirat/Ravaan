"""Dialog opening and management mixin for RavanApp."""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class AppDialogsMixin:
    """Mixin for opening auxiliary windows and dialogs in RavanApp."""

    def open_settings(self: Any) -> None:
        if self._settings_window is not None and self._settings_window.open:
            return
        from ravan.ui.settings import SettingsWindow

        self._settings_window = SettingsWindow(
            self.cfg, on_saved=self._on_settings_saved
        )
        self._settings_window.show()

    def open_snippet_editor(self: Any) -> None:
        if self._snippet_window is not None and self._snippet_window.open:
            return
        from ravan.ui.snippet_editor import SnippetEditorWindow

        self._snippet_window = SnippetEditorWindow(
            self.cfg.snippets, on_saved=self._on_snippets_saved
        )
        self._snippet_window.show()

    def _on_snippets_saved(self: Any, snippets: list[Any]) -> None:
        self.cfg.snippets = snippets
        from ravan.core.config import save_config
        from ravan.core.snippet import SnippetEngine

        self.snippets = SnippetEngine.from_config(self.cfg)
        save_config(self.cfg)
        from ravan.core.i18n import t

        self.tray.notify(
            t(
                "notifications.snippets_saved",
                "Saved {count} snippets",
                count=len(snippets),
            )
        )

    def open_diagnostics(self: Any) -> None:
        if self._diagnostics_window is not None and self._diagnostics_window.open:
            return
        from ravan.ui.diagnostics import DiagnosticsWindow

        self._diagnostics_window = DiagnosticsWindow(
            snapshot_fn=self._get_diagnostics_snapshot
        )
        self._diagnostics_window.show()

    def _show_update_dialog(self: Any, release_info: dict[str, Any]) -> None:
        from ravan.ui.update_dialog import UpdateDialog

        def on_exit() -> None:
            if hasattr(self, "_single_instance") and self._single_instance:
                self._single_instance.release()
            self.stop()

        dialog = UpdateDialog(release_info, on_ready_to_exit=on_exit)
        dialog.show()

    def _show_onboarding(self: Any) -> None:
        if getattr(self, "_wizard_window", None) is not None and self._wizard_window.open:
            return
        from ravan.ui.wizard import FirstRunWizard

        parent = getattr(self.overlay, "_root", None)
        self._wizard_window = FirstRunWizard(
            self.cfg,
            on_complete=None,
            parent=parent,
        )
        self._wizard_window.show()

    def _drain_ui_actions(self: Any) -> None:
        import queue

        while True:
            try:
                action, arg = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            if action == "quit":
                self.stop()
                break
            elif action == "show_lang":
                self._show_lang_indicator()
            elif action == "settings":
                self.open_settings()
            elif action == "snippets":
                self.open_snippet_editor()
            elif action == "diagnostics":
                self.open_diagnostics()
            elif action == "set_prediction":
                self.set_prediction_enabled(bool(arg))
            elif action == "set_autocorrect":
                self.set_autocorrect_enabled(bool(arg))
            elif action == "set_auto_zwnj":
                self.set_auto_zwnj_enabled(bool(arg))
            elif action == "toggle_pause":
                self.toggle_pause()
            elif action == "quick_stats":
                self._show_quick_text_stats()
            elif action == "show_update":
                self._show_update_dialog(arg)
            elif action == "toggle_power_mode":
                self.toggle_power_mode()
            elif action == "start_macro_recording":
                self.start_macro_recording()
            elif action == "stop_macro_recording":
                self.stop_macro_recording()
            elif action == "toggle_translit":
                if hasattr(self, "_toggle_translit"):
                    self._toggle_translit()
            elif action == "clean_clipboard":
                if hasattr(self, "_clean_clipboard_text"):
                    self._clean_clipboard_text()

    def set_prediction_enabled(self: Any, enabled: bool) -> None:
        self.cfg.prediction_enabled = enabled
        from ravan.core.config import save_config

        save_config(self.cfg)
        if not enabled:
            self.overlay.hide()

    def set_autocorrect_enabled(self: Any, enabled: bool) -> None:
        self.cfg.autocorrect_enabled = enabled
        from ravan.core.config import save_config

        save_config(self.cfg)

    def set_auto_zwnj_enabled(self: Any, enabled: bool) -> None:
        self.cfg.auto_zwnj_enabled = enabled
        from ravan.core.config import save_config

        save_config(self.cfg)

    def toggle_pause(self: Any, minutes: int = 10) -> None:
        import threading

        from ravan.core.i18n import t

        self.is_paused = not getattr(self, "is_paused", False)
        if self._pause_timer:
            self._pause_timer.cancel()
            self._pause_timer = None
        if self.is_paused:
            self.overlay.hide()
            self._pause_timer = threading.Timer(minutes * 60, self._auto_resume)
            self._pause_timer.daemon = True
            self._pause_timer.start()
            msg = t("tray.paused_msg", "Ravaan paused for {min} minutes.", min=minutes)
        else:
            msg = t("tray.resumed_msg", "Ravaan resumed.")
        if hasattr(self.tray, "set_paused"):
            self.tray.set_paused(self.is_paused, minutes if self.is_paused else 0)
        self.tray.notify(msg, title="Ravaan")

    def _auto_resume(self: Any) -> None:
        if getattr(self, "is_paused", False):
            self._ui_queue.put(("toggle_pause", None))
