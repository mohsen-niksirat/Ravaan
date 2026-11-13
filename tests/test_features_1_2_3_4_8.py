"""Comprehensive & non-interference tests for Features 1, 2, 3, 4, and 8."""

from __future__ import annotations

import tkinter as tk
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ravan.core.config import Config, config_from_dict, config_to_dict
from ravan.core.dict import DictEntry, Dictionary, Language
from ravan.core.journal import KeystrokeJournal
from ravan.core.layout import LayoutMapper
from ravan.core.learning import UserLearningEngine
from ravan.core.orthography import (
    add_blacklist_token,
    check_live_orthography,
    is_token_blacklisted,
)
from ravan.core.predictor import DictPredictor
from ravan.core.profiles import (
    detect_builtin_preset,
    normalize_exe_key,
    resolve_effective_profile,
    sanitize_app_profiles,
)
from ravan.core.zwnj import ZWNJ
from ravan.platform import winapi as w
from ravan.platform.caret import CaretRect, get_selected_text_and_rect, set_mock_selection
from ravan.platform.hook import HookEvent
from ravan.platform.lang import LanguageInfo
from ravan.ui.app_actions import AppActionsMixin
from ravan.ui.app_autofix import AppAutofixMixin
from ravan.ui.app_polling import AppPollingMixin
from ravan.ui.key_handler import KeyHandlerMixin
from ravan.ui.selection_toolbar import SelectionToolbarWindow
from ravan.ui.settings import SettingsWindow
from ravan.ui.settings_reset import reset_tab_defaults
from ravan.ui.theme import rects_overlap, resolve_popup_position
from ravan.ui.undo_chip import UndoChipWindow


class _FeatureHarnessApp(AppActionsMixin, AppAutofixMixin, AppPollingMixin, KeyHandlerMixin):
    """Unified headless harness wiring real mixins for cross-feature integration tests."""

    def __init__(self, tmp_path=None, persian_dict: Dictionary | None = None) -> None:
        self.cfg = Config()
        self.cfg.auto_zwnj_enabled = True
        self.cfg.orthography_guard_enabled = True
        self.cfg.orthography_guard_mode = "safe"
        self.cfg.quick_undo_chip_enabled = True
        self.cfg.selection_toolbar_enabled = True
        self.cfg.app_profiles_enabled = True
        self.cfg.smart_punctuation_enabled = True
        self.cfg.prediction_enabled = True
        self.cfg.prediction_debounce_ms = 0
        self.cfg.autofix_mode = "safe"
        self.cfg.autofix_enabled = True
        self.cfg.autocorrect_enabled = False
        self.cfg.show_lang_on_click = False

        self.journal = KeystrokeJournal()
        self.overlay = MagicMock()
        self.overlay.visible = False
        self.overlay.predicting = False
        self.overlay.clipboard_open = False
        self.overlay.has_custom_pos = False
        self.overlay._root = None
        self.overlay.contains_screen_point.return_value = False
        self.overlay.bounds = MagicMock(return_value=None)

        self.undo_chip = MagicMock()
        self.undo_chip.visible = False
        self.undo_chip.bounds.return_value = None
        self.undo_chip.contains_screen_point.return_value = False

        self.selection_toolbar = MagicMock()
        self.selection_toolbar.visible = False
        self.selection_toolbar.bounds.return_value = None
        self.selection_toolbar.contains_screen_point.return_value = False

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
        self._last_lang_poll = 0.0
        self._last_mouse_lang_shown = 0.0
        self._last_tap_up_time = 0.0
        self._last_double_click_time = 0.0
        self._last_autocorrect = None
        self._last_quick_undo = None
        self._last_profile_layout_exe = None
        self._pending_selection_check_time = None
        self._pending_click_time = None
        self._journal_desynced = False
        self._uia_resync_enabled = False
        self._mouse_left_down = False
        self.is_paused = False
        self.power_mode_active = False

        self.snippets = MagicMock()
        self.snippets.find_matching_snippet.return_value = None
        self.snippets.expand_with_cursor.return_value = None
        self.snippets.find_matching_regex_snippet.return_value = None

        fa_dict = persian_dict or Dictionary(
            [
                DictEntry("سلام", 1, 1000),
                DictEntry("میروم", 2, 500),
                DictEntry("می‌روم", 3, 900),
            ],
            Language.PERSIAN,
        )
        self.learning = UserLearningEngine(
            storage_path=(tmp_path / "learning.json") if tmp_path else None,
            auto_load=False,
            learning_enabled=True,
        )
        self.predictor = DictPredictor(
            persian=fa_dict,
            english=Dictionary(
                [DictEntry("hello", 1, 1000), DictEntry("world", 2, 900)],
                Language.ENGLISH,
            ),
            learning_engine=self.learning,
            autocorrect_mode="off",
        )
        self.mapper = LayoutMapper()
        self._init_autofix()
        self.tray = MagicMock()
        self.ai_assistant = MagicMock()

    def _is_foreground_self(self) -> bool:
        return False

    def _is_excluded(self) -> bool:
        return self.cfg.is_excluded(self._current_exe)

    def _check_elevated(self, hwnd=None) -> bool:
        return False

    def _record_event(self, *args, **kwargs) -> None:
        pass

    def _on_word_completed(self, word: str, delimiter: str = "") -> bool:
        return self._maybe_autofix_word(word, delimiter=delimiter)


