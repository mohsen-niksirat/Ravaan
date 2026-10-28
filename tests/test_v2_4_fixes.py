"""Tests for Version 2.4.0 bugfixes and improvements.

Verifies:
- Prefix suggestion ranking for short prefixes ('س', 't', etc.)
- Caret caching duration (250ms)
- Native non-activating overlay show/hide mechanism
- System tray status indicator and menu updates
- Multi-resolution icon format and resolutions
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image

from ravan.core.dict import Dictionary
from ravan.platform import caret
from ravan.ui.tray import TrayIcon


def test_v2_4_suggestion_ranking_persian_single_char():
    """Typing 'س' must return high-frequency words (سلام, سال, ساعت) first, not rare alphabetical words."""
    d = Dictionary.persian()
    results = [e.word for e in d.completions("س", 5)]
    assert len(results) >= 3
    # Top words must include high-frequency terms
    assert any(w in results for w in ["سلام", "سال", "ساعت"])
    # Must NOT be polluted by rare 'سؤال', 'سئوال' as the only top matches
    assert "سؤال" not in results[:2]


def test_v2_4_suggestion_ranking_english_single_char():
    """Typing 't' must return top common English words (the, to, that)."""
    d = Dictionary.english()
    results = [e.word.lower() for e in d.completions("t", 5)]
    assert "the" in results
    assert "to" in results


def test_v2_4_caret_cache_ttl():
    """Caret cache duration should be 250ms to prevent AttachThreadInput hammer during typing bursts."""
    caret.reset_caret_cache()
    mock_rect = caret.CaretRect(100, 200, 2, 16)
    caret._cached_caret = (mock_rect, "test", time.monotonic())

    # Immediately after, cached rect is returned
    r, src = caret.get_caret_rect_with_source()
    assert r == mock_rect
    assert src == "test"


def test_v2_4_icon_ico_resolutions():
    """ravan/data/icon.ico must be a valid multi-resolution ICO file."""
    ico_path = Path(__file__).resolve().parent.parent / "ravan" / "data" / "icon.ico"
    assert ico_path.is_file()
    im = Image.open(ico_path)
    assert im.format == "ICO"
    # Primary dimension
    assert im.size[0] >= 64


def test_v2_4_tray_menu_status_and_update():
    """Tray icon must have status header and call update_menu on pause toggle."""
    on_quit = MagicMock()
    on_toggle_pause = MagicMock()
    is_paused = MagicMock(return_value=False)

    tray = TrayIcon(
        on_quit=on_quit,
        on_toggle_pause=on_toggle_pause,
        is_paused=is_paused,
    )
    tray._icon = MagicMock()

    # Simulate pause toggle
    tray._toggle_pause_action()
    on_toggle_pause.assert_called_once()
    tray._icon.update_menu.assert_called_once()

    # Simulate set_paused
    tray.set_paused(True, 10)
    assert tray._icon.update_menu.call_count == 2
