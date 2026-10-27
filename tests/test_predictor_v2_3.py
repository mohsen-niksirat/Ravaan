"""Tests for Version 2.3.0: Non-interfering overlay, auto-space, draggable custom position, and UI customization."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ravan.core.config import Config, config_from_dict, config_to_dict
from ravan.core.events import Candidate, CandidateKind
from ravan.ui.app import RavanApp
from ravan.ui.overlay import OverlayWindow

pytestmark = pytest.mark.windows


def test_config_prediction_v2_3_roundtrip() -> None:
    cfg = Config()
    assert cfg.prediction_auto_space is True
    assert cfg.overlay_custom_pos is False
    assert cfg.overlay_pos_x == -1
    assert cfg.overlay_pos_y == -1
    assert cfg.prediction_ui_style == "modern"
    assert cfg.prediction_font_size == 12
    assert cfg.prediction_opacity == 0.95

    # Serialize and deserialize with custom values
    cfg.prediction_auto_space = False
    cfg.overlay_custom_pos = True
    cfg.overlay_pos_x = 250
    cfg.overlay_pos_y = 400
    cfg.prediction_ui_style = "glass"
    cfg.prediction_font_size = 14
    cfg.prediction_opacity = 0.85

    d = config_to_dict(cfg)
    cfg2 = config_from_dict(d)

    assert cfg2.prediction_auto_space is False
    assert cfg2.overlay_custom_pos is True
    assert cfg2.overlay_pos_x == 250
    assert cfg2.overlay_pos_y == 400
    assert cfg2.prediction_ui_style == "glass"
    assert cfg2.prediction_font_size == 14
    assert pytest.approx(cfg2.prediction_opacity, 0.01) == 0.85


def test_prediction_auto_space_enabled_in_app() -> None:
    cfg = Config()
    cfg.prediction_auto_space = True
    overlay = MagicMock()
    with patch("ravan.ui.app.KeyboardHook"), patch("ravan.ui.app.replace_last_n_with") as mock_replace:
        app = RavanApp(cfg, overlay=overlay)
        try:
            # User typed "sal"
            app.journal.push("s")
            app.journal.push("a")
            app.journal.push("l")
            assert app.journal.last_word() == "sal"

            cand = Candidate(text="salam", score=100.0, kind=CandidateKind.COMPLETION)
            app._accept_candidate(cand)

            # Check that replace_last_n_with was called with "salam " (with trailing space)
            mock_replace.assert_called_once_with(3, "salam ", cursor_offset=None)
            # Check journal has "salam "
            assert app.journal.text() == "salam "
            assert overlay.hide.called
        finally:
            app.stop()


def test_prediction_auto_space_disabled_in_app() -> None:
    cfg = Config()
    cfg.prediction_auto_space = False
    overlay = MagicMock()
    with patch("ravan.ui.app.KeyboardHook"), patch("ravan.ui.app.replace_last_n_with") as mock_replace:
        app = RavanApp(cfg, overlay=overlay)
        try:
            app.journal.push("s")
            app.journal.push("a")
            app.journal.push("l")

            cand = Candidate(text="salam", score=100.0, kind=CandidateKind.COMPLETION)
            app._accept_candidate(cand)

            # Check that replace_last_n_with was called with "salam" (without trailing space)
            mock_replace.assert_called_once_with(3, "salam", cursor_offset=None)
            assert app.journal.text() == "salam"
        finally:
            app.stop()


def test_prediction_sentence_auto_space() -> None:
    cfg = Config()
    cfg.prediction_auto_space = True
    overlay = MagicMock()
    with patch("ravan.ui.app.KeyboardHook"), patch("ravan.ui.app.replace_last_n_with") as mock_replace:
        app = RavanApp(cfg, overlay=overlay)
        try:
            app.journal.push("h")
            cand = Candidate(text="hal shoma", score=90.0, kind=CandidateKind.SENTENCE)
            app._accept_candidate(cand)

            mock_replace.assert_called_once_with(1, "hal shoma ")
            assert app.journal.text() == "hal shoma "
        finally:
            app.stop()


def test_is_foreground_self_excludes_overlay() -> None:
    cfg = Config()
    overlay = MagicMock()
    overlay._get_root_hwnd.return_value = 98765
    with patch("ravan.ui.app.KeyboardHook"):
        app = RavanApp(cfg, overlay=overlay)
        try:
            with patch("ravan.platform.winapi.user32.GetForegroundWindow", return_value=98765):
                # When foreground window is overlay HWND, it should NOT be considered foreground self
                assert app._is_foreground_self() is False
        finally:
            app.stop()


def test_overlay_window_custom_position_and_reset() -> None:
    cfg = Config()
    cfg.overlay_custom_pos = True
    cfg.overlay_pos_x = 300
    cfg.overlay_pos_y = 500

    try:
        ov = OverlayWindow(cfg=cfg)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Tkinter display not available: {exc}")

    try:
        assert ov.has_custom_pos is True
        assert ov.custom_x == 300
        assert ov.custom_y == 500

        ov.reset_position_to_caret()
        assert ov.has_custom_pos is False
        assert ov.custom_x == -1
        assert ov.custom_y == -1
    finally:
        ov.destroy()


def test_overlay_window_ui_styles() -> None:
    for style in ("modern", "compact", "glass", "classic"):
        cfg = Config()
        cfg.prediction_ui_style = style
        cfg.prediction_font_size = 11
        try:
            ov = OverlayWindow(cfg=cfg)
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"Tkinter display not available: {exc}")

        try:
            assert ov.cfg.prediction_ui_style == style
        finally:
            ov.destroy()


def test_overlay_mouse_drag_and_callback() -> None:
    cfg = Config()
    moved_positions = []

    def on_moved(x: int, y: int) -> None:
        moved_positions.append((x, y))

    try:
        ov = OverlayWindow(cfg=cfg, on_position_changed=on_moved)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Tkinter display not available: {exc}")

    try:
        # Simulate mouse down
        event_down = MagicMock(x_root=100, y_root=100)
        ov._on_mouse_down(event_down, row_index=-1)
        assert ov._is_dragging is False

        # Simulate mouse drag by 50px
        event_drag = MagicMock(x_root=150, y_root=150)
        ov._on_mouse_drag(event_drag)
        assert ov._is_dragging is True

        # Simulate mouse up
        event_up = MagicMock(x_root=150, y_root=150)
        ov._on_mouse_up(event_up, row_index=-1)
        assert ov._is_dragging is False
        assert ov.has_custom_pos is True
        assert len(moved_positions) == 1
    finally:
        ov.destroy()