def _type_chars_into(app: _FeatureHarnessApp, chars: str, lang_tag: str = "fa") -> list[str]:
    """Simulate real character keystrokes against an in-memory text buffer."""
    screen = [""]
    fa_lang = LanguageInfo(
        hkl=0x04290429 if lang_tag == "fa" else 0x04090409,
        tag=lang_tag,
        name="Persian" if lang_tag == "fa" else "English",
    )

    def fake_replace(delete_n: int, repl: str) -> None:
        if delete_n > 0:
            screen[0] = screen[0][:-delete_n]
        screen[0] += repl

    char_list = list(chars)
    with (
        patch("ravan.ui.key_handler.current_language", return_value=fa_lang),
        patch("ravan.ui.app_actions.current_language", return_value=fa_lang),
        patch("ravan.ui.key_handler.replace_last_n_with", side_effect=fake_replace),
        patch("ravan.ui.app_actions.replace_last_n_with", side_effect=fake_replace),
        patch("ravan.ui.app_actions.get_caret_rect", return_value=CaretRect(200, 300, 10, 22)),
        patch("ravan.platform.focus.is_password_focused", return_value=False),
        patch("ravan.ui.key_handler.is_ime_composing", return_value=False, create=True),
        patch(
            "ravan.ui.key_handler.vk_to_unicode",
            side_effect=lambda _vk, scan: char_list[scan] if 0 <= scan < len(char_list) else "",
        ),
        patch("ravan.ui.key_handler.set_popup_visible"),
        patch("ravan.platform.keys.modifiers_down", return_value=False),
        patch("ravan.ui.key_handler.matches_hotkey", return_value=False),
    ):
        for idx, ch in enumerate(char_list):
            screen[0] += ch
            ev = HookEvent(
                vk_code=w.VK_SPACE if ch == " " else 0x41,
                flags=0,
                scan_code=idx,
                is_key_down=True,
            )
            app._handle_key(ev)
    return screen


# ── Feature 4: Per-App Smart Profiles ──────────────────────────────────────


