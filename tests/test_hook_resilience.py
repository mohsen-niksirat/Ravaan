"""Unit tests for keyboard hook resilience, auto-recovery watchdog, and clock jump handling."""

from __future__ import annotations

import queue
from unittest.mock import MagicMock, patch

import pytest

from ravan.platform.hook import HookEvent, KeyboardHook
from ravan.ui.app_polling import AppPollingMixin

pytestmark = pytest.mark.windows


def test_hook_is_alive_and_check_health():
    hook = KeyboardHook()
    assert hook.is_alive() is False
    assert hook.check_health() is False

    # Mock running state with active thread and hook handle
    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = True
    hook._thread = mock_thread
    hook._running = True
    hook._hook = 12345

    assert hook.is_alive() is True
    assert hook.check_health() is True

    # If thread unexpectedly dies while _running is True
    mock_thread.is_alive.return_value = False
    with patch.object(hook, "reinstall", return_value=True) as mock_reinstall:
        healthy = hook.check_health()
        assert healthy is True
        assert mock_reinstall.called


def test_hook_reinstall_lifecycle():
    hook = KeyboardHook()
    hook._thread_id = 111
    hook._running = True

    with patch("ravan.platform.winapi.user32.PostThreadMessageW"), \
         patch("ravan.platform.winapi.user32.UnhookWindowsHookEx"), \
         patch.object(hook, "start") as mock_start:
        hook.reinstall()
        assert mock_start.called


def test_hook_emit_queue_overflow_nonblocking():
    hook = KeyboardHook()
    # Fill queue to maximum capacity
    test_q: queue.Queue[HookEvent] = queue.Queue(maxsize=3)
    hook._queue = test_q

    e1 = HookEvent(vk_code=65, flags=0, scan_code=30, is_key_down=True)
    e2 = HookEvent(vk_code=66, flags=0, scan_code=31, is_key_down=True)
    e3 = HookEvent(vk_code=67, flags=0, scan_code=32, is_key_down=True)
    e4 = HookEvent(vk_code=68, flags=0, scan_code=33, is_key_down=True)

    hook._emit(e1)
    hook._emit(e2)
    hook._emit(e3)
    assert test_q.full()

    # Emitting e4 when full must NOT block, and must drop oldest (e1) so e4 is stored
    hook._emit(e4)
    assert test_q.full()

    remaining_vks = [test_q.get_nowait().vk_code for _ in range(3)]
    assert remaining_vks == [66, 67, 68]


def test_poll_hook_health_clock_jump_recovery():
    class DummyApp(AppPollingMixin):
        def __init__(self):
            self.journal = MagicMock()
            self._pending_predict = True
            self.overlay = MagicMock()
            self.overlay.predicting = True
            self.hook = MagicMock()
            self._last_watchdog_tick = 100.0

    app = DummyApp()
    # Simulate monotonic clock jump (e.g. 10 seconds elapsed due to sleep or lock screen)
    with patch("time.monotonic", return_value=110.0):
        app._poll_hook_health()
        assert app.journal.clear.called
        assert app._pending_predict is False
        assert app.overlay.hide.called
        assert app.hook.check_health.called
