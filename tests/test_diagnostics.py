"""Unit tests for Phase 3 diagnostics, structured logging, and caret tracking."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from unittest.mock import MagicMock, patch

from ravan.ui.app import RavanApp, setup_logging


def test_setup_logging_rotating_handler():
    setup_logging()
    root = logging.getLogger()
    rotating_handlers = [
        h for h in root.handlers if isinstance(h, RotatingFileHandler)
    ]
    assert len(rotating_handlers) == 1
    h = rotating_handlers[0]
    assert h.maxBytes == 2 * 1024 * 1024
    assert h.backupCount == 3


def test_app_event_ring_buffer_cap():
    app = RavanApp(overlay=MagicMock())
    for i in range(70):
        app._record_event(f"Action {i}", vk=0x41 + (i % 26), char=chr(65 + (i % 26)))

    assert len(app.recent_events) == 50
    # Oldest (0..19) should have been dropped; first entry is Action 20
    assert app.recent_events[0]["action"] == "Action 20"
    assert app.recent_events[-1]["action"] == "Action 69"


def test_diagnostics_snapshot_structure():
    app = RavanApp(overlay=MagicMock())
    app._record_event("Test diagnostic event", vk=0x7B, char="")
    snap = app._get_diagnostics_snapshot()

    assert "version" in snap
    assert "hook_active" in snap
    assert "foreground_exe" in snap
    assert "foreground_pid" in snap
    assert "window_title" in snap
    assert "is_excluded" in snap
    assert "layout" in snap
    assert "caret_source" in snap
    assert "caret_pos" in snap
    assert "recent_events" in snap
    assert len(snap["recent_events"]) >= 1
    assert snap["recent_events"][-1]["action"] == "Test diagnostic event"


def test_caret_source_tracking():
    from ravan.platform import caret

    with patch.object(
        caret, "_try_uia_caret", return_value=caret.CaretRect(10, 20, 2, 16)
    ):
        rect, source = caret.get_caret_rect_with_source()
        assert source == "UIA"
        assert rect.x == 10
        assert caret.get_last_caret_source() == "UIA"

    with patch.object(caret, "_try_uia_caret", return_value=None), patch.object(
        caret, "_try_gui_thread_info", return_value=caret.CaretRect(30, 40, 2, 16)
    ):
        rect, source = caret.get_caret_rect_with_source()
        assert source == "GetGUIThreadInfo"
        assert rect.x == 30
        assert caret.get_last_caret_source() == "GetGUIThreadInfo"