def test_profiles_sanitize_and_builtin_resolution():
    assert normalize_exe_key(r"C:\Program Files\Microsoft VS Code\Code.exe") == "code.exe"
    assert detect_builtin_preset("PowerShell.exe") == "code"
    assert detect_builtin_preset("telegram.exe") == "chat"
    assert detect_builtin_preset("winword.exe") == "formal"
    assert detect_builtin_preset("notepad.exe") == "default"

    cleaned = sanitize_app_profiles(
        {
            r"C:\Apps\Code.exe": {
                "preset": "invalid_preset",
                "auto_zwnj": True,
                "orthography_guard": "not_bool",
                "preferred_layout": "INVALID",
            }
        }
    )
    assert cleaned == {
        "code.exe": {
            "preset": "custom",
            "preferred_layout": "none",
            "auto_zwnj": True,
            "orthography_guard": None,
            "smart_punctuation": None,
            "prediction_enabled": None,
            "autofix_enabled": None,
            "selection_toolbar": None,
        }
    }


def test_profiles_code_builtin_protects_globals_and_user_override_wins():
    cfg = Config()
    cfg.auto_zwnj_enabled = True
    cfg.orthography_guard_enabled = True
    cfg.smart_punctuation_enabled = True
    cfg.prediction_enabled = True
    cfg.selection_toolbar_enabled = True

    code_prof = resolve_effective_profile(cfg, "code.exe")
    assert code_prof.source == "builtin"
    assert code_prof.preset == "code"
    assert code_prof.auto_zwnj is False
    assert code_prof.orthography_guard is False
    assert code_prof.smart_punctuation is False
    assert code_prof.autofix_enabled is False
    assert code_prof.selection_toolbar is False
    assert code_prof.prediction_enabled is True  # inherits global

    # Built-in chat/formal should NOT force overrides without explicit user rule
    tg_prof = resolve_effective_profile(cfg, "telegram.exe")
    assert tg_prof.preset == "chat"
    assert tg_prof.smart_punctuation is True

    # Explicit user rule on code.exe overrides built-in code preset
    cfg.app_profiles["code.exe"] = {
        "preset": "custom",
        "auto_zwnj": True,
        "orthography_guard": True,
        "preferred_layout": "en",
    }
    user_code = resolve_effective_profile(cfg, "code.exe")
    assert user_code.source == "user"
    assert user_code.auto_zwnj is True
    assert user_code.orthography_guard is True
    assert user_code.preferred_layout == "en"

    # Global disable bypasses profiles cleanly
    cfg.app_profiles_enabled = False
    disabled_prof = resolve_effective_profile(cfg, "code.exe")
    assert disabled_prof.source == "global"
    assert disabled_prof.auto_zwnj is True


def test_profile_code_stops_zwnj_orthography_and_punctuation_at_runtime(tmp_path):
    app = _FeatureHarnessApp(tmp_path=tmp_path)
    app._current_exe = "code.exe"

    screen = _type_chars_into(app, "انشاالله؟ ")
    assert screen[0] == "انشاالله؟ "
    app.undo_chip.show.assert_not_called()

    app.journal.clear()
    screen2 = _type_chars_into(app, "می روم")
    assert screen2[0] == "می روم"


