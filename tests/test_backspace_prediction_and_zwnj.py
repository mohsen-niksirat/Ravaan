"""Regression tests for Backspace/edit prediction accuracy and live Auto-ZWNJ."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ravan.core.config import Config
from ravan.core.dict import Dictionary
from ravan.core.events import Candidate, CandidateKind
from ravan.core.journal import KeystrokeJournal
from ravan.core.learning import UserLearningEngine
from ravan.core.predictor import DictPredictor
from ravan.core.zwnj import ZWNJ, fix_joined_zwnj, match_trailing_compound, should_attach_suffix
from ravan.platform import winapi as w
from ravan.platform.caret import CaretRect
from ravan.platform.hook import HookEvent
from ravan.platform.keys import _foreground_keyboard_state
from ravan.ui.app_actions import AppActionsMixin
from ravan.ui.app_polling import AppPollingMixin
from ravan.ui.key_handler import KeyHandlerMixin


class _LiveHarnessApp(AppActionsMixin, AppPollingMixin, KeyHandlerMixin):
    def __init__(self, persian_dict: Dictionary | None = None) -> None:
        self.cfg = Config()
        self.cfg.auto_zwnj_enabled = True
        self.cfg.prediction_enabled = True
        self.cfg.prediction_debounce_ms = 0
        self.cfg.min_prefix_len = 1
        self.cfg.smart_punctuation_enabled = True
        self.cfg.autocorrect_enabled = False
        self.cfg.autofix_enabled = False

        self.journal = KeystrokeJournal()
        self.overlay = MagicMock()
        self.overlay.visible = False
        self.overlay.predicting = False
        self.overlay.clipboard_open = False
        self.overlay.has_custom_pos = False
        self.overlay.contains_screen_point.return_value = False

        self.hook = MagicMock()
        self._ui_queue = MagicMock()
        self._own_pid = 9999
        self._current_exe = "notepad.exe"
        self._current_hwnd = 1001
        self._current_window_class = "Notepad"
        self._active_layout_tag = "fa"
        self._pending_predict = False
        self._last_key_time = 0.0
        self._suppress_until = 0.0
        self._last_convert_at = 0.0
        self._last_focus_poll = 0.0
        self._last_autocorrect = None
        self._journal_desynced = False
        self._uia_resync_enabled = False
        self._mouse_left_down = False
        self._pending_click_time = None
        self._last_mouse_lang_shown = 0.0
        self.is_paused = False
        self.snippets = MagicMock()
        self.snippets.find_matching_snippet.return_value = None
        self.snippets.expand_with_cursor.return_value = None
        self.snippets.find_matching_regex_snippet.return_value = None

        if persian_dict is not None:
            self.predictor = DictPredictor(
                persian=persian_dict,
                learning_engine=UserLearningEngine(auto_load=False, learning_enabled=False),
                autocorrect_mode="off",
            )
        else:
            self.predictor = MagicMock()
            self.predictor.predict.return_value = []
            self.predictor.correct.return_value = None

    def _is_foreground_self(self) -> bool:
        return False

    def _is_excluded(self) -> bool:
        return False

    def _check_elevated(self, hwnd=None) -> bool:
        return False

    def _record_event(self, *args, **kwargs) -> None:
        pass

    def _maybe_autofix_word(self, word: str, delimiter: str = " ") -> bool:
        return False

    def _maybe_autofix_mid_word(self, word: str) -> bool:
        return False

    def _on_word_completed(self, word: str, delimiter: str = " ") -> bool:
        return False

    def _accept_candidate(self, cand) -> None:
        pass

    def _show_lang_indicator(self, use_mouse_pos: bool = False) -> None:
        pass


def test_fast_typing_after_auto_zwnj_and_backspace_stays_in_sync() -> None:
    app = _LiveHarnessApp()
    # Physical key sequence: 'م' 'ی' ' ' -> triggers auto-ZWNJ and _suppress_until=+50ms,
    # followed immediately (< 5ms) by physical 'ر', 'و', 'م', then 2 Backspaces and 'س'.
    vk_map = {1: "م", 2: "ی", w.VK_SPACE: " ", 3: "ر", 4: "و", 5: "م", 6: "س"}
    seq = [
        HookEvent(vk_code=1, flags=0, scan_code=0, is_key_down=True),
        HookEvent(vk_code=2, flags=0, scan_code=0, is_key_down=True),
        HookEvent(vk_code=w.VK_SPACE, flags=0, scan_code=0, is_key_down=True),
        HookEvent(vk_code=3, flags=0, scan_code=0, is_key_down=True),
        HookEvent(vk_code=4, flags=0, scan_code=0, is_key_down=True),
        HookEvent(vk_code=5, flags=0, scan_code=0, is_key_down=True),
        HookEvent(vk_code=w.VK_BACK, flags=0, scan_code=0, is_key_down=True),
        HookEvent(vk_code=w.VK_BACK, flags=0, scan_code=0, is_key_down=True),
        HookEvent(vk_code=6, flags=0, scan_code=0, is_key_down=True),
    ]
    poll_iter = iter(seq + [None])

    app.hook.poll.side_effect = lambda: next(poll_iter, None)
    with patch("ravan.ui.key_handler.vk_to_unicode", side_effect=lambda vk, _sc=0: vk_map.get(vk)), \
         patch("ravan.ui.key_handler.replace_last_n_with"), \
         patch("ravan.platform.focus.is_password_focused", return_value=False):
        app._drain_hook_events()

    assert app.journal.last_word() == f"می{ZWNJ}رس"


def test_backspace_then_retype_hides_stale_popup_when_no_candidates() -> None:
    app = _LiveHarnessApp()
    app.journal.push("س")
    app.journal.push("ل")
    app.journal.push("ا")
    app.journal.push("م")
    app.overlay.visible = True
    app.overlay.predicting = True
    app.predictor.predict.return_value = []

    # Backspace 'م' -> '_edited_since_popup = True', then type 'ز' -> '_last_key_was_backspace = False'
    ev_back = HookEvent(vk_code=w.VK_BACK, flags=0, scan_code=0, is_key_down=True)
    ev_z = HookEvent(vk_code=10, flags=0, scan_code=0, is_key_down=True)
    events = iter([ev_back, ev_z, None])
    app.hook.poll.side_effect = lambda: next(events, None)

    with patch("ravan.ui.key_handler.vk_to_unicode", return_value="ز"), \
         patch("ravan.platform.focus.is_password_focused", return_value=False), \
         patch("ravan.platform.focus.is_numeric_focused", return_value=False), \
         patch("ravan.platform.lang.is_ime_composing", return_value=False):
        app._drain_hook_events()
        app._last_key_time = time.monotonic() - 1.0
        app._maybe_predict()

    assert app.journal.last_word() == "سلاز"
    app.overlay.hide.assert_called()


def test_hwnd_switch_within_same_exe_resets_journal() -> None:
    app = _LiveHarnessApp()
    for ch in "قدیمی":
        app.journal.push(ch)
    app._current_exe = "chrome.exe"
    app._current_hwnd = 1001
    app._last_focus_poll = 0.0

    with patch("ravan.platform.winapi.user32.GetForegroundWindow", return_value=2002), \
         patch("ravan.ui.app_polling.foreground_exe", return_value="chrome.exe"), \
         patch("ravan.ui.app_polling.window_class_name", return_value="Chrome_WidgetWin_1"):
        app._poll_focus()

    assert app.journal.text() == ""
    assert app._journal_desynced is True
    assert app._current_hwnd == 2002


def test_mouse_click_outside_overlay_clears_journal_even_when_chip_disabled() -> None:
    app = _LiveHarnessApp()
    app.cfg.show_lang_on_click = False
    for ch in "حافظه":
        app.journal.push(ch)

    with patch("ravan.platform.winapi.user32.GetAsyncKeyState", return_value=0x8000), \
         patch("ravan.platform.caret._cursor_position", return_value=CaretRect(50, 50, 2, 16)):
        app._poll_mouse_click()

    assert app.journal.text() == ""
    assert app._journal_desynced is True


def test_mouse_click_inside_overlay_preserves_journal_for_candidate_accept() -> None:
    app = _LiveHarnessApp()
    for ch in "سلام":
        app.journal.push(ch)
    app.overlay.visible = True
    app.overlay.contains_screen_point.return_value = True

    with patch("ravan.platform.winapi.user32.GetAsyncKeyState", return_value=0x8000), \
         patch("ravan.platform.caret._cursor_position", return_value=CaretRect(300, 300, 2, 16)):
        app._poll_mouse_click()

    assert app.journal.text() == "سلام"


def test_tab_and_ctrl_tab_clear_stale_journal() -> None:
    app = _LiveHarnessApp()
    for ch in "قبلی":
        app.journal.push(ch)

    ev_tab = HookEvent(vk_code=w.VK_TAB, flags=0, scan_code=0, is_key_down=True)
    with patch("ravan.platform.focus.is_password_focused", return_value=False), \
         patch("ravan.platform.keys.modifiers_down", return_value=False):
        app._handle_key(ev_tab)

    assert app.journal.text() == ""
    assert app._journal_desynced is True

    for ch in "تب":
        app.journal.push(ch)
    with patch("ravan.platform.focus.is_password_focused", return_value=False), \
         patch("ravan.platform.keys.modifiers_down", side_effect=lambda mods, exact=False: "ctrl" in mods):
        app._handle_key(ev_tab)

    assert app.journal.text() == ""
    assert app._journal_desynced is True


def test_uia_resync_on_backspace_predicts_remaining_text_after_click() -> None:
    app = _LiveHarnessApp()
    app._uia_resync_enabled = True
    app._journal_desynced = True  # e.g. user clicked inside existing paragraph
    app.predictor.predict.return_value = [
        Candidate(text="برنامه", score=10.0, kind=CandidateKind.COMPLETION)
    ]

    ev_back = HookEvent(vk_code=w.VK_BACK, flags=0, scan_code=0, is_key_down=True)
    with patch("ravan.platform.focus.is_password_focused", return_value=False), \
         patch("ravan.platform.focus.is_numeric_focused", return_value=False), \
         patch("ravan.platform.lang.is_ime_composing", return_value=False), \
         patch("ravan.platform.caret.get_text_before_caret", return_value="این برنام"), \
         patch("ravan.ui.app_polling.get_caret_rect", return_value=CaretRect(100, 200, 2, 16)):
        app._handle_key(ev_back)
        assert app._pending_predict is True
        app._last_key_time = time.monotonic() - 1.0
        app._maybe_predict()

    app.predictor.predict.assert_called_once()
    args, _ = app.predictor.predict.call_args
    assert args[0] == "برنام"
    assert app.journal.last_word() == "برنام"


def test_foreground_keyboard_state_syncs_live_shift() -> None:
    def _fake_async(vk: int) -> int:
        return 0x8000 if vk in (w.VK_SHIFT, w.VK_LSHIFT) else 0

    with patch("ravan.platform.winapi.user32.GetKeyboardState", return_value=1), \
         patch("ravan.platform.winapi.user32.GetAsyncKeyState", side_effect=_fake_async), \
         patch("ravan.platform.winapi.user32.GetKeyState", return_value=0):
        state = _foreground_keyboard_state()

    assert state[w.VK_SHIFT] == 0x80
    assert state[w.VK_LSHIFT] == 0x80


def test_dictionary_completions_with_zwnj_prefix_and_suffix() -> None:
    fa = Dictionary.persian()
    mi_k = [e.word for e in fa.completions(f"می{ZWNJ}ک", 5)]
    assert mi_k and any(w.startswith(f"می{ZWNJ}ک") for w in mi_k)

    nami_d = [e.word for e in fa.completions(f"نمی{ZWNJ}د", 5)]
    assert nami_d and any(w.startswith(f"نمی{ZWNJ}د") for w in nami_d)

    ketab_ha = [e.word for e in fa.completions(f"کتاب{ZWNJ}ه", 5)]
    assert f"کتاب{ZWNJ}ها" in ketab_ha


def test_live_auto_zwnj_compounds_punctuation_and_joined_words() -> None:
    fa = Dictionary.persian()
    app = _LiveHarnessApp(persian_dict=fa)

    def _feed_text(text: str) -> str:
        app.journal.clear()
        screen: list[str] = []

        def _fake_replace(n: int, repl: str, cursor_offset=None) -> None:
            for _ in range(n):
                if screen:
                    screen.pop()
            screen.extend(repl)

        with patch("ravan.ui.key_handler.replace_last_n_with", side_effect=_fake_replace), \
             patch("ravan.ui.app_actions.replace_last_n_with", side_effect=_fake_replace), \
             patch("ravan.ui.key_handler.current_language", return_value=SimpleNamespace(tag="fa", is_persian=True)), \
             patch("ravan.platform.focus.is_password_focused", return_value=False):
            for idx, ch in enumerate(text):
                screen.append(ch)
                vk = w.VK_SPACE if ch == " " else 100 + idx
                with patch("ravan.ui.key_handler.vk_to_unicode", return_value=ch):
                    app._handle_key(HookEvent(vk_code=vk, flags=0, scan_code=0, is_key_down=True))
        assert "".join(screen) == app.journal.text()
        return app.journal.text()

    # 1. Punctuation-delimited suffix ZWNJ & colloquial plurals/possessives
    assert _feed_text("کتاب ها،") == f"کتاب{ZWNJ}ها،"
    assert _feed_text("خونه مون؟") == f"خونه{ZWNJ}مون؟"
    assert _feed_text("کتاب ها,") == f"کتاب{ZWNJ}ها،"  # smart punctuation + ZWNJ!

    # 2. Multi-word compounds fixed live
    assert _feed_text("برنامه نویس ") == f"برنامه{ZWNJ}نویس "
    assert _feed_text("گفت و گو.") == f"گفت{ZWNJ}وگو."
    assert _feed_text("فوق العاده،") == f"فوق{ZWNJ}العاده،"

    # 3. Joined words fixed live without space
    assert _feed_text("میروم ") == f"می{ZWNJ}روم "
    assert _feed_text("نمیدانم ") == f"نمی{ZWNJ}دانم "
    assert _feed_text("کتابها ") == f"کتاب{ZWNJ}ها "
    assert _feed_text("برنامهها ") == f"برنامه{ZWNJ}ها "
    assert _feed_text("بیشمار ") == f"بی{ZWNJ}شمار "

    # 4. Exceptions must NEVER get spurious ZWNJ
    for word in ("مینا", "بیمار", "بیشتر", "بهتر", "دختر", "میگو", "میمون", "تنها", "انتها", "منتها", "روزنامه"):
        assert _feed_text(f"{word} ") == f"{word} "


def test_zwnj_core_helpers_colloquial_and_safety() -> None:
    assert should_attach_suffix("بچه", "هامون") is True
    assert should_attach_suffix("خونه", "مون") is True
    assert should_attach_suffix("او", "مون") is False  # vowel + colloquial 'مون' blocked
    assert match_trailing_compound("یک برنامه نویس") == ("برنامه نویس", f"برنامه{ZWNJ}نویس")
    fa = Dictionary.persian()
    assert fix_joined_zwnj("میخواهم", fa.contains) == f"می{ZWNJ}خواهم"
    assert fix_joined_zwnj("بیشتر", fa.contains) is None
