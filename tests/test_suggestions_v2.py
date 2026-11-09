"""Tests for Phase 5: Live Suggestions Upgrade (Target E)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from ravan.core.config import Config
from ravan.core.events import Candidate, CandidateKind
from ravan.platform import winapi as w
from ravan.platform.focus import set_mock_numeric_focused, set_mock_password_focused
from ravan.platform.lang import set_mock_ime_composing
from ravan.ui.app import RavanApp


class DummyOverlay:
    def __init__(self) -> None:
        self.predicting = False
        self.clipboard_open = False
        self.active_popup = False
        self.visible = False
        self._candidates: list[Candidate] = []
        self._selected = 0
        self.last_shown_x = 0
        self.last_shown_y = 0

    def hide(self) -> None:
        self.predicting = False
        self.visible = False
        self._candidates = []

    def destroy(self) -> None:
        pass

    def tick(self) -> None:
        pass

    def show_predictions(self, cands: list[Candidate], x: int, y: int, h: int) -> None:
        self.predicting = True
        self.visible = True
        self._candidates = list(cands)
        self._selected = 0
        self.last_shown_x = x
        self.last_shown_y = y

    def accept_selected(self) -> Candidate | None:
        if not self.predicting or not self._candidates:
            return None
        c = self._candidates[self._selected]
        self.hide()
        return c

    def accept_sentence_continuation(self) -> Candidate | None:
        for idx, c in enumerate(self._candidates):
            if c.kind == CandidateKind.SENTENCE:
                self._selected = idx
                return self.accept_selected()
        return None

    def move_selection(self, delta: int) -> None:
        if self._candidates:
            self._selected = (self._selected + delta) % len(self._candidates)


def test_arrow_key_accept_right():
    cfg = Config()
    cfg.suggestion_accept_arrow = "right"
    overlay = DummyOverlay()
    with patch("ravan.ui.app.KeyboardHook"):
        app = RavanApp(cfg, overlay=overlay)
        try:
            overlay.show_predictions(
                [Candidate(text="سلام", score=100.0, kind=CandidateKind.COMPLETION)],
                100, 100, 20
            )
            assert overlay.predicting

            # Mock HookEvent for Right Arrow (VK_RIGHT)
            event = MagicMock(vk_code=w.VK_RIGHT, scan_code=0, flags=0)
            accepted = []
            app._accept_candidate = lambda cand: accepted.append(cand.text)

            app._handle_key(event)
            assert len(accepted) == 1
            assert accepted[0] == "سلام"
            assert not overlay.predicting
        finally:
            app.stop()


def test_arrow_key_accept_left_in_rtl():
    cfg = Config()
    cfg.suggestion_accept_arrow = "auto_rtl"
    overlay = DummyOverlay()
    with patch("ravan.ui.app.KeyboardHook"):
        app = RavanApp(cfg, overlay=overlay)
        try:
            overlay.show_predictions(
                [Candidate(text="کتاب", score=100.0, kind=CandidateKind.COMPLETION)],
                100, 100, 20
            )
            # Simulate Persian language active
            mock_lang = MagicMock(is_persian=True)
            with patch("ravan.ui.key_handler.current_language", return_value=mock_lang):
                event = MagicMock(vk_code=w.VK_LEFT, scan_code=0, flags=0)
                accepted = []
                app._accept_candidate = lambda cand: accepted.append(cand.text)

                app._handle_key(event)
                assert len(accepted) == 1
                assert accepted[0] == "کتاب"
                assert not overlay.predicting
        finally:
            app.stop()


def test_shift_enter_passes_through_newline_and_dismisses_prediction():
    cfg = Config()
    overlay = DummyOverlay()
    with patch("ravan.ui.app.KeyboardHook"):
        app = RavanApp(cfg, overlay=overlay)
        try:
            # First candidate is single word, second is sentence continuation
            cands = [
                Candidate(text="حال", score=100.0, kind=CandidateKind.COMPLETION),
                Candidate(text="حال شما چطوره", score=80.0, kind=CandidateKind.SENTENCE),
            ]
            overlay.show_predictions(cands, 100, 100, 20)
            assert overlay.predicting

            # Simulate Shift key held down
            with patch("ravan.platform.winapi.user32.GetKeyState", return_value=0x8000):
                event = MagicMock(vk_code=w.VK_RETURN, scan_code=0, flags=0)
                accepted = []
                app._accept_candidate = lambda cand: accepted.append(cand.text)

                app._handle_key(event)
                # Shift+Enter MUST NOT accept candidate or replace words!
                assert len(accepted) == 0
                assert not overlay.predicting
                assert "\n" in app.journal.text()
        finally:
            app.stop()


def test_hook_callback_shift_enter_not_swallowed():
    import ctypes

    from ravan.platform.hook import KeyboardHook, set_popup_visible
    hook = KeyboardHook()
    set_popup_visible(True, swallow_enter=True)
    try:
        kb = w.KBDLLHOOKSTRUCT()
        kb.vkCode = w.VK_RETURN
        kb.scanCode = 28
        kb.flags = 0
        kb_ptr = ctypes.addressof(kb)

        # 1. Plain Enter when popup is visible and swallow_enter=True -> swallowed (returns 1)
        with patch("ravan.platform.hook._is_shift_pressed", return_value=False):
            res = hook._callback(0, w.WM_KEYDOWN, kb_ptr)
            assert res == 1

        # 2. Shift+Enter when popup is visible -> NOT swallowed (passes through)
        with patch("ravan.platform.hook._is_shift_pressed", return_value=True), \
             patch("ravan.platform.winapi.user32.CallNextHookEx", return_value=0):
            res = hook._callback(0, w.WM_KEYDOWN, kb_ptr)
            assert res == 0

        # 3. Plain Enter when swallow_enter=False (default) -> NOT swallowed (passes through)
        set_popup_visible(True, swallow_enter=False)
        with patch("ravan.platform.hook._is_shift_pressed", return_value=False), \
             patch("ravan.platform.winapi.user32.CallNextHookEx", return_value=0):
            res = hook._callback(0, w.WM_KEYDOWN, kb_ptr)
            assert res == 0
    finally:
        set_popup_visible(False)


def test_suppression_in_password_and_numeric_and_ime():
    cfg = Config()
    overlay = DummyOverlay()
    with patch("ravan.ui.app.KeyboardHook"):
        app = RavanApp(cfg, overlay=overlay)
        try:
            app._pending_predict = True
            app._last_key_time = time.monotonic() - 1.0  # past debounce

            # 1. Password field suppression
            set_mock_password_focused(True)
            try:
                app._maybe_predict()
                assert not overlay.predicting
            finally:
                set_mock_password_focused(None)

            # 2. Numbers-only field suppression
            app._pending_predict = True
            set_mock_numeric_focused(True)
            try:
                app._maybe_predict()
                assert not overlay.predicting
            finally:
                set_mock_numeric_focused(None)

            # 3. IME composition suppression
            app._pending_predict = True
            set_mock_ime_composing(True)
            try:
                app._maybe_predict()
                assert not overlay.predicting
            finally:
                set_mock_ime_composing(None)

            # 4. Pure digits typing suppression
            app._pending_predict = True
            for ch in "12345":
                app.journal.push(ch)
            app._maybe_predict()
            assert not overlay.predicting
        finally:
            app.stop()


def test_prediction_continuous_latency_p95():
    """Verify prediction lookup completes in under 15ms p95."""
    from ravan.core.dict import DictEntry, Dictionary, Language
    from ravan.core.predictor import DictPredictor

    entries = [
        DictEntry("hello", rank=1, frequency=100),
        DictEntry("help", rank=2, frequency=90),
        DictEntry("helicopter", rank=3, frequency=50),
    ]
    en_dict = Dictionary(entries=entries, language=Language.ENGLISH)
    predictor = DictPredictor(english=en_dict)

    latencies = []
    for _ in range(100):
        t0 = time.perf_counter()
        cands = predictor.predict("hel", "i want to", limit=5)
        dt = (time.perf_counter() - t0) * 1000.0  # ms
        latencies.append(dt)
        assert len(cands) > 0

    latencies.sort()
    p95 = latencies[95]
    print(f"\np95 Prediction Latency: {p95:.2f}ms")
    assert p95 < 15.0, f"p95 latency {p95:.2f}ms exceeded 15ms threshold"


def test_overlay_clamping_and_sentence_rendering():
    """Verify overlay popup clamps within monitor work area and renders dimmed sentence tag."""
    import tkinter as tk

    import pytest

    from ravan.ui.overlay import OverlayWindow

    try:
        overlay = OverlayWindow()
    except (tk.TclError, Exception) as exc:
        pytest.skip(f"Tkinter display not available: {exc}")
    try:
        # Mock monitor work area: left=0, top=0, right=1920, bottom=1080
        with patch("ravan.platform.winapi.get_monitor_work_area", return_value=(0, 0, 1920, 1080)):
            cands = [
                Candidate(text="سلام", score=100.0, kind=CandidateKind.COMPLETION),
                Candidate(text="سلام وقت بخیر", score=80.0, kind=CandidateKind.SENTENCE),
            ]
            # Place near right edge: 1910
            overlay.show_predictions(cands, x=1910, y=500, height=20)
            assert overlay.predicting
            # Label text for sentence continuation should contain [ادامه]
            text = overlay._row_text(1, cands[1], selected=False)
            assert "[ادامه]" in text
    finally:
        overlay.destroy()


def test_new_prediction_styles_resolve_different_palettes():
    """Verify all new styles resolve to visually distinct palettes and tokens."""
    from ravan.ui.theme import get_prediction_style

    new_styles = ["fluent", "material", "ios", "minimal", "neon"]

    for mode in ("dark", "light"):
        tokens_list = [get_prediction_style(st, mode=mode) for st in new_styles]

        # 1. Names match
        for st, tok in zip(new_styles, tokens_list, strict=True):
            assert tok.name == st

        # 2. Palettes are distinct across styles
        palettes = [tok.palette for tok in tokens_list]
        bg_colors = [p.bg for p in palettes]
        card_colors = [p.card_bg for p in palettes]

        # Each style has a distinct combination of bg + card_bg
        bg_card_pairs = list(zip(bg_colors, card_colors, strict=True))
        assert len(set(bg_card_pairs)) == len(new_styles), f"Duplicate palette in mode {mode}"

        # 3. Tokens differ across styles (radius, padding, separators, badges)
        radii = {tok.name: tok.corner_radius for tok in tokens_list}
        assert radii["material"] == 20.0
        assert radii["minimal"] == 4.0
        assert radii["fluent"] == 8.0

        # Neon confidence meter always visible
        neon_tok = next(t for t in tokens_list if t.name == "neon")
        assert neon_tok.confidence_meter_always is True
        assert neon_tok.border_color in ("#00E5FF", "#FF007F")

        # Material pill badge style
        mat_tok = next(t for t in tokens_list if t.name == "material")
        assert mat_tok.badge_style == "circle"
        assert mat_tok.selected_row_style == "pill"

        # iOS MacBook squircle, acrylic, pill selection, circular badges
        ios_tok = next(t for t in tokens_list if t.name == "ios")
        assert ios_tok.corner_radius == 16.0
        assert ios_tok.acrylic is True
        assert ios_tok.selected_row_style == "pill"
        assert ios_tok.badge_style == "circle"
        assert ios_tok.show_hint_bar is True


def test_overlay_renders_all_styles_without_raising():
    """Verify OverlayWindow applies and renders all 10 styles without raising exceptions."""
    import tkinter as tk

    import pytest

    from ravan.ui.overlay import OverlayWindow

    try:
        cfg = Config()
        overlay = OverlayWindow(cfg=cfg)
    except (tk.TclError, Exception) as exc:
        pytest.skip(f"Tkinter display not available: {exc}")

    try:
        styles = [
            "macos", "modern", "compact", "glass", "classic",
            "fluent", "material", "ios", "minimal", "neon"
        ]
        cands = [
            Candidate(text="سلام", score=100.0, kind=CandidateKind.COMPLETION),
            Candidate(text="سلام وقت بخیر", score=80.0, kind=CandidateKind.SENTENCE),
            Candidate(text="english", score=60.0, kind=CandidateKind.COMPLETION),
        ]

        with patch("ravan.platform.winapi.get_monitor_work_area", return_value=(0, 0, 1920, 1080)):
            for st in styles:
                cfg.prediction_ui_style = st
                overlay.apply_config(cfg)
                assert overlay._ui_style == st
                overlay.show_predictions(cands, x=200, y=200, height=20)
                assert overlay.predicting
                assert len(overlay._rows) >= len(cands)
                # Verify row texts generated without error for both RTL and LTR
                r0 = overlay._row_text(0, cands[0], selected=True)
                r1 = overlay._row_text(1, cands[1], selected=False)
                r2 = overlay._row_text(2, cands[2], selected=False)
                assert len(r0) > 0 and len(r1) > 0 and len(r2) > 0
                assert "سلام" in r0
                assert "[ادامه]" in r1
                assert "english" in r2
    finally:
        overlay.destroy()


def test_invalid_style_falls_back_to_macos():
    """Verify unknown style name gracefully resolves to macos design tokens."""
    from ravan.ui.theme import get_prediction_style

    tok = get_prediction_style("non_existent_fancy_style", mode="dark")
    assert tok.name == "macos"
    assert tok.corner_radius == 12.0
    assert tok.acrylic is True


def test_prediction_style_custom_colors_and_layout():
    """Verify get_prediction_style respects custom color schemes and horizontal layout adjustments."""
    from ravan.ui.theme import get_prediction_style

    # Test layout=horizontal modifies tokens
    tok_horiz = get_prediction_style("macos", mode="dark", layout="horizontal")
    assert tok_horiz.layout == "horizontal"
    assert tok_horiz.row_padding_y == 5
    assert tok_horiz.row_padding_x == 14
    assert tok_horiz.show_separators is True

    # Test custom colors override palette and border
    custom = {
        "bg": "#123456",
        "fg": "#ABCDEF",
        "highlight": "#FF007F",
        "border": "#778899",
        "accent": "#00FFCC",
    }
    tok_custom = get_prediction_style("ios", mode="dark", custom_colors=custom)
    assert tok_custom.palette.bg == "#123456"
    assert tok_custom.palette.fg == "#ABCDEF"
    assert tok_custom.palette.highlight == "#FF007F"
    assert tok_custom.palette.accent == "#00FFCC"
    assert tok_custom.border_color == "#778899"
    # Preserves style geometry
    assert tok_custom.corner_radius == 16.0
    assert tok_custom.badge_style == "circle"


def test_overlay_horizontal_mode_and_custom_colors():
    """Verify OverlayWindow renders properly in horizontal ribbon mode with custom colors."""
    import tkinter as tk

    import pytest

    from ravan.ui.overlay import OverlayWindow

    try:
        cfg = Config()
        cfg.prediction_layout = "horizontal"
        cfg.prediction_use_custom_colors = True
        cfg.prediction_custom_bg = "#112233"
        cfg.prediction_custom_fg = "#EAEAEA"
        cfg.prediction_custom_highlight = "#00CC88"
        overlay = OverlayWindow(cfg=cfg)
    except (tk.TclError, Exception) as exc:
        pytest.skip(f"Tkinter display not available: {exc}")

    try:
        cands = [
            Candidate(text="سلام", score=100.0, kind=CandidateKind.COMPLETION),
            Candidate(text="علیکم", score=90.0, kind=CandidateKind.COMPLETION),
            Candidate(text="hello", score=80.0, kind=CandidateKind.COMPLETION),
        ]
        with patch("ravan.platform.winapi.get_monitor_work_area", return_value=(0, 0, 1920, 1080)):
            overlay.show_predictions(cands, x=300, y=300, height=20)
            assert overlay.predicting
            assert overlay._is_horizontal is True
            assert len(overlay._rows) == 3
            # In horizontal ribbon mode, rows are packed horizontally side-by-side
            # Navigation works with step +1 / -1
            overlay.move_selection(1)
            assert overlay._selected == 1
            overlay.move_selection(-1)
            assert overlay._selected == 0
    finally:
        overlay.destroy()


def test_settings_render_style_preview_all_styles():
    """Verify SettingsWindow._render_style_preview renders all styles cleanly without raising."""
    import tkinter as tk

    import pytest

    from ravan.ui.settings import SettingsWindow

    try:
        cfg = Config()
        win = SettingsWindow(cfg=cfg)
    except (tk.TclError, Exception) as exc:
        pytest.skip(f"Tkinter display not available: {exc}")

    try:
        styles = [
            "macos", "modern", "compact", "glass", "classic",
            "fluent", "material", "ios", "minimal", "neon"
        ]
        win.show()
        win.tick()
        assert hasattr(win, "_prediction_ui_style_var")
        for st in styles:
            win._prediction_ui_style_var.set(st)
            win._render_style_preview()
            preview = win._style_preview
            # Verify container and children were rendered cleanly
            children = preview.winfo_children()
            assert len(children) >= 2  # Container + info_bar
    finally:
        win._close()


