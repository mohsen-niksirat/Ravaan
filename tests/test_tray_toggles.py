"""Tests for tray toggles and synchronous state updates (autocorrect, autofix, prediction)."""

from __future__ import annotations

import queue
from unittest.mock import MagicMock, patch

from ravan.core.config import Config
from ravan.ui.app_tray import create_app_tray
from ravan.ui.tray import TrayIcon


class DummyApp:
    def __init__(self) -> None:
        self.cfg = Config()
        self._ui_queue: queue.Queue = queue.Queue()
        self.predictor = MagicMock()
        self.autofix = MagicMock()
        self.power_mode_active = False


def test_tray_autocorrect_synchronous_toggle() -> None:
    """Toggling autocorrect via tray must synchronously update app.cfg immediately."""
    app = DummyApp()
    app.cfg.autocorrect_enabled = True

    with patch("ravan.core.config.save_config") as mock_save:
        tray = create_app_tray(app)
        tray._icon = MagicMock()

        # Simulate tray clicking autocorrect toggle (should turn off)
        tray._toggle_autocorrect()

        # Config must be mutated immediately without waiting for queue processing
        assert app.cfg.autocorrect_enabled is False
        assert app.predictor.autocorrect_mode == "off"
        mock_save.assert_called()
        tray._icon.update_menu.assert_called()

        # UI queue must have the corresponding action for main thread
        action, val = app._ui_queue.get_nowait()
        assert action == "set_autocorrect"
        assert val is False

        # Simulate second click (should turn back on)
        tray._toggle_autocorrect()
        assert app.cfg.autocorrect_enabled is True
        assert app.predictor.autocorrect_mode == "safe"


def test_tray_autofix_synchronous_toggle() -> None:
    """Toggling auto-fix layout via tray must synchronously update app.cfg immediately."""
    app = DummyApp()
    app.cfg.autofix_mode = "safe"
    assert app.cfg.autofix_wrong_layout is True

    with patch("ravan.core.config.save_config") as mock_save:
        tray = create_app_tray(app)
        tray._icon = MagicMock()

        # Simulate clicking auto-fix toggle in tray
        tray._toggle_autofix()

        # Must immediately be False
        assert app.cfg.autofix_wrong_layout is False
        assert app.cfg.autofix_mode == "off"
        assert app.autofix.mode == "off"
        mock_save.assert_called()
        tray._icon.update_menu.assert_called()

        # UI queue
        action, val = app._ui_queue.get_nowait()
        assert action == "set_autofix"
        assert val is False

        # Toggle back on
        tray._toggle_autofix()
        assert app.cfg.autofix_wrong_layout is True
        assert app.cfg.autofix_mode == "safe"
        assert app.autofix.mode == "safe"


def test_tray_prediction_and_zwnj_synchronous_toggle() -> None:
    """Prediction and auto-ZWNJ toggles update config synchronously."""
    app = DummyApp()
    app.cfg.prediction_enabled = True
    app.cfg.auto_zwnj_enabled = True

    with patch("ravan.core.config.save_config"):
        tray = create_app_tray(app)
        tray._icon = MagicMock()

        tray._toggle_prediction()
        assert app.cfg.prediction_enabled is False

        tray._toggle_auto_zwnj()
        assert app.cfg.auto_zwnj_enabled is False


def test_tray_icon_callbacks_and_update_menu() -> None:
    """TrayIcon calls update_menu on all toggles."""
    on_toggle_autofix = MagicMock()
    is_autofix = MagicMock(return_value=True)

    tray = TrayIcon(
        on_quit=MagicMock(),
        on_toggle_autofix=on_toggle_autofix,
        is_autofix_enabled=is_autofix,
    )
    tray._icon = MagicMock()

    tray._toggle_autofix()
    on_toggle_autofix.assert_called_once_with(False)
    tray._icon.update_menu.assert_called_once()
