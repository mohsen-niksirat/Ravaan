"""Tests for smart prediction triggers: post-accept next-word, paste suppression, and numeric suppression."""

from __future__ import annotations

import ctypes
from unittest.mock import MagicMock, patch

from ravan.core.config import Config
from ravan.core.events import Candidate, CandidateKind
from ravan.core.learning import UserLearningEngine
from ravan.core.normalizer import is_numeric_or_symbol_token, is_valid_prediction_context_word
from ravan.core.predictor import DictPredictor
from ravan.platform import winapi as w
from ravan.platform.caret import CaretRect
from ravan.platform.hook import HookEvent, KeyboardHook, set_popup_visible
from ravan.ui.app import RavanApp


class _RecordingOverlay:
    def __init__(self) -> None:
        self.visible = False
        self.predicting = False
        self.clipboard_open = False
        self.has_custom_pos = False
        self.custom_x = -1
        self.custom_y = -1
        self._candidates: list[Candidate] = []
        self._selected = 0
        self._on_accept = None
        self.show_calls: list[list[Candidate]] = []
        self.hide_count = 0

    def hide(self) -> None:
        self.visible = False
        self.predicting = False
        self._candidates = []
        self._selected = 0
        self.hide_count += 1

    def show_predictions(self, candidates, x, y, height=16, on_accept=None) -> None:
        self._candidates = list(candidates)
        self._selected = 0
        self._on_accept = on_accept
        self.visible = bool(self._candidates)
        self.predicting = bool(self._candidates)
        self.show_calls.append(list(self._candidates))

    def accept_index(self, idx: int) -> Candidate | None:
        if not self.predicting or not (0 <= idx < len(self._candidates)):
            return None
        cand = self._candidates[idx]
        self.hide()
        return cand

    def accept_selected(self) -> Candidate | None:
        return self.accept_index(self._selected)

    def contains_screen_point(self, x: int, y: int) -> bool:
        return False

    def destroy(self) -> None:
        pass

    def tick(self) -> None:
        pass


def _make_app(cfg: Config | None = None) -> tuple[RavanApp, _RecordingOverlay]:
    c = cfg or Config()
    c.prediction_debounce_ms = 0
    c.prediction_enabled = True
    c.next_word_prediction = True
    c.prediction_auto_space = True
    c.quickpick_digits = True
    ov = _RecordingOverlay()
    with patch("ravan.ui.app.KeyboardHook"):
        app = RavanApp(c, overlay=ov)
    app.predictor = DictPredictor(
        english=None,
        persian=None,
        learning_engine=UserLearningEngine(auto_load=False),
        ignored_words=c.ignored_words,
    )
    return app, ov


def test_accept_candidate_via_quickpick_schedules_next_word_prediction() -> None:
    app, ov = _make_app()
    try:
        app.journal.push("س")
        app.journal.push("ل")
        ov.show_predictions(
            [Candidate(text="سلام", score=100.0, kind=CandidateKind.COMPLETION)],
            100,
            200,
            16,
            on_accept=app._accept_candidate,
        )

        ev_pick_1 = HookEvent(
            vk_code=ord("1"),
            flags=0,
            scan_code=2,
            is_key_down=True,
            modifiers=frozenset(),
        )
        with (
            patch("ravan.ui.app.replace_last_n_with") as mock_replace,
            patch("ravan.platform.focus.is_password_focused", return_value=False),
            patch("ravan.platform.focus.is_numeric_focused", return_value=False),
            patch("ravan.platform.lang.is_ime_composing", return_value=False),
            patch("ravan.ui.app_polling.get_caret_rect", return_value=CaretRect(130, 200, 2, 16)),
        ):
            app._handle_key(ev_pick_1)
            mock_replace.assert_called_once_with(2, "سلام ", cursor_offset=None)
            assert app.journal.text() == "سلام "
            assert app._pending_predict is True
            assert app._last_key_was_backspace is False

            app._maybe_predict()
            assert ov.predicting is True
            assert len(ov.show_calls) == 2
            next_texts = [c.text for c in ov._candidates]
            assert any(w_fa in next_texts for w_fa in ("عزیز", "علیکم", "وقتتون"))
            assert all(c.kind == CandidateKind.NEXT_WORD for c in ov._candidates)

            # Chain picking next-word candidate #1 ("عزیز" / first suggestion)
            first_next = ov._candidates[0].text
            app._handle_key(ev_pick_1)
            assert app.journal.text() == f"سلام {first_next} "
            assert app._pending_predict is True
    finally:
        app.stop()


