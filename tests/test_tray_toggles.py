"""Tests for tray toggles and synchronous state updates (autocorrect, autofix, prediction)."""

from __future__ import annotations

import queue
from unittest.mock import MagicMock, patch

from ravan.core.config import Config
from ravan.ui.app_actions import AppActionsMixin
from ravan.ui.app_autofix import AppAutofixMixin
from ravan.ui.app_dialogs import AppDialogsMixin
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


class _PauseAndPowerDummyApp(DummyApp, AppActionsMixin, AppAutofixMixin, AppDialogsMixin):
    def __init__(self) -> None:
        super().__init__()
        self.is_paused = False
        self._pause_timer = None
        self._power_mode_timer = None
        self._pending_predict = True
        self.overlay = MagicMock()
        self.tray = None
        self._toast = None

    def _record_event(self, *args, **kwargs) -> None:
        pass


def test_tray_manual_pause_vs_timed_pause() -> None:
    """First tray item toggles indefinite manual pause; second toggles 10m pause/resume."""
    app = _PauseAndPowerDummyApp()
    tray = create_app_tray(app)
    tray._icon = MagicMock()
    app.tray = tray

    try:
        # 1. Click first item (manual pause -> indefinite, no timer)
        tray._toggle_manual_pause_action()
        assert app._ui_queue.get_nowait() == ("toggle_manual_pause", None)
        app._ui_queue.put(("toggle_manual_pause", None))
        with patch("ravan.platform.hook.set_popup_visible") as mock_vis:
            app._drain_ui_actions()
            mock_vis.assert_called_with(False)

        assert app.is_paused is True
        assert app._pause_timer is None
        assert tray._paused_minutes is None
        assert tray._icon.title == "Ravaan (Paused)"
        app.overlay.hide.assert_called()

        # 2. Click first item again -> resumes
        tray._toggle_manual_pause_action()
        app._drain_ui_actions()
        assert app.is_paused is False
        assert app._pause_timer is None
        assert tray._icon.title == "Ravan"

        # 3. Click second item -> 10m timed pause (starts timer)
        tray._toggle_pause_action()
        assert app._ui_queue.get_nowait() == ("toggle_pause", None)
        app._ui_queue.put(("toggle_pause", None))
        app._drain_ui_actions()

        assert app.is_paused is True
        assert app._pause_timer is not None
        assert tray._paused_minutes == 10
        assert tray._icon.title == "Ravaan (Paused ~10m)"

        # 4. Clicking first item while in 10m pause cancels timer & resumes immediately
        tray._toggle_manual_pause_action()
        app._drain_ui_actions()
        assert app.is_paused is False
        assert app._pause_timer is None
        assert tray._icon.title == "Ravan"
    finally:
        if app._pause_timer is not None:
            app._pause_timer.cancel()


def test_tray_power_mode_toggle_executes_side_effects() -> None:
    """Power Mode toggle from tray must still hide overlay, update hooks, and notify."""
    app = _PauseAndPowerDummyApp()
    with patch("ravan.core.config.save_config"):
        tray = create_app_tray(app)
        tray._icon = MagicMock()
        tray.notify = MagicMock()
        app.tray = tray

        tray._toggle_power_mode()
        assert app.power_mode_active is True
        assert tray._icon.update_menu.called

        with patch("ravan.ui.app.set_popup_visible") as mock_vis:
            app._drain_ui_actions()
            mock_vis.assert_called_with(False)
        app.overlay.hide.assert_called_once()
        tray.notify.assert_called()
        assert app.power_mode_active is True

        tray._toggle_power_mode()
        app._drain_ui_actions()
        assert app.power_mode_active is False