def test_profile_focus_preferred_layout_switch_respects_safety_guards(tmp_path):
    app = _FeatureHarnessApp(tmp_path=tmp_path)
    app.cfg.app_profiles = {
        "winword.exe": {"preset": "formal", "preferred_layout": "fa"},
    }
    en_lang = LanguageInfo(hkl=0x04090409, tag="en", name="English")
    app.undo_chip.visible = True
    app.selection_toolbar.visible = True

    # Blocked in password field -> never switch
    with (
        patch("ravan.ui.app_polling.w.user32") as mock_u32,
        patch("ravan.ui.app_polling.foreground_exe", return_value="winword.exe"),
        patch("ravan.ui.app_polling.window_class_name", return_value="OpusApp"),
        patch("ravan.platform.focus.is_fullscreen_focused", return_value=False),
        patch("ravan.platform.focus.is_password_focused", return_value=True),
        patch("ravan.platform.lang.is_ime_composing", return_value=False),
        patch("ravan.platform.lang.current_language", return_value=en_lang),
        patch("ravan.platform.lang.switch_to_language") as mock_sw,
    ):
        mock_u32.GetForegroundWindow.return_value = 2002
        app._poll_focus()
        mock_sw.assert_not_called()

    # Reset hwnd and simulate clean focus gain in Word -> switches to Persian
    app._current_hwnd = 1001
    app._current_exe = "notepad.exe"
    app._last_focus_poll = 0.0
    app._last_profile_layout_exe = None
    app.undo_chip.visible = True
    app.selection_toolbar.visible = True
    with (
        patch("ravan.ui.app_polling.w.user32") as mock_u32,
        patch("ravan.ui.app_polling.foreground_exe", return_value="winword.exe"),
        patch("ravan.ui.app_polling.window_class_name", return_value="OpusApp"),
        patch("ravan.platform.focus.is_fullscreen_focused", return_value=False),
        patch("ravan.platform.focus.is_password_focused", return_value=False),
        patch("ravan.platform.lang.is_ime_composing", return_value=False),
        patch("ravan.platform.lang.current_language", return_value=en_lang),
        patch("ravan.platform.lang.switch_to_language") as mock_sw,
    ):
        mock_u32.GetForegroundWindow.return_value = 2002
        app._poll_focus()
        mock_sw.assert_called_once_with("fa", hwnd=2002)
        app.undo_chip.hide.assert_called()
        app.selection_toolbar.hide.assert_called()


# ── Feature 3: Real-Time Persian Orthography Guard ─────────────────────────


def test_orthography_guard_modes_and_safety():
    # Safe fixes
    s1 = check_live_orthography("انشاالله", mode="safe")
    assert s1 is not None and s1.replacement == "ان‌شاءالله"

    s2 = check_live_orthography("حتما", mode="safe")
    assert s2 is not None and s2.replacement == "حتماً" and s2.reason == "tanween"

    s3 = check_live_orthography("بصورت", mode="safe")
    assert s3 is not None and s3.replacement == "به صورت" and s3.reason == "preposition"

    s4 = check_live_orthography("كيفيت", mode="safe")
    assert s4 is not None and s4.replacement == "کیفیت" and s4.reason == "arabic_chars"

    # Multi-word compound phrase
    s5 = check_live_orthography("گو", recent_words=["سلام", "گفت", "و", "گو"], mode="safe")
    assert s5 is not None and s5.original == "گفت و گو" and s5.replacement == "گفت‌وگو"

    # Safe vs Strict mode
    assert check_live_orthography("لطفا", mode="safe") is None
    strict_lut = check_live_orthography("لطفا", mode="strict")
    assert strict_lut is not None and strict_lut.replacement == "لطفاً"

    # Off mode & non-Persian/code tokens ignored
    assert check_live_orthography("انشاالله", mode="off") is None
    assert check_live_orthography("user_1", mode="strict") is None
    assert check_live_orthography("۱۴۰۳", mode="strict") is None

    # Blacklist blocks single and multi-word matches
    assert check_live_orthography("انشاالله", mode="safe", blacklist=["انشاالله"]) is None
    assert check_live_orthography("كيفيت", mode="safe", blacklist=["کیفیت"]) is None


def test_live_orthography_and_smart_punctuation_chain(tmp_path):
    app = _FeatureHarnessApp(tmp_path=tmp_path)
    screen = _type_chars_into(app, "انشاالله?")
    # Smart punctuation converts '?' -> '؟', then orthography guard fixes 'انشاالله' -> 'ان‌شاءالله'
    assert screen[0] == "ان‌شاءالله؟"
    assert app._last_quick_undo is not None
    assert app._last_quick_undo["original"] == "انشاالله"
    assert app._last_quick_undo["replacement"] == "ان‌شاءالله"
    app.undo_chip.show.assert_called_once()


def test_orthography_respects_ignored_words(tmp_path):
    app = _FeatureHarnessApp(tmp_path=tmp_path)
    app.cfg.ignored_words = ["انشاالله"]
    screen = _type_chars_into(app, "انشاالله ")
    assert screen[0] == "انشاالله "
    app.undo_chip.show.assert_not_called()


