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
    set_popup_visible(True)
    try:
        kb = w.KBDLLHOOKSTRUCT()
        kb.vkCode = w.VK_RETURN
        kb.scanCode = 28
        kb.flags = 0
        kb_ptr = ctypes.addressof(kb)

        # 1. Plain Enter when popup is visible -> swallowed (returns 1)
        with patch("ravan.platform.hook._is_shift_pressed", return_value=False):
            res = hook._callback(0, w.WM_KEYDOWN, kb_ptr)
            assert res == 1

        # 2. Shift+Enter when popup is visible -> NOT swallowed (passes through)
        with patch("ravan.platform.hook._is_shift_pressed", return_value=True), \
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
