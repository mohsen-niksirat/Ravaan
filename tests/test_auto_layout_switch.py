"""Platform-level tests for Phase 3: Auto layout switch on detection."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from ravan.core.config import Config
from ravan.core.events import LanguageInfo
from ravan.platform.lang import (
    get_installed_layouts,
    get_layout_for_language,
    is_ime_composing,
    switch_to_language,
)
from ravan.ui.app import RavanApp


def test_get_installed_layouts_mocked() -> None:
    # Simulate 2 installed layouts: English (0x04090409) and Persian (0x04290429)
    with patch("ravan.platform.winapi.user32.GetKeyboardLayoutList") as mock_list:
        def side_effect(count: int, buf: Any) -> int:
            if buf is None:
                return 2
            buf[0] = 0x04090409
            buf[1] = 0x04290429
            return 2

        mock_list.side_effect = side_effect
        layouts = get_installed_layouts()
        assert len(layouts) == 2
        assert any(layout.tag == "en" for layout in layouts)
        assert any(layout.tag == "fa" for layout in layouts)


def test_get_layout_for_language() -> None:
    with patch("ravan.platform.lang.get_installed_layouts") as mock_installed:
        mock_installed.return_value = [
            LanguageInfo(tag="en", name="English", hkl=0x04090409),
            LanguageInfo(tag="fa", name="Persian", hkl=0x04290429),
        ]
        assert get_layout_for_language("en") == 0x04090409
        assert get_layout_for_language("fa") == 0x04290429
        assert get_layout_for_language("unknown") is None


def test_switch_to_language() -> None:
    with (
        patch("ravan.platform.lang.get_layout_for_language") as mock_get,
        patch("ravan.platform.winapi.user32.GetForegroundWindow") as mock_fg,
        patch("ravan.platform.winapi.user32.PostMessageW") as mock_post,
        patch("ravan.platform.winapi.user32.ActivateKeyboardLayout") as mock_activate,
    ):
        mock_get.return_value = 0x04290429
        mock_fg.return_value = 12345

        res = switch_to_language("fa")
        assert res is True
        mock_post.assert_called_once_with(12345, 0x0050, 0, 0x04290429)
        mock_activate.assert_called_once_with(0x04290429, 0x00000100)


def test_is_ime_composing() -> None:
    with (
        patch("ravan.platform.winapi.user32.GetForegroundWindow") as mock_fg,
        patch("ctypes.windll.imm32.ImmGetContext") as mock_ctx,
        patch("ctypes.windll.imm32.ImmGetCompositionStringW") as mock_comp,
        patch("ctypes.windll.imm32.ImmReleaseContext"),
    ):
        mock_fg.return_value = 100
        mock_ctx.return_value = 200

        # No composition string
        mock_comp.return_value = 0
        assert is_ime_composing() is False

        # Active composition string length 4
        mock_comp.return_value = 4
        assert is_ime_composing() is True


def test_auto_layout_switch_modes() -> None:
    cfg = Config()
    cfg.auto_layout_switch = True
    app = RavanApp(cfg)
    app._replace_word = MagicMock()
    app._maybe_switch_keyboard_layout = MagicMock()

    # 1. Mode: fix_only -> replaces word, does not switch layout
    cfg.auto_layout_mode = "fix_only"
    handled = app._maybe_autofix_word("sghl")
    assert handled is True
    app._replace_word.assert_called_once()
    app._maybe_switch_keyboard_layout.assert_not_called()

    # 2. Mode: switch_only -> does not replace word, switches layout
    app._replace_word.reset_mock()
    app._maybe_switch_keyboard_layout.reset_mock()
    cfg.auto_layout_mode = "switch_only"
    handled = app._maybe_autofix_word("sghl")
    assert handled is True
    app._replace_word.assert_not_called()
    app._maybe_switch_keyboard_layout.assert_called_once_with("fa")

    # 3. Mode: fix_and_switch -> replaces word AND switches layout
    app._replace_word.reset_mock()
    app._maybe_switch_keyboard_layout.reset_mock()
    cfg.auto_layout_mode = "fix_and_switch"
    handled = app._maybe_autofix_word("sghl")
    assert handled is True
    app._replace_word.assert_called_once()
    app._maybe_switch_keyboard_layout.assert_called_once_with("fa")


def test_auto_layout_switch_suppressed_in_excluded_passwords_ime() -> None:
    cfg = Config()
    cfg.auto_layout_switch = True
    cfg.auto_layout_mode = "fix_and_switch"
    app = RavanApp(cfg)
    app._replace_word = MagicMock()
    app._maybe_switch_keyboard_layout = MagicMock()

    # Password focused: layout switch must be suppressed
    with patch("ravan.platform.focus.is_password_focused", return_value=True):
        app._maybe_autofix_word("sghl")
        app._maybe_switch_keyboard_layout.assert_not_called()

    # IME active: layout switch must be suppressed
    with (
        patch("ravan.platform.focus.is_password_focused", return_value=False),
        patch("ravan.platform.lang.is_ime_composing", return_value=True),
    ):
        app._maybe_autofix_word("sghl")
        app._maybe_switch_keyboard_layout.assert_not_called()