def test_accept_candidate_after_backspace_and_auto_space_guards() -> None:
    app, ov = _make_app()
    try:
        app._last_key_was_backspace = True
        app._edited_since_popup = True
        app.journal.push("س")
        app.journal.push("ل")
        cand = Candidate(text="سلام", score=100.0, kind=CandidateKind.COMPLETION)

        with (
            patch("ravan.ui.app.replace_last_n_with"),
            patch("ravan.platform.focus.is_password_focused", return_value=False),
            patch("ravan.platform.focus.is_numeric_focused", return_value=False),
            patch("ravan.platform.lang.is_ime_composing", return_value=False),
            patch("ravan.ui.app_polling.get_caret_rect", return_value=CaretRect(130, 200, 2, 16)),
        ):
            app._accept_candidate(cand)
            assert app._last_key_was_backspace is False
            assert app._pending_predict is True
            app._maybe_predict()
            assert ov.predicting is True

            # Auto-space disabled: accepting should not schedule next-word prediction
            ov.hide()
            app.cfg.prediction_auto_space = False
            app._pending_predict = False
            app._accept_candidate(cand)
            assert app._pending_predict is False
    finally:
        app.stop()


def test_fast_ctrl_v_and_ctrl_c_modifier_snapshot_beats_release_race() -> None:
    app, ov = _make_app()
    try:
        app.journal.push("ت")
        ov.show_predictions(
            [Candidate(text="تست", score=10.0, kind=CandidateKind.COMPLETION)],
            10,
            20,
        )

        # Simulate Ctrl already released by the time main loop drains GetAsyncKeyState,
        # while HookEvent captured modifiers={"ctrl"} synchronously at keystroke instant.
        ev_ctrl_v = HookEvent(
            vk_code=ord("V"),
            flags=0,
            scan_code=0x2F,
            is_key_down=True,
            modifiers=frozenset({"ctrl"}),
        )
        with (
            patch("ravan.platform.keys.modifiers_down", return_value=False),
            patch("ravan.platform.focus.is_password_focused", return_value=False),
            patch("ravan.ui.key_handler.vk_to_unicode", return_value="ر"),
        ):
            app._handle_key(ev_ctrl_v)

        assert ov.visible is False
        assert app._pending_predict is False
        assert app.journal.text() == ""
        assert app._just_pasted is True

        # Same for Ctrl+C: must preserve journal and NEVER leak 'ز' / 'c'
        app.journal.push("ق")
        app._just_pasted = False
        ev_ctrl_c = HookEvent(
            vk_code=ord("C"),
            flags=0,
            scan_code=0x2E,
            is_key_down=True,
            modifiers=frozenset({"ctrl"}),
        )
        with (
            patch("ravan.platform.keys.modifiers_down", return_value=False),
            patch("ravan.platform.focus.is_password_focused", return_value=False),
            patch("ravan.ui.key_handler.vk_to_unicode", return_value="ز"),
        ):
            app._handle_key(ev_ctrl_c)

        assert app.journal.text() == "ق"
        assert app._pending_predict is False
    finally:
        app.stop()