# ── Feature 2: Inline Quick-Undo Chip & Auto-Learn Blacklist ──────────────


def test_quick_undo_reverts_and_auto_blacklists_zwnj_and_orthography(tmp_path):
    app = _FeatureHarnessApp(tmp_path=tmp_path)
    with patch("ravan.core.config.save_config") as mock_save:
        screen = _type_chars_into(app, "کتاب ها ")
        assert screen[0] == f"کتاب{ZWNJ}ها "
        assert app._last_quick_undo is not None
        app.undo_chip.show.assert_called()

        # Simulate clicking Quick-Undo button by rewiring replace_last_n_with against same screen buffer
        def fake_rep(n: int, r: str) -> None:
            screen[0] = (screen[0][:-n] if n > 0 else screen[0]) + r

        with patch("ravan.ui.app_actions.replace_last_n_with", side_effect=fake_rep):
            reverted = app._undo_quick_fix()
        assert reverted is True
        assert screen[0] == "کتاب ها "
        assert is_token_blacklisted("کتاب ها", app.cfg.zwnj_orthography_blacklist)
        mock_save.assert_called_once()

    # Subsequent typing of "کتاب ها " must NOT auto-attach ZWNJ!
    app.journal.clear()
    app.undo_chip.show.reset_mock()
    screen_again = _type_chars_into(app, "کتاب ها ")
    assert screen_again[0] == "کتاب ها "
    app.undo_chip.show.assert_not_called()


def test_quick_undo_cooperates_with_autofix_stack_by_timestamp(tmp_path):
    app = _FeatureHarnessApp(tmp_path=tmp_path)
    app.autofix.record_fix(
        original="sghl",
        fixed="سلام",
        app_name="notepad.exe",
        layout_from="en",
        layout_to="fa",
        delimiter=" ",
    )
    # Make quick undo newer than autofix correction
    t_af = app.autofix.correction_stack[-1].timestamp
    app._last_quick_undo = {
        "kind": "orthography",
        "original": "حتما",
        "replacement": "حتماً",
        "delimiter": " ",
        "blacklist_token": "حتما",
        "timestamp": t_af + 5.0,
    }
    app.journal._chars.extend(list("حتماً "))

    with (
        patch("ravan.ui.app_actions.replace_last_n_with"),
        patch("ravan.core.config.save_config"),
    ):
        app._undo_last_correction()

    # Quick-Undo handled it, autofix history remains intact!
    assert len(app.autofix.correction_stack) == 1
    assert is_token_blacklisted("حتما", app.cfg.zwnj_orthography_blacklist)


def test_undo_chip_real_tk_window_and_overlap_avoidance():
    root = tk.Tk()
    root.withdraw()
    undo_calls = []
    chip = UndoChipWindow(parent=root, on_undo=lambda: undo_calls.append(True), theme_mode="dark")
    try:
        avoid = (180, 280, 420, 460)
        chip.show(
            replacement="ان‌شاءالله",
            original="انشاالله",
            x=200,
            y=300,
            avoid_rect=avoid,
            duration_ms=4000,
        )
        assert chip.visible is True
        b = chip.bounds()
        assert b is not None
        assert not rects_overlap(b, avoid)
        cx = (b[0] + b[2]) // 2
        cy = (b[1] + b[3]) // 2
        assert chip.contains_screen_point(cx, cy) is True
        assert chip.contains_screen_point(0, 0) is False

        chip.hide()
        assert chip.visible is False
        assert chip.bounds() is None
    finally:
        chip.destroy()
        root.destroy()


# ── Feature 1: Floating Selection Mini-Toolbar ──────────────────────────────


