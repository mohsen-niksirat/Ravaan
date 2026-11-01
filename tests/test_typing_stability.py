"""Tests verifying typing stability, caret position anchoring, and fast typing desync fixes."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from ravan.core.config import Config
from ravan.core.events import Candidate, CandidateKind
from ravan.platform import winapi as w
from ravan.platform.hook import HookEvent
from ravan.ui.app_actions import AppActionsMixin
from ravan.ui.app_polling import AppPollingMixin
from ravan.ui.key_handler import KeyHandlerMixin


class MockApp(AppActionsMixin, AppPollingMixin, KeyHandlerMixin):
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._current_exe = "notepad.exe"
        self._current_window_class = "Notepad"
        self._active_layout_tag = "fa"
        self._pending_predict = False
        self._last_key_time = 0.0
        self._suppress_until = 0.0
        self._last_convert_at = 0.0
        self._last_autofix_time = 0.0
        self._last_autocorrect = None
        self._own_pid = 1234
        self.journal = MagicMock()
        self.journal.last_word.return_value = ""
        self.journal.previous_context.return_value = ""
        self.overlay = MagicMock()
        self.overlay.visible = False
        self.overlay.predicting = False
        self.overlay.clipboard_open = False
        self.predictor = MagicMock()
        self.hook = MagicMock()
        self._ui_queue = MagicMock()
        self.is_paused = False

    def _record_event(self, *args, **kwargs):
        pass

    def _schedule_predict(self):
        self._pending_predict = True


def test_hardware_backspace_never_suppressed_by_synthetic_cooldown():
    """Verify that a user pressing Backspace is never discarded even when synthetic cooldown is active."""
    cfg = Config()
    app = MockApp(cfg)

    # Set synthetic suppression active for the next 2 seconds
    app._suppress_until = time.monotonic() + 2.0

    # Backspace event (hardware from user, no LLKHF_INJECTED)
    event_back = HookEvent(vk_code=w.VK_BACK, flags=0, scan_code=14, is_key_down=True)
    app.hook.poll.side_effect = [event_back, None]

    with patch.object(app, "_is_foreground_self", return_value=False):
        app._drain_hook_events()

    # Backspace MUST have been pushed to journal!
    app.journal.push.assert_called_with("\b")


def test_backspacing_to_empty_immediately_hides_visible_overlay():
    """When the user deletes all characters of the word, overlay must hide immediately without waiting for debounce."""
    cfg = Config()
    app = MockApp(cfg)
    app.overlay.visible = True
    app.overlay.predicting = True
    app.journal.last_word.return_value = ""  # empty after backspace

    event_back = HookEvent(vk_code=w.VK_BACK, flags=0, scan_code=14, is_key_down=True)
    app.hook.poll.side_effect = [event_back, None]

    with patch.object(app, "_is_foreground_self", return_value=False):
        app._drain_hook_events()

    app.overlay.hide.assert_called()


def test_overlay_position_stays_stable_during_consecutive_keystrokes():
    """OverlayWindow must not jump down and left with every keystroke when predicting a word."""
    from ravan.ui.overlay import OverlayWindow

    cfg = Config()
    cfg.overlay_custom_pos = False
    cfg.overlay_pos_x = -1
    cfg.overlay_pos_y = -1

    ov = OverlayWindow(cfg=cfg)
    try:
        cands = [
            Candidate(text="سلام", score=10.0, kind=CandidateKind.COMPLETION),
            Candidate(text="سیستم", score=8.0, kind=CandidateKind.COMPLETION),
        ]

        # First keystroke (e.g. typing 'س')
        ov.show_predictions(cands, x=500, y=300, height=20)
        first_x = ov.current_x
        first_y = ov.current_y
        assert first_x >= 0 and first_y >= 0

        # Second keystroke (e.g. typing 'ل' -> 'سل')
        # Overlay is already visible; coordinates should remain locked and stable!
        ov.show_predictions(cands, x=500, y=300, height=20)
        assert ov.current_x == first_x
        assert ov.current_y == first_y

        # Third keystroke (e.g. typing 'ا' -> 'سلا')
        ov.show_predictions(cands, x=500, y=300, height=20)
        assert ov.current_x == first_x
        assert ov.current_y == first_y

        # When hidden, coordinates reset
        ov.hide()
        assert ov.current_x == -1
        assert ov.current_y == -1
        assert ov._root.state() == "withdrawn"
    finally:
        ov.destroy()
