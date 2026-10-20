"""Tests for QuickTipsWindow, HintManager, and dedicated pause hotkey."""

from __future__ import annotations

import queue
import tkinter as tk
from unittest.mock import MagicMock, patch

from ravan.core.config import Config, HotkeySpec, config_from_dict, config_to_dict
from ravan.platform.hook import HookEvent
from ravan.ui.hint_manager import HintManager
from ravan.ui.key_handler import KeyHandlerMixin
from ravan.ui.quick_tips import QuickTipsWindow, _get_tips_data


class DummyApp(KeyHandlerMixin):
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.is_paused = False
        self._suppress_until = 0.0
        self._last_convert_at = 0.0
        self._ui_queue: queue.Queue = queue.Queue()
        self.overlay = MagicMock()
        self.overlay.clipboard_open = False
        self.overlay.predicting = False
        self.overlay.visible = False
        self.recent_events = []
        self._root = None

    def _is_foreground_self(self) -> bool:
        return False

    def _record_event(self, action: str, vk: int = 0, char: str = "") -> None:
        pass


def test_config_pause_and_hints_serialization(tmp_path):
    cfg = Config(
        pause_hotkey=HotkeySpec("Pause", ["Ctrl", "Alt"]),
        enable_feature_hints=True,
        shown_hints=["hint_zwnj"],
    )
    d = config_to_dict(cfg)
    assert d["pause_hotkey"]["key"] == "Pause"
    assert "Ctrl" in d["pause_hotkey"]["modifiers"]
    assert "Alt" in d["pause_hotkey"]["modifiers"]
    assert d["enable_feature_hints"] is True
    assert "hint_zwnj" in d["shown_hints"]

    loaded = config_from_dict(d)
    assert loaded.pause_hotkey.key == "Pause"
    assert loaded.pause_hotkey.modifiers == ["Ctrl", "Alt"]
    assert loaded.enable_feature_hints is True
    assert loaded.shown_hints == ["hint_zwnj"]


def test_hint_manager_max_once_and_persistence(tmp_path):
    cfg = Config(
        enable_feature_hints=True,
        shown_hints=[],
    )
    toast_messages = []

    def fake_toast(msg: str):
        toast_messages.append(msg)

    with patch("ravan.ui.hint_manager.save_config") as mock_save:
        manager = HintManager(cfg, on_show_toast=fake_toast)

        assert manager.should_show("tip_zwnj") is True
        res1 = manager.show_hint("tip_zwnj", "Use Shift+Space for half-space")
        assert res1 is True
        assert len(toast_messages) == 1
        assert "tip_zwnj" in cfg.shown_hints
        assert mock_save.called

        # Second call must be suppressed (max once per feature rule)
        res2 = manager.show_hint("tip_zwnj", "Use Shift+Space for half-space")
        assert res2 is False
        assert len(toast_messages) == 1

        # Dismiss forever
        manager.dismiss_forever("tip_calc")
        assert "tip_calc" in cfg.shown_hints
        assert manager.should_show("tip_calc") is False

        # Global hints disable
        manager.dismiss_forever(None)
        assert cfg.enable_feature_hints is False
        assert manager.should_show("tip_any") is False

        # Reset all hints
        manager.reset_all_hints()
        assert cfg.shown_hints == []


def test_tips_data_categories():
    data = _get_tips_data()
    assert len(data) >= 3
    categories = [cat["category"] for cat in data]
    assert any("Keyboard Shortcuts" in c or "میانبر" in c for c in categories)
    assert any("Features" in c or "قابلیت" in c for c in categories)
    assert any("Privacy" in c or "امنیت" in c for c in categories)

    total_items = sum(len(cat["items"]) for cat in data)
    assert total_items >= 10


def test_quick_tips_window_lifecycle_and_search():
    root = tk.Tk()
    root.withdraw()
    try:
        cfg = Config(theme_mode="light")
        win = QuickTipsWindow(parent=root, cfg=cfg)
        win.show()
        assert win._top is not None
        assert win._top.winfo_exists()

        # Check search filtering
        win._search_var.set("Pause")
        root.update()

        win._search_var.set("nonexistent_xyz_query")
        root.update()
        assert win._no_results_lbl is not None

        # Reset search
        win._search_var.set("")
        root.update()

        win.tick()
        win.close()
        assert win._top is None
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def test_pause_hotkey_dispatches_when_active():
    from ravan.platform import winapi as w

    cfg = Config(
        pause_hotkey=HotkeySpec("Pause", ["Ctrl", "Alt"]),
    )
    app = DummyApp(cfg)

    # Simulate Ctrl+Alt pressed
    with patch("ravan.platform.keys.w.user32.GetAsyncKeyState") as mock_async_state:
        def async_key_state(vk):
            if vk in (w.VK_CONTROL, w.VK_MENU):
                return 0x8000
            return 0
        mock_async_state.side_effect = async_key_state

        event = HookEvent(vk_code=w.VK_PAUSE, scan_code=0, is_key_down=True, flags=0)
        app._handle_key(event)

        assert not app._ui_queue.empty()
        action, _ = app._ui_queue.get_nowait()
        assert action == "toggle_pause"


def test_pause_hotkey_dispatches_when_paused():
    from ravan.platform import winapi as w

    cfg = Config(
        pause_hotkey=HotkeySpec("Pause", ["Ctrl", "Alt"]),
    )
    app = DummyApp(cfg)
    app.is_paused = True

    # Simulate Ctrl+Alt pressed
    with patch("ravan.platform.keys.w.user32.GetAsyncKeyState") as mock_async_state:
        def async_key_state(vk):
            if vk in (w.VK_CONTROL, w.VK_MENU):
                return 0x8000
            return 0
        mock_async_state.side_effect = async_key_state

        event = HookEvent(vk_code=w.VK_PAUSE, scan_code=0, is_key_down=True, flags=0)
        app._handle_key(event)

        assert not app._ui_queue.empty()
        action, _ = app._ui_queue.get_nowait()
        assert action == "toggle_pause"