def test_tray_autocorrect_enables_from_off_mode() -> None:
    """Turning Autocorrect ON from tray must promote autocorrect_mode='off' to 'safe'."""
    app = _PauseAndPowerDummyApp()
    app.cfg.autocorrect_enabled = False
    app.cfg.autocorrect_mode = "off"
    app.predictor.autocorrect_mode = "off"

    with patch("ravan.core.config.save_config"):
        tray = create_app_tray(app)
        tray._icon = MagicMock()
        app.tray = tray

        tray._toggle_autocorrect()
        assert app.cfg.autocorrect_enabled is True
        assert app.cfg.autocorrect_mode == "safe"
        assert app.predictor.autocorrect_mode == "safe"


def test_tray_translit_and_open_logs_with_pystray_args() -> None:
    """Translit toggle syncs config/menu and _open_logs accepts pystray (icon, item) args."""
    app = _PauseAndPowerDummyApp()
    app.cfg.translit_enabled = False
    app.events = []

    with patch("ravan.core.config.save_config"), patch("ravan.ui.log_setup.open_logs_folder") as mock_logs:
        tray = create_app_tray(app)
        tray._icon = MagicMock()
        tray.notify = MagicMock()
        app.tray = tray

        tray._toggle_translit()
        assert app.cfg.translit_enabled is True
        assert app._ui_queue.get_nowait() == ("set_translit", True)

        # Simulate hotkey calling set_translit_enabled on main thread
        app.set_translit_enabled(False)
        assert app.cfg.translit_enabled is False
        assert tray._icon.update_menu.called

        # pystray MenuItem.__call__ invokes action(icon, item) with 2 arguments
        tray._open_logs(tray._icon, object())
        mock_logs.assert_called_once()


def test_tray_menu_items_distinct_pause_actions_and_labels() -> None:
    """Built pystray menu wires Row 1 to manual pause and Row 2 to 10m pause/resume."""
    app = _PauseAndPowerDummyApp()
    tray = create_app_tray(app)
    app.tray = tray

    captured: dict[str, object] = {}

    class FakeIcon:
        def __init__(self, name, icon, title, menu) -> None:
            captured["menu"] = menu
            self.icon = icon
            self.title = title

        def run(self) -> None:
            pass

        def update_menu(self) -> None:
            pass

        def stop(self) -> None:
            pass

        def notify(self, msg, title="") -> None:
            pass

    class ImmediateThread:
        def __init__(self, target=None, name=None, daemon=None) -> None:
            self._target = target

        def start(self) -> None:
            pass

    with patch("pystray.Icon", FakeIcon), patch("threading.Thread", ImmediateThread):
        tray.start()

    menu = captured["menu"]
    items = list(menu.items)
    row1, row2 = items[0], items[1]

    # Clicking Row 1 and Row 2 must enqueue different actions
    row1(tray._icon)
    row2(tray._icon)
    assert app._ui_queue.get_nowait() == ("toggle_manual_pause", None)
    assert app._ui_queue.get_nowait() == ("toggle_pause", None)

    # Row 1 text distinguishes active, manual pause, and timed pause
    assert "Active" in row1.text or "فعال" in row1.text
    assert "10 min" in row2.text or "۱۰ دقیقه" in row2.text

    tray.set_paused(True, 0)
    app.is_paused = True
    assert "Paused" in row1.text or "متوقف" in row1.text
    assert "10m" not in row1.text and "۱۰" not in row1.text
    assert "Resume" in row2.text or "ادامه" in row2.text

    tray.set_paused(True, 10)
    assert "10" in row1.text

    # Every Quick Toggles submenu item has checked state & Open logs takes (icon, item)
    quick_toggles_item = items[3]
    for sub in quick_toggles_item.submenu.items:
        assert sub._checked is not None

    with patch("ravan.ui.log_setup.open_logs_folder") as mock_logs:
        open_logs_item = [it for it in items if callable(getattr(it, "_action", None)) and getattr(it._action, "__name__", "") == "_open_logs"]
        assert len(open_logs_item) == 1
        open_logs_item[0](tray._icon)
        mock_logs.assert_called_once()