def test_mock_selection_hook_and_toolbar_window():
    try:
        rect = CaretRect(150, 220, 90, 20)
        set_mock_selection(("hello", rect))
        assert get_selected_text_and_rect() == ("hello", rect)
        set_mock_selection(None)
    finally:
        set_mock_selection(None)

    root = tk.Tk()
    root.withdraw()
    triggered = []
    tb = SelectionToolbarWindow(parent=root, on_action=triggered.append, theme_mode="light")
    try:
        avoid = [(120, 175, 280, 220)]
        tb.show(x=160, y=230, width=80, height=20, show_ai=True, avoid_rects=avoid, duration_ms=4000)
        assert tb.visible is True
        b = tb.bounds()
        assert b is not None
        assert not rects_overlap(b, avoid[0])
        assert tb._buttons["ai"].winfo_manager() == "pack"

        tb.show(x=160, y=230, width=80, height=20, show_ai=False)
        assert tb._buttons["ai"].winfo_manager() == ""

        tb._trigger("normalize")
        assert triggered == ["normalize"]
        assert tb.visible is False
    finally:
        tb.destroy()
        root.destroy()


def test_drag_and_double_click_trigger_selection_toolbar_even_if_lang_click_off(tmp_path):
    app = _FeatureHarnessApp(tmp_path=tmp_path)
    app.cfg.show_lang_on_click = False
    app.cfg.ai_assistant_enabled = True
    app._current_exe = "notepad.exe"

    # Test drag release -> schedules selection check -> _dispatch_selection_toolbar shows toolbar
    app._mouse_left_down = True
    app._mouse_down_time = 100.0
    app._mouse_down_pos = CaretRect(100, 100, 0, 0)

    try:
        set_mock_selection(("سلام سحیح", CaretRect(100, 100, 120, 20)))
        with (
            patch("ravan.ui.app_polling.w.user32") as mock_u32,
            patch("ravan.ui.app_polling.time.monotonic", side_effect=[100.6, 100.8]),
            patch("ravan.platform.focus.is_password_focused", return_value=False),
            patch("ravan.platform.focus.is_fullscreen_focused", return_value=False),
        ):
            mock_u32.GetAsyncKeyState.return_value = 0  # mouse released after >0.45s
            app._poll_mouse_click()
            assert app._pending_selection_check_time is not None

            mock_u32.GetAsyncKeyState.return_value = 0
            app._poll_mouse_click()  # second tick passes pending timestamp
            app.selection_toolbar.show.assert_called_once()
            kwargs = app.selection_toolbar.show.call_args.kwargs
            assert kwargs["show_ai"] is True
    finally:
        set_mock_selection(None)

    # Blocked in built-in code profile
    app.selection_toolbar.show.reset_mock()
    app._current_exe = "code.exe"
    try:
        set_mock_selection(("selected code", CaretRect(10, 10, 40, 20)))
        with (
            patch("ravan.platform.focus.is_password_focused", return_value=False),
            patch("ravan.platform.focus.is_fullscreen_focused", return_value=False),
        ):
            app._dispatch_selection_toolbar()
        app.selection_toolbar.show.assert_not_called()
    finally:
        set_mock_selection(None)


def test_selection_toolbar_actions_and_overlay_hit_protection(tmp_path):
    app = _FeatureHarnessApp(tmp_path=tmp_path)
    app.selection_toolbar.visible = True
    app.selection_toolbar.contains_screen_point.return_value = True
    assert app._is_point_in_overlay(CaretRect(250, 250, 0, 0)) is True

    app._convert_selection_or_last_word = MagicMock()
    app._toggle_digits_selection_or_last_word = MagicMock()

    app._on_selection_toolbar_action("convert")
    app._convert_selection_or_last_word.assert_called_once()

    app._on_selection_toolbar_action("digits")
    app._toggle_digits_selection_or_last_word.assert_called_once()

    with patch.object(app, "_trigger_ai_assistant", create=True) as mock_ai:
        app._on_selection_toolbar_action("ai")
        mock_ai.assert_called_once()

    with patch("ravan.platform.clipboard.try_convert_selection") as mock_try:
        app._on_selection_toolbar_action("normalize")
        mock_try.assert_called_once()
        fn = mock_try.call_args.args[0]
        polished = fn("عليكم انشاالله می روم")
        assert "ی" in polished and f"می{ZWNJ}روم" in polished


