"""Unit tests for v2.6.0 features:
- Autocorrect disabled by default
- Enter does not accept predictions by default (only digits 1-5 or explicit accept)
- Mouse click language indicator
- Language chip formatting (FA, EN, translit) and cursor fallback
- Application icon presence and valid ICO resolutions
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from ravan.core.config import Config
from ravan.core.events import Candidate
from ravan.platform import winapi as w
from ravan.platform.caret import CaretRect
from ravan.platform.hook import HookEvent
from ravan.ui.app_actions import AppActionsMixin
from ravan.ui.app_polling import AppPollingMixin
from ravan.ui.key_handler import KeyHandlerMixin
from ravan.ui.overlay import OverlayWindow


def test_autocorrect_disabled_by_default():
    cfg = Config()
    assert cfg.autocorrect_enabled is False
    assert cfg.suggestion_accept_enter is False
    assert cfg.show_lang_on_click is True


def test_format_lang_label():
    assert OverlayWindow._format_lang_label("فا") == "🇮🇷 فارسی"
    assert OverlayWindow._format_lang_label("FA") == "🇮🇷 فارسی"
    assert OverlayWindow._format_lang_label("EN") == "🇺🇸 English"
    assert OverlayWindow._format_lang_label("فا-TL") == "🔤 فینگلیش (FA)"
    assert OverlayWindow._format_lang_label("FA-TL") == "🔤 فینگلیش (FA)"
    assert OverlayWindow._format_lang_label("AR") == "🇸🇦 العربية"


def test_show_language_fallback_to_cursor():
    overlay = OverlayWindow()
    try:
        with patch(
            "ravan.platform.caret._cursor_position",
            return_value=CaretRect(x=350, y=420, width=2, height=16),
        ):
            overlay.show_language("فا", 0, 0, 16)
            assert overlay._mode == "lang"
            assert overlay.current_x > 0 or overlay.current_y > 0
    finally:
        overlay.destroy()


class DummyJournal:
    def __init__(self):
        self.items = []

    def push(self, ch):
        self.items.append(ch)

    def pop_last_word_info(self, **kwargs):
        pass

    def clear(self):
        self.items.clear()


class DummyKeyApp(KeyHandlerMixin, AppActionsMixin):
    def __init__(self, cfg=None):
        self.cfg = cfg or Config()
        self.journal = DummyJournal()
        self._ui_queue = MagicMock()
        self.hook = MagicMock()
        self.overlay = MagicMock()
        self.overlay.visible = True
        self.overlay.predicting = True
        self.overlay.clipboard_open = False
        self._accepted = []
        self._last_convert_at = 0.0
        self._last_autocorrect = None
        self._suppress_until = 0.0

    def _record_event(self, *args, **kwargs):
        pass

    def _accept_candidate(self, cand):
        self._accepted.append(cand)


def test_enter_does_not_accept_candidate_when_disabled():
    app = DummyKeyApp()
    app.cfg.suggestion_accept_enter = False
    app.overlay.accept_selected.return_value = Candidate("تست", 1.0, "dict")

    # When user presses Enter
    ev = HookEvent(vk_code=w.VK_RETURN, flags=0, scan_code=28, is_key_down=True)
    with patch("ravan.platform.hook._is_shift_pressed", return_value=False):
        app._handle_key(ev)

    # Candidate was NOT accepted
    assert len(app._accepted) == 0
    # Overlay was hidden
    app.overlay.hide.assert_called()
    # Newline was added to journal
    assert "\n" in app.journal.items


def test_digits_accept_candidate():
    app = DummyKeyApp()
    app.cfg.quickpick_digits = True
    app.overlay.accept_index.return_value = Candidate("گزینه۱", 1.0, "dict")

    # Press '1'
    ev = HookEvent(vk_code=ord("1"), flags=0, scan_code=2, is_key_down=True)
    app._handle_key(ev)

    # Candidate 1 was accepted
    assert len(app._accepted) == 1
    assert app._accepted[0].text == "گزینه۱"


class DummyPollingApp(AppPollingMixin, AppActionsMixin):
    def __init__(self, cfg=None):
        self.cfg = cfg or Config()
        self.overlay = MagicMock()
        self.overlay.predicting = False
        self._mouse_left_down = False
        self._mouse_down_time = 0.0
        self._mouse_down_pos = None
        self._last_mouse_lang_shown = 0.0
        self._shown_langs = []

    def _is_excluded(self):
        return False

    def _is_foreground_self(self):
        return False

    def _show_lang_indicator(self, use_mouse_pos=False):
        self._shown_langs.append(use_mouse_pos)


def test_poll_mouse_click_triggers_lang_indicator():
    app = DummyPollingApp()
    app.cfg.show_lang_on_click = True
    base_t = 1000.0

    # 1. Mouse button goes down
    with patch("ravan.platform.winapi.user32.GetAsyncKeyState", return_value=0x8000), \
         patch("ravan.platform.caret._cursor_position", return_value=CaretRect(200, 300, 2, 16)), \
         patch("time.monotonic", return_value=base_t):
        app._poll_mouse_click()
        assert app._mouse_left_down is True

    # 2. Mouse button released -> pending single click scheduled
    with patch("ravan.platform.winapi.user32.GetAsyncKeyState", return_value=0), \
         patch("ravan.platform.caret._cursor_position", return_value=CaretRect(201, 301, 2, 16)), \
         patch("time.monotonic", return_value=base_t + 0.05):
        app._poll_mouse_click()
        assert app._mouse_left_down is False
        assert getattr(app, "_pending_click_time", None) == base_t + 0.05
        assert len(app._shown_langs) == 0  # not yet, awaiting settle to protect double-clicks

    # 3. Settling time elapsed without second click (single click confirmed, caret active)
    with patch("ravan.platform.winapi.user32.GetAsyncKeyState", return_value=0), \
         patch("time.monotonic", return_value=base_t + 0.30), \
         patch("ravan.platform.caret.is_text_caret_active", return_value=True):
        app._poll_mouse_click()
        assert getattr(app, "_pending_click_time", None) is None
        assert len(app._shown_langs) == 1
        assert app._shown_langs[0] is True  # use_mouse_pos


def test_poll_mouse_click_ignores_empty_background_when_no_caret():
    app = DummyPollingApp()
    app.cfg.show_lang_on_click = True
    base_t = 1000.0

    # Mouse down
    with patch("ravan.platform.winapi.user32.GetAsyncKeyState", return_value=0x8000), \
         patch("ravan.platform.caret._cursor_position", return_value=CaretRect(200, 300, 2, 16)), \
         patch("time.monotonic", return_value=base_t):
        app._poll_mouse_click()
        assert app._mouse_left_down is True

    # Mouse up
    with patch("ravan.platform.winapi.user32.GetAsyncKeyState", return_value=0), \
         patch("ravan.platform.caret._cursor_position", return_value=CaretRect(200, 300, 2, 16)), \
         patch("time.monotonic", return_value=base_t + 0.05):
        app._poll_mouse_click()
        assert app._mouse_left_down is False

    # Settling time elapsed on empty page/wallpaper (no text caret)
    with patch("ravan.platform.winapi.user32.GetAsyncKeyState", return_value=0), \
         patch("time.monotonic", return_value=base_t + 0.30), \
         patch("ravan.platform.caret.is_text_caret_active", return_value=False):
        app._poll_mouse_click()
        # Indicator MUST NOT be shown on empty canvas/desktop
        assert len(app._shown_langs) == 0


def test_poll_mouse_click_aborts_on_double_click_or_touchpad_double_tap():
    """Touchpad double-tap or mouse double-click must abort single-click indicator cleanly."""
    app = DummyPollingApp()
    app.cfg.show_lang_on_click = True
    base_t = 1000.0

    # 1. Tap 1 down
    with patch("ravan.platform.winapi.user32.GetAsyncKeyState", return_value=0x8000), \
         patch("ravan.platform.caret._cursor_position", return_value=CaretRect(200, 300, 2, 16)), \
         patch("time.monotonic", return_value=base_t):
        app._poll_mouse_click()
        assert app._mouse_left_down is True

    # 2. Tap 1 up (40ms later)
    with patch("ravan.platform.winapi.user32.GetAsyncKeyState", return_value=0), \
         patch("ravan.platform.caret._cursor_position", return_value=CaretRect(200, 300, 2, 16)), \
         patch("time.monotonic", return_value=base_t + 0.04):
        app._poll_mouse_click()
        assert app._mouse_left_down is False
        assert getattr(app, "_pending_click_time", None) == base_t + 0.04

    # 3. Tap 2 down (120ms after Tap 1 up -> double-tap in progress!)
    with patch("ravan.platform.winapi.user32.GetAsyncKeyState", return_value=0x8000), \
         patch("time.monotonic", return_value=base_t + 0.16):
        app._poll_mouse_click()
        assert app._mouse_left_down is True
        # Pending click must be ABORTED immediately so double-click is never blocked!
        assert getattr(app, "_pending_click_time", None) is None
        assert getattr(app, "_last_double_click_time", 0.0) == base_t + 0.16
        assert len(app._shown_langs) == 0

    # 4. Tap 2 up (40ms later) -> recognized as part of double-click
    with patch("ravan.platform.winapi.user32.GetAsyncKeyState", return_value=0), \
         patch("time.monotonic", return_value=base_t + 0.20):
        app._poll_mouse_click()
        assert app._mouse_left_down is False
        assert getattr(app, "_pending_click_time", None) is None
        assert len(app._shown_langs) == 0



def test_app_icon_validity():
    repo_root = Path(__file__).resolve().parent.parent
    ico_path = repo_root / "ravan" / "data" / "icon.ico"
    png_path = repo_root / "ravan" / "data" / "icon.png"

    assert ico_path.is_file()
    assert png_path.is_file()

    with Image.open(png_path) as im:
        assert im.size == (512, 512)
        assert im.mode == "RGBA"

    with Image.open(ico_path) as im:
        sizes = im.info.get("sizes", set())
        assert (256, 256) in sizes
        assert (48, 48) in sizes
        assert (32, 32) in sizes
        assert (16, 16) in sizes