def test_paste_shortcuts_suppress_followup_space_and_backspace_resync() -> None:
    app, ov = _make_app()
    try:
        app._uia_resync_enabled = True
        pasted_uia = "سلام این یک جمله کپی شده است "

        for paste_ev in (
            HookEvent(vk_code=ord("V"), flags=0, scan_code=0, is_key_down=True, modifiers=frozenset({"ctrl"})),
            HookEvent(vk_code=ord("V"), flags=0, scan_code=0, is_key_down=True, modifiers=frozenset({"win"})),
            HookEvent(vk_code=w.VK_INSERT, flags=0, scan_code=0, is_key_down=True, modifiers=frozenset({"shift"})),
        ):
            with (
                patch("ravan.platform.focus.is_password_focused", return_value=False),
                patch("ravan.platform.focus.is_numeric_focused", return_value=False),
                patch("ravan.platform.lang.is_ime_composing", return_value=False),
                patch("ravan.platform.caret.get_text_before_caret", return_value=pasted_uia),
            ):
                app._handle_key(paste_ev)
                assert app._just_pasted is True
                assert app._pending_predict is False

                # Pressing Space immediately after paste must NOT resync pasted text or show popup
                ev_space = HookEvent(vk_code=w.VK_SPACE, flags=0, scan_code=0x39, is_key_down=True, modifiers=frozenset())
                with patch("ravan.ui.key_handler.vk_to_unicode", return_value=" "):
                    app._handle_key(ev_space)
                assert app._pending_predict is False
                app._maybe_predict()
                assert ov.visible is False

                # Pressing Backspace right after paste must NOT resync pasted text
                ev_back = HookEvent(vk_code=w.VK_BACK, flags=0, scan_code=0x0E, is_key_down=True, modifiers=frozenset())
                app._handle_key(ev_back)
                assert app._pending_predict is False
                app._maybe_predict()
                assert ov.visible is False

        # Once user types a genuine new word character, prediction resumes cleanly
        app.predictor = MagicMock()
        app.predictor.predict.return_value = [
            Candidate(text="سلام", score=10.0, kind=CandidateKind.COMPLETION)
        ]
        ev_s = HookEvent(vk_code=ord("S"), flags=0, scan_code=0x1F, is_key_down=True, modifiers=frozenset())
        with (
            patch("ravan.platform.focus.is_password_focused", return_value=False),
            patch("ravan.platform.focus.is_numeric_focused", return_value=False),
            patch("ravan.platform.lang.is_ime_composing", return_value=False),
            patch("ravan.ui.key_handler.vk_to_unicode", return_value="س"),
            patch("ravan.platform.caret.get_text_before_caret", return_value="این س"),
            patch("ravan.ui.app_polling.get_caret_rect", return_value=CaretRect(100, 200, 2, 16)),
        ):
            app._handle_key(ev_s)
            assert app._just_pasted is False
            assert app._pending_predict is True
            app._maybe_predict()
            assert ov.predicting is True
    finally:
        app.stop()


def test_clipboard_item_paste_and_empty_space_do_not_trigger_prediction() -> None:
    app, ov = _make_app()
    try:
        app._uia_resync_enabled = True
        app.journal.push("ک")
        with (
            patch("ravan.platform.clipboard.set_clipboard_text"),
            patch("ravan.platform.inject.send_shortcut"),
        ):
            app._paste_clipboard_item("این جمله از تاریخچه کلیپ‌بورد است")

        assert app._just_pasted is True
        assert app.journal.text() == ""
        assert ov.visible is False

        # Bare space when no word was typed before space (e.g. after mouse right-click paste)
        app._just_pasted = False
        app._invalidate_journal_for_external_click()
        ev_space = HookEvent(vk_code=w.VK_SPACE, flags=0, scan_code=0x39, is_key_down=True, modifiers=frozenset())
        with (
            patch("ravan.platform.focus.is_password_focused", return_value=False),
            patch("ravan.platform.focus.is_numeric_focused", return_value=False),
            patch("ravan.platform.lang.is_ime_composing", return_value=False),
            patch("ravan.ui.key_handler.vk_to_unicode", return_value=" "),
            patch("ravan.platform.caret.get_text_before_caret", return_value="این جمله راست کلیک است"),
        ):
            app._handle_key(ev_space)
            assert app._pending_predict is False
            app._maybe_predict()
            assert ov.visible is False
    finally:
        app.stop()


def test_numbers_and_numeric_formats_never_trigger_during_or_after_space() -> None:
    app, ov = _make_app()
    try:
        # Verify core numeric token helpers directly
        for num in ("123", "۱۲۳۴", "2026/01/02", "۱۴۰۵/۰۸/۲۲", "12:30", "12.5", "۱۲٫۵", "50%", "$100", "100٬۰۰۰", "-42"):
            assert is_numeric_or_symbol_token(num) is True
            assert is_valid_prediction_context_word(num) is False
            assert app.predictor.predict("", num, 5) == []
            assert app.predictor.predict(num, "", 5) == []

        # Words (including test words with trailing digits like word1) remain valid
        for word_tok in ("سلام", "hello", "می‌خواهم", "word1"):
            assert is_numeric_or_symbol_token(word_tok) is False
            assert is_valid_prediction_context_word(word_tok) is True

        # End-to-end keystrokes: type "1405" then Space -> NO popup, and not learned
        with (
            patch("ravan.platform.focus.is_password_focused", return_value=False),
            patch("ravan.platform.focus.is_numeric_focused", return_value=False),
            patch("ravan.platform.lang.is_ime_composing", return_value=False),
        ):
            for ch in ("۱", "۴", "۰", "۵"):
                ev = HookEvent(vk_code=0x30, flags=0, scan_code=0, is_key_down=True, modifiers=frozenset())
                with patch("ravan.ui.key_handler.vk_to_unicode", return_value=ch):
                    app._handle_key(ev)
                assert app._pending_predict is False
                assert ov.visible is False

            ev_space = HookEvent(vk_code=w.VK_SPACE, flags=0, scan_code=0x39, is_key_down=True, modifiers=frozenset())
            with patch("ravan.ui.key_handler.vk_to_unicode", return_value=" "):
                app._handle_key(ev_space)
            assert app._pending_predict is False
            app._maybe_predict()
            assert ov.visible is False
            assert "۱۴۰۵" not in app.predictor.learning.word_counts

        # Mixed context ending with a number ("ساعت ۱۲ ") must also stay quiet
        assert app.predictor.predict("", "ساعت ۱۲", 5) == []
    finally:
        app.stop()