def test_escape_key_dismisses_both_floating_popups(tmp_path):
    app = _FeatureHarnessApp(tmp_path=tmp_path)
    app.undo_chip.visible = True
    app.selection_toolbar.visible = True

    with (
        patch("ravan.ui.key_handler.current_language", return_value=LanguageInfo(0x04290429, "fa", "Persian")),
        patch("ravan.platform.focus.is_password_focused", return_value=False),
        patch("ravan.ui.key_handler.vk_to_unicode", return_value=""),
        patch("ravan.ui.key_handler.set_popup_visible"),
        patch("ravan.platform.keys.modifiers_down", return_value=False),
        patch("ravan.ui.key_handler.matches_hotkey", return_value=False),
    ):
        app._handle_key(HookEvent(vk_code=w.VK_ESCAPE, flags=0, scan_code=0, is_key_down=True))

    app.undo_chip.hide.assert_called()
    app.selection_toolbar.hide.assert_called()


# ── Feature 8: Learning Manager & Personal Corpus Import ───────────────────


def test_learning_manager_list_forget_exclude_and_corpus_import(tmp_path):
    eng = UserLearningEngine(storage_path=tmp_path / "learn.json", auto_load=False, learning_enabled=True)

    sample = (
        "سلام بر شما همکار گرامی.\n"
        "هوش مصنوعی و یادگیری ماشین بسیار مهم است! "
        "لطفا به https://example.com/test نروید و كد زیر را بخوانید."
    )
    stats = eng.import_corpus_text(sample, app_name="winword.exe", save_now=True)
    assert stats["words_added"] > 0
    assert stats["unique_words"] > 0
    # URL & Arabic-letter normalization honored; exact 1x count (no triple-counting)
    assert "https" not in eng.word_counts
    assert eng.word_counts["هوش"] == 1
    assert eng.word_counts["کد"] == 1  # normalized from 'كد'

    # Sentence boundary preserved: last word before period ("گرامی") must not transition to "هوش"
    assert "هوش" not in eng.transitions.get("گرامی", {})
    assert eng.transitions.get("هوش", {}).get("مصنوعی", 0) == 1

    # Query filter normalizes Arabic 'ي/ك' to match Persian 'ی/ک'
    filtered = eng.list_learned_words(query="ك")
    assert any(word == "کد" for word, _score in filtered)

    # Forget clears word from unigrams, app_counts, bigrams, and trigrams
    assert eng.forget_word("هوش", save_now=True) is True
    assert "هوش" not in eng.word_counts
    assert "هوش" not in eng.transitions
    for nexts in eng.transitions.values():
        assert "هوش" not in nexts
    for k3 in eng.trigrams:
        assert "هوش" not in k3

    # Exclude word blocks it cleanly in Config & DictPredictor
    cfg = Config()
    pred = DictPredictor(
        persian=Dictionary([DictEntry("سلام", 1, 500)], Language.PERSIAN),
        learning_engine=eng,
        ignored_words=cfg.ignored_words,
        autocorrect_mode="off",
    )
    assert any(
        c.text == "مصنوعی"
        for c in pred.predict("مص", context="", limit=5, app_name="winword.exe")
    )
    with patch("ravan.core.config.save_config"):
        eng.exclude_word("مصنوعی", cfg=cfg, save_now=True)
    pred.ignored_words = cfg.ignored_words
    assert all(
        c.text != "مصنوعی"
        for c in pred.predict("مص", context="", limit=5, app_name="winword.exe")
    )

    # Windows-1256 corpus file import works cleanly (with Arabic ي normalized to Persian ی)
    cp_file = tmp_path / "farsi_cp1256.txt"
    cp_file.write_bytes("توسعه نرم افزار با پايتون عالي است.".encode("cp1256"))
    fstats = eng.import_corpus_file(cp_file, save_now=True)
    assert fstats["words_added"] >= 4
    assert "پایتون" in eng.word_counts


