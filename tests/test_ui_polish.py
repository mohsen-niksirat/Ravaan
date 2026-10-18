"""Tests for Phase 3 UX polish: Theme tokens, FirstRunWizard, Tray Quick Toggles, and Overlay."""

from __future__ import annotations

import tkinter as tk
from unittest.mock import MagicMock

import pytest

from ravan.core.config import Config
from ravan.core.events import Candidate, CandidateKind
from ravan.ui.overlay import OverlayWindow
from ravan.ui.stats_popup import StatsPopupWindow
from ravan.ui.theme import (
    confidence_bar,
    get_active_palette,
    get_ui_font,
)
from ravan.ui.tray import TrayIcon, _make_icon_image
from ravan.ui.wizard import FirstRunWizard


def test_palette_modes() -> None:
    dark = get_active_palette("dark")
    assert dark.name == "dark"
    assert dark.bg == "#202124"
    assert dark.alpha == 0.95

    light = get_active_palette("light")
    assert light.name == "light"
    assert light.bg == "#ffffff"

    hc = get_active_palette("high_contrast")
    assert hc.name == "high_contrast"
    assert hc.bg == "#000000"
    assert hc.fg == "#ffffff"
    assert hc.alpha == 1.0


def test_confidence_bar_meter() -> None:
    assert confidence_bar(0.0) == " "
    assert confidence_bar(0.3) == "▂"
    assert confidence_bar(0.6) == "▅"
    assert confidence_bar(1.0) == "█"
    assert confidence_bar(1.5) == "█"
    assert confidence_bar(-0.5) == " "


def test_get_ui_font() -> None:
    f_en = get_ui_font(size=11, bold=False, rtl=False)
    assert f_en == ("Segoe UI", 11, "normal")

    f_fa = get_ui_font(size=12, bold=True, rtl=True)
    assert f_fa == ("Vazirmatn", 12, "bold")


def test_overlay_theme_and_confidence() -> None:
    try:
        ov = OverlayWindow()
    except tk.TclError:
        pytest.skip("Tkinter display not available in this environment")

    try:
        ov.set_theme_mode("high_contrast")
        assert ov.palette.name == "high_contrast"
        assert ov.theme.name == "high_contrast"

        c1 = Candidate(text="سلام", score=0.9, kind=CandidateKind.COMPLETION)
        c2 = Candidate(text="سرد", score=0.4, kind=CandidateKind.COMPLETION)
        ov._candidates = [c1, c2]
        ov._mode = "predict"
        ov._selected = 0
        ov._render_candidates()

        row0_text = ov._row_text(0, c1, True)
        assert "▶ 1  سلام" in row0_text
        assert "█" in row0_text

        # Test selection movement
        ov.move_selection(1)
        assert ov._selected == 1
    finally:
        ov.destroy()


def test_first_run_wizard_lifecycle(tmp_path) -> None:
    cfg = Config()
    cfg.has_seen_onboarding = False

    called = False

    def on_done():
        nonlocal called
        called = True

    wiz = FirstRunWizard(cfg=cfg, on_complete=on_done)
    assert not wiz.open

    wiz.show()
    assert wiz.open

    # Simulate completion
    wiz._close(completed=True)
    assert not wiz.open
    assert cfg.has_seen_onboarding is True
    assert called is True


def test_first_run_wizard_skip(tmp_path) -> None:
    cfg = Config()
    cfg.has_seen_onboarding = False

    wiz = FirstRunWizard(cfg=cfg)
    wiz.show()
    wiz._close(completed=False)
    assert not wiz.open
    assert cfg.has_seen_onboarding is True


def test_tray_icon_images() -> None:
    img_normal = _make_icon_image(dimmed=False, paused=False)
    assert img_normal is not None
    assert img_normal.size == (64, 64)

    img_dimmed = _make_icon_image(dimmed=True, paused=False)
    assert img_dimmed is not None
    assert img_dimmed.size == (64, 64)

    img_paused = _make_icon_image(dimmed=False, paused=True)
    assert img_paused is not None
    assert img_paused.size == (64, 64)


def test_tray_quick_toggles_and_pause() -> None:
    on_quit = MagicMock()
    on_toggle_pred = MagicMock()
    on_toggle_auto = MagicMock()
    on_toggle_zwnj = MagicMock()
    on_toggle_pause = MagicMock()

    tray = TrayIcon(
        on_quit=on_quit,
        on_toggle_prediction=on_toggle_pred,
        is_prediction_enabled=lambda: True,
        on_toggle_autocorrect=on_toggle_auto,
        is_autocorrect_enabled=lambda: False,
        on_toggle_auto_zwnj=on_toggle_zwnj,
        is_auto_zwnj_enabled=lambda: True,
        on_toggle_pause=on_toggle_pause,
        is_paused=lambda: False,
    )

    tray._toggle_prediction()
    on_toggle_pred.assert_called_once_with(False)

    tray._toggle_autocorrect()
    on_toggle_auto.assert_called_once_with(True)

    tray._toggle_auto_zwnj()
    on_toggle_zwnj.assert_called_once_with(False)

    tray._toggle_pause_action()
    on_toggle_pause.assert_called_once()

    tray.set_paused(True, 10)
    tray.set_paused(False)


def test_stats_popup_window() -> None:
    try:
        popup = StatsPopupWindow()
        stats = {
            "word_count": 42,
            "char_count": 195,
            "char_no_spaces": 160,
            "reading_time_sec": 12,
            "ratio_str": "90% FA / 10% EN",
        }
        popup.show(stats, x=200, y=200)
        assert popup._root is not None
        popup.close()
        assert popup._root is None
    except tk.TclError:
        pytest.skip("Tkinter display not available")
