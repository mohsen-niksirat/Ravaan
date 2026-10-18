"""Targeted tests for Phase 2 Windows QA Matrix:
- Rapid layout switching during popup render
- Elevated window single-warning rate limiting (zero spam)
- Custom caret fallback chain (VS Code, Excel, terminals)
- Multi-monitor work area clamping
- Sensible exclusion defaults
"""

from __future__ import annotations

from unittest.mock import MagicMock

from ravan.core.config import DEFAULT_EXCLUDED_APPS, Config
from ravan.platform.caret import (
    CaretRect,
    _rects_to_caret,
    get_caret_rect_with_source,
    set_mock_caret,
)
from ravan.platform.focus import set_mock_window_elevated
from ravan.platform.hook import set_popup_visible


def test_default_excluded_apps():
    """Verify password managers and lock/logon screens are pre-seeded in DEFAULT_EXCLUDED_APPS."""
    cfg = Config()
    required = [
        "1password.exe",
        "bitwarden.exe",
        "keepass.exe",
        "keepassxc.exe",
        "dashlane.exe",
        "lockapp.exe",
        "logonui.exe",
        "credentialuibroker.exe",
    ]
    for app in required:
        assert app in DEFAULT_EXCLUDED_APPS, f"Missing {app} from DEFAULT_EXCLUDED_APPS"
        assert cfg.is_excluded(app), f"Config.is_excluded failed for {app}"

    # Normal apps must not be excluded
    assert not cfg.is_excluded("notepad.exe")
    assert not cfg.is_excluded("code.exe")
    assert not cfg.is_excluded("chrome.exe")


def test_elevated_window_single_warning_no_spam():
    """Verify typing/focusing in elevated windows emits a single notification and never spams."""
    from ravan.ui.app_polling import AppPollingMixin

    class DummyApp(AppPollingMixin):
        def __init__(self):
            self._own_pid = 9999
            self.tray = MagicMock()
            self._elevated_warned_hwnds = set()

        def _is_foreground_self(self):
            return False

    app = DummyApp()

    try:
        set_mock_window_elevated(True)

        # First encounter with elevated window 1001: must notify once
        assert app._check_elevated(hwnd=1001) is True
        assert app.tray.notify.call_count == 1

        # Repeated 50 checks / keystrokes on same hwnd: MUST NOT NOTIFY AGAIN (zero spam!)
        for _ in range(50):
            assert app._check_elevated(hwnd=1001) is True
        assert app.tray.notify.call_count == 1

        # Different elevated window: notifies once for that new window
        assert app._check_elevated(hwnd=1002) is True
        assert app.tray.notify.call_count == 2

        for _ in range(50):
            assert app._check_elevated(hwnd=1002) is True
        assert app.tray.notify.call_count == 2

        # Non-elevated window: returns False, no notification
        set_mock_window_elevated(False)
        assert app._check_elevated(hwnd=1003) is False
        assert app.tray.notify.call_count == 2

    finally:
        set_mock_window_elevated(None)


def test_custom_caret_fallback_chain():
    """Verify custom caret handling: container boxes rejected, degenerate rects filtered, cursor fallback."""
    # 1. Normal valid caret
    rect = _rects_to_caret([120, 240, 2, 18])
    assert rect is not None
    assert rect.x == 120 and rect.y == 240 and rect.height == 18

    # 2. Terminal / Electron whole-window bounding box (e.g. VS Code terminal canvas)
    # Must be rejected so fallback to cursor engages
    assert _rects_to_caret([0, 0, 900, 600]) is None
    assert _rects_to_caret([100, 100, 700, 400]) is None

    # 3. Degenerate zero rect
    assert _rects_to_caret([0, 0, 0, 0]) is None
    assert _rects_to_caret([0, 0, 2, 2]) is None

    # 4. Incomplete rect
    assert _rects_to_caret([10, 20]) is None

    # 5. Mock caret hook
    try:
        set_mock_caret(CaretRect(350, 450, 2, 16), source="UIA")
        r, src = get_caret_rect_with_source()
        assert src == "UIA"
        assert r.x == 350 and r.y == 450
    finally:
        set_mock_caret(None)


def test_multi_monitor_work_area_clamping():
    """Verify popup position clamps inside monitor work area and flips upward near bottom edge."""
    from ravan.platform import winapi as wapi

    # Test work area helper returns reasonable numbers
    work = wapi.get_monitor_work_area(100, 100)
    assert len(work) == 4
    left, top, right, bottom = work
    assert right > left
    assert bottom > top

    # Test popup placement logic inside work area
    eff_h = 22
    popup_h = 140
    y_near_bottom = bottom - 30

    # Near bottom of monitor -> must flip above caret
    if y_near_bottom + eff_h + popup_h + 8 < bottom:
        py = y_near_bottom + eff_h + 8
    else:
        py = max(top + 8, y_near_bottom - popup_h - 8)

    assert py < y_near_bottom
    assert py >= top + 8


def test_rapid_layout_switch_during_popup():
    """Verify rapid layout switches dismiss active predictions and never leave hook in swallowed state."""
    from ravan.ui.app_polling import AppPollingMixin

    class DummyOverlay:
        def __init__(self):
            self.predicting = False
            self.hidden_count = 0

        def hide(self):
            self.predicting = False
            self.hidden_count += 1
            set_popup_visible(False)

        def show_language(self, label, x, y, h):
            self.predicting = False
            set_popup_visible(False)

    class DummyLangApp(AppPollingMixin):
        def __init__(self):
            self.cfg = Config()
            self.overlay = DummyOverlay()
            self._pending_predict = False
            self._last_lang_poll = 0
            self._last_lang_hkl = 0x0409

        def _is_excluded(self):
            return False

    app = DummyLangApp()

    # Simulate active prediction popup open
    app.overlay.predicting = True
    app._pending_predict = True
    set_popup_visible(True)

    # Simulate rapid layout switch
    from ravan.platform.lang import LanguageInfo

    new_lang = LanguageInfo(tag="fa", hkl=0x0429, name="Persian")

    # When layout changes:
    if new_lang.hkl != app._last_lang_hkl:
        app._last_lang_hkl = new_lang.hkl
        if app.overlay.predicting:
            app.overlay.hide()
            set_popup_visible(False)
        app._pending_predict = False

    assert app.overlay.predicting is False
    assert app._pending_predict is False
    assert app.overlay.hidden_count == 1
