"""Tests for Phase 7: Quick Accent / Persian Letter Picker (Target G)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ravan.core.accent import AccentEngine
from ravan.core.config import Config
from ravan.platform.focus import set_mock_fullscreen_focused
from ravan.ui.app import RavanApp


class DummyOverlay:
    def __init__(self) -> None:
        self.predicting = False
        self.clipboard_open = False
        self.visible = False
    def hide(self) -> None: pass
    def destroy(self) -> None: pass
    def tick(self) -> None: pass


def test_accent_variants_coverage():
    engine = AccentEngine()

    # Test Persian letter variants
    assert "ه" in engine.get_variants_for_char("h")
    assert "ة" in engine.get_variants_for_char("h")
    assert "ھ" in engine.get_variants_for_char("h")

    assert "ی" in engine.get_variants_for_char("y")
    assert "ي" in engine.get_variants_for_char("y")
    assert "ئ" in engine.get_variants_for_char("y")

    assert "ا" in engine.get_variants_for_char("a")
    assert "آ" in engine.get_variants_for_char("a")
    assert "أ" in engine.get_variants_for_char("a")

    # Space hold -> ZWNJ
    assert engine.get_variants_for_char(" ") == ["\u200c"]

    # Number hold -> Persian & Arabic digits
    assert engine.get_variants_for_char("5") == ["۵", "٥"]


def test_tap_vs_hold_detection():
    engine = AccentEngine(hold_ms=300)

    # 1. Tap (< 300ms hold)
    engine.on_key_down(ord("H"), "h", now=1.0)
    # Key down auto-repeat at 100ms
    v_early = engine.on_key_down(ord("H"), "h", now=1.1)
    assert v_early is None
    assert not engine.is_active

    # Key up at 150ms
    was_active, char = engine.on_key_up(ord("H"), now=1.15)
    assert not was_active
    assert char == "h"

    # 2. Hold (>= 300ms)
    engine.on_key_down(ord("H"), "h", now=2.0)
    v_hold = engine.on_key_down(ord("H"), "h", now=2.35)  # 350ms later
    assert v_hold is not None
    assert engine.is_active
    assert len(v_hold) >= 3

    # Key up after hold: bar must stay active for selection
    was_active, char = engine.on_key_up(ord("H"), now=2.4)
    assert was_active is True
    assert engine.is_active is True


def test_variant_selection_by_digit():
    engine = AccentEngine(hold_ms=300)
    engine.on_key_down(ord("H"), "h", now=1.0)
    engine.on_key_down(ord("H"), "h", now=1.35)
    assert engine.is_active

    # Select 2: 'ة'
    chosen = engine.select_digit(2)
    assert chosen == "ة"
    assert not engine.is_active


def test_variant_selection_by_arrows_and_enter():
    engine = AccentEngine(hold_ms=300)
    engine.on_key_down(ord("Y"), "y", now=1.0)
    engine.on_key_down(ord("Y"), "y", now=1.35)
    assert engine.is_active
    assert engine.selected_index == 0

    # Move right (+1)
    idx1 = engine.move_selection(1)
    assert idx1 == 1

    # Move right (+1)
    idx2 = engine.move_selection(1)
    assert idx2 == 2

    # Accept current selection
    chosen = engine.accept_current()
    assert chosen == "ئ"
    assert not engine.is_active


def test_escape_dismissal():
    engine = AccentEngine(hold_ms=300)
    engine.on_key_down(ord("A"), "a", now=1.0)
    engine.on_key_down(ord("A"), "a", now=1.35)
    assert engine.is_active

    engine.reset()
    assert not engine.is_active


def test_fullscreen_suppression_and_app_integration():
    cfg = Config()
    cfg.quick_accent_enabled = True
    cfg.quick_accent_hold_ms = 300

    with patch("ravan.ui.app.KeyboardHook"):
        app = RavanApp(cfg, overlay=DummyOverlay())
        try:
            assert app.accent is not None

            # 1. Fullscreen active -> accent suppressed
            set_mock_fullscreen_focused(True)
            try:
                event = MagicMock(vk_code=ord("H"), scan_code=0, flags=0)
                # First press
                app._handle_accent_key(event, ord("H"), "h")
                # Repeat past threshold
                handled = app._handle_accent_key(event, ord("H"), "h")
                assert not handled
                assert not app.accent.is_active
            finally:
                set_mock_fullscreen_focused(None)

            # 2. Normal window -> accent triggers
            event = MagicMock(vk_code=ord("H"), scan_code=0, flags=0)
            app.accent._press_time = 1.0
            app.accent._held_vk = ord("H")
            app.accent._held_char = "h"

            # Mock caret and bar
            with patch("ravan.ui.app_accent.get_caret_rect") as mock_caret:
                mock_caret.return_value = MagicMock(x=100, y=200, height=20)
                with patch.object(app.accent_bar, "show") as mock_show:
                    # Key down after 350ms
                    with patch("time.monotonic", return_value=1.35):
                        handled = app._handle_accent_key(event, ord("H"), "h")
                        assert handled is True
                        assert app.accent.is_active
                        assert mock_show.called
        finally:
            app.stop()
