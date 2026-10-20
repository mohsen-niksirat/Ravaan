"""Tests verifying password-field and excluded-app suppression.

Guarantees that Ravaan never intercepts, suggests, autofixes, or captures text
inside password inputs, password manager apps, or user-excluded applications.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

from ravan.core.cliphistory import ClipboardHistory
from ravan.core.config import Config
from ravan.platform.focus import is_password_focused, set_mock_password_focused
from ravan.ui.app_autofix import AppAutofixMixin
from ravan.ui.app_polling import AppPollingMixin
from ravan.ui.key_handler import KeyHandlerMixin


class DummyApp(AppPollingMixin, AppAutofixMixin, KeyHandlerMixin):
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._current_exe: str | None = None
        self._current_window_class: str | None = None
        self._active_layout_tag = "en"
        self._pending_predict = False
        self._last_key_time = 0.0
        self.journal = MagicMock()
        self.journal.text.return_value = "pass"
        self.journal.last_word.return_value = "pass"
        self.overlay = MagicMock()
        self.overlay.visible = False
        self.overlay.predicting = False
        self.overlay.clipboard_open = False
        self.predictor = MagicMock()
        self.mapper = MagicMock()
        self._last_autocorrect = None
        self._ui_queue = MagicMock()
        self._init_autofix()

    def _record_event(self, *args, **kwargs):
        pass

    def _schedule_predict(self):
        self._pending_predict = True


def test_password_field_suppresses_predictions():
    cfg = Config()
    app = DummyApp(cfg)

    try:
        set_mock_password_focused(True)
        assert is_password_focused() is True

        app._pending_predict = True
        app._last_key_time = time.monotonic() - 1.0  # past debounce
        app._maybe_predict()

        # Must clear pending prediction and not call predictor
        assert app._pending_predict is False
        app.predictor.predict.assert_not_called()
    finally:
        set_mock_password_focused(None)


def test_password_field_suppresses_autofix():
    cfg = Config()
    app = DummyApp(cfg)

    try:
        set_mock_password_focused(True)
        # Mock autofix detect returning a replacement
        app.autofix.detect = MagicMock(return_value=("سلام", "fa"))
        app._replace_word = MagicMock()

        handled = app._maybe_autofix_word("sghl", delimiter=" ")
        assert handled is False
        app._replace_word.assert_not_called()
    finally:
        set_mock_password_focused(None)


def test_password_field_suppresses_key_handling():
    cfg = Config()
    app = DummyApp(cfg)
    app.overlay.visible = True

    try:
        set_mock_password_focused(True)
        event = MagicMock()
        event.vk_code = ord("A")
        event.scan_code = 0x1E

        app._handle_key(event)

        # Overlay must be hidden and journal cleared
        app.overlay.hide.assert_called()
        app.journal.clear.assert_called()
    finally:
        set_mock_password_focused(None)


def test_excluded_apps_config_matching():
    cfg = Config(excluded_apps=["keepass.exe", "1password.exe", "cmd.exe", "terminal"])

    assert cfg.is_excluded("keepass.exe") is True
    assert cfg.is_excluded("KEEPASS.EXE") is True
    assert cfg.is_excluded("keepass") is True
    assert cfg.is_excluded("1password.exe") is True
    assert cfg.is_excluded("terminal.exe") is True
    assert cfg.is_excluded("notepad.exe") is False
    assert cfg.is_excluded("chrome.exe") is False


def test_excluded_app_suppresses_predictions():
    cfg = Config(excluded_apps=["secret_tool.exe"])
    app = DummyApp(cfg)
    app._current_exe = "secret_tool.exe"

    assert app._is_excluded() is True

    app._pending_predict = True
    app._last_key_time = time.monotonic() - 1.0
    app._maybe_predict()

    # Must suppress prediction in excluded app
    app.predictor.predict.assert_not_called()


def test_excluded_app_suppresses_autofix():
    cfg = Config(excluded_apps=["keepassxc.exe"])
    app = DummyApp(cfg)
    app._current_exe = "keepassxc.exe"

    app.autofix.detect = MagicMock(return_value=("سلام", "fa"))
    app._replace_word = MagicMock()

    handled = app._maybe_autofix_word("sghl", delimiter=" ")
    assert handled is False
    app._replace_word.assert_not_called()


def test_excluded_app_suppresses_key_handling():
    cfg = Config(excluded_apps=["gamelauncher.exe"])
    app = DummyApp(cfg)
    app._current_exe = "gamelauncher.exe"
    app.overlay.visible = True

    event = MagicMock()
    event.vk_code = ord("X")
    event.scan_code = 0x2D

    app._handle_key(event)

    app.overlay.hide.assert_called()
    app.journal.clear.assert_called()


def test_clipboard_history_ignores_password_managers_and_excluded_apps():
    history = ClipboardHistory(maxlen=10)

    # 1. Password manager apps
    assert history.add("my_secret_password", source_app="keepass.exe") is False
    assert history.add("my_secret_token", source_app="1password.exe") is False
    assert history.add("my_secret_pin", source_app="bitwarden.exe") is False

    # 2. Excluded apps
    assert (
        history.add("sensitive_code", source_app="custom_private.exe", excluded_apps=["custom_private.exe"])
        is False
    )

    # 3. Normal app is accepted
    assert history.add("regular copied text", source_app="notepad.exe") is True
    assert len(history) == 1
    assert history.items()[0] == "regular copied text"