def test_punctuation_ending_and_double_space_suppress_next_word() -> None:
    app, ov = _make_app()
    try:
        with (
            patch("ravan.platform.focus.is_password_focused", return_value=False),
            patch("ravan.platform.focus.is_numeric_focused", return_value=False),
            patch("ravan.platform.lang.is_ime_composing", return_value=False),
            patch("ravan.ui.app_polling.get_caret_rect", return_value=CaretRect(120, 220, 2, 16)),
        ):
            # Typing "سلام" + first Space SHOULD show next-word popup
            for ch in "سلام":
                app.journal.push(ch)
            ev_space = HookEvent(vk_code=w.VK_SPACE, flags=0, scan_code=0x39, is_key_down=True, modifiers=frozenset())
            with patch("ravan.ui.key_handler.vk_to_unicode", return_value=" "):
                app._handle_key(ev_space)
            assert app._pending_predict is True
            app._maybe_predict()
            assert ov.predicting is True

            # Pressing a second Space immediately ("سلام  ") dismisses and must NOT re-show
            with patch("ravan.ui.key_handler.vk_to_unicode", return_value=" "):
                app._handle_key(ev_space)
            assert ov.visible is False
            assert app._pending_predict is False

            # Sentence terminator then Space ("سلام. ") must NOT trigger next-word popup
            app.journal.clear()
            for ch in "سلام.":
                app.journal.push(ch)
            with patch("ravan.ui.key_handler.vk_to_unicode", return_value=" "):
                app._handle_key(ev_space)
            assert app._pending_predict is False
            app._maybe_predict()
            assert ov.visible is False
    finally:
        app.stop()


def test_hook_modifier_snapshot_and_ctrl_tab_passthrough() -> None:
    hook = KeyboardHook()
    set_popup_visible(True, swallow_digits=True, swallow_enter=False)
    try:
        kb = w.KBDLLHOOKSTRUCT()
        kb.flags = 0
        ptr = ctypes.addressof(kb)

        with (
            patch("ravan.platform.winapi.user32.GetAsyncKeyState", return_value=0),
            patch("ravan.platform.winapi.user32.CallNextHookEx", return_value=0) as mock_next,
        ):
            # 1. Press Left Ctrl (even before AsyncKeyState reports, tracked in hook)
            kb.vkCode = w.VK_LCONTROL
            kb.scanCode = 0x1D
            hook._callback(0, w.WM_KEYDOWN, ptr)

            # 2. Press '1' while Ctrl is down: must NOT be swallowed even when popup is visible
            kb.vkCode = ord("1")
            kb.scanCode = 0x02
            res = hook._callback(0, w.WM_KEYDOWN, ptr)
            assert res == 0
            assert mock_next.called

            # 3. Captured event for 'V' while Ctrl is held still carries modifiers={"ctrl"} even after Ctrl goes UP
            kb.vkCode = ord("V")
            kb.scanCode = 0x2F
            hook._callback(0, w.WM_KEYDOWN, ptr)
            kb.vkCode = w.VK_LCONTROL
            hook._callback(0, w.WM_KEYUP, ptr)

            drained = []
            while True:
                ev = hook.poll()
                if ev is None:
                    break
                drained.append(ev)
            v_events = [e for e in drained if e.vk_code == ord("V")]
            assert len(v_events) == 1
            assert v_events[0].modifiers == frozenset({"ctrl"})
    finally:
        set_popup_visible(False)