def test_config_roundtrip_and_settings_window_integration(tmp_path):
    raw = {
        "schema_version": 3,
        "app_profiles_enabled": True,
        "app_profiles": {
            "obsidian.exe": {"preset": "formal", "auto_zwnj": True, "preferred_layout": "fa"}
        },
        "orthography_guard_enabled": True,
        "orthography_guard_mode": "strict",
        "quick_undo_chip_enabled": False,
        "zwnj_orthography_blacklist": ["انشاالله"],
        "selection_toolbar_enabled": True,
    }
    cfg = config_from_dict(raw)
    assert cfg.schema_version == 3
    assert cfg.orthography_guard_mode == "strict"
    assert cfg.quick_undo_chip_enabled is False
    assert cfg.zwnj_orthography_blacklist == ["انشاالله"]
    dumped = config_to_dict(cfg)
    assert dumped["app_profiles"]["obsidian.exe"]["preferred_layout"] == "fa"

    eng = UserLearningEngine(storage_path=tmp_path / "settings_learn.json", auto_load=False)
    eng.learn_word("راوان")
    saved_cfgs: list[Config] = []

    with (
        patch.object(SettingsWindow, "flash_saved"),
        patch("ravan.ui.settings_save.messagebox.showinfo"),
        patch("ravan.ui.settings_save.messagebox.showwarning"),
        patch("ravan.ui.settings_reset.messagebox.askyesno", return_value=True),
        patch("ravan.ui.settings_save.save_config"),
        patch("ravan.core.user_dict.save_user_words"),
    ):
        win = SettingsWindow(cfg, on_saved=saved_cfgs.append, learning_engine=eng)
        try:
            win.show()
            for _ in range(40):
                win.tick()
            assert win._root is not None

            # Verify notebook structure: Hotkeys kept at index 3, App Profiles added at index 5
            assert win._nb.index("end") == 9
            assert win._orthography_mode_var.get() == "strict"

            win._orthography_guard_var.set(False)
            win._orthography_mode_var.set("safe")
            win._quick_undo_chip_var.set(True)
            win._selection_toolbar_var.set(False)

            # Blacklist + Profile updates
            win._managed_zwnj_blacklist = add_blacklist_token(win._managed_zwnj_blacklist, "می شود")
            win._managed_app_profiles["telegram.exe"] = {
                "preset": "chat",
                "auto_zwnj": True,
                "preferred_layout": "fa",
            }
            win._save()

            assert saved_cfgs, "on_saved callback must fire on _save()"
            new_cfg = saved_cfgs[-1]
            assert new_cfg.orthography_guard_enabled is False
            assert new_cfg.orthography_guard_mode == "safe"
            assert new_cfg.quick_undo_chip_enabled is True
            assert new_cfg.selection_toolbar_enabled is False
            assert "می شود" in new_cfg.zwnj_orthography_blacklist
            assert new_cfg.app_profiles["telegram.exe"]["preferred_layout"] == "fa"

            # Verify tab reset restores clean defaults
            reset_tab_defaults(win, "general")
            assert win._orthography_guard_var.get() is True
            assert win._orthography_mode_var.get() == "safe"
            reset_tab_defaults(win, "profiles")
            assert win._app_profiles_enabled_var.get() is True
            assert win._managed_app_profiles == {}
        finally:
            win._close()


def test_resolve_popup_position_clamps_and_avoids_overlap():
    fake_win = SimpleNamespace(
        winfo_vrootx=lambda: 0,
        winfo_vrooty=lambda: 0,
        winfo_screenwidth=lambda: 1920,
        winfo_screenheight=lambda: 1080,
    )
    avoid = [(200, 300, 420, 460)]
    px, py = resolve_popup_position(fake_win, 210, 310, 120, 36, avoid_rects=avoid)
    assert not rects_overlap((px, py, px + 120, py + 36), avoid[0])
