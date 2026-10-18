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
