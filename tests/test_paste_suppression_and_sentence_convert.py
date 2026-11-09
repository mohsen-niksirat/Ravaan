"""Tests for paste/copy suppression of word prediction and last sentence layout toggle."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ravan.core.config import Config
from ravan.core.journal import KeystrokeJournal
from ravan.platform import winapi as w
from ravan.platform.hook import HookEvent
from ravan.ui.app import RavanApp


def test_journal_last_sentence_span_single_phrase() -> None:
    journal = KeystrokeJournal(maxlen=256)
    for ch in "sghl plndn hv shukn":
        journal.push(ch)

    span, length = journal.last_sentence_span()
    assert span == "sghl plndn hv shukn"
    assert length == len("sghl plndn hv shukn")


def test_journal_last_sentence_span_after_punctuation() -> None:
    journal = KeystrokeJournal(maxlen=256)
    for ch in "جمله قبلی تمام شد. sghl plndn":
        journal.push(ch)

    span, length = journal.last_sentence_span()
    assert span == "sghl plndn"
    assert length == len("sghl plndn")


def test_journal_last_sentence_span_after_persian_question_mark() -> None:
    journal = KeystrokeJournal(maxlen=256)
    for ch in "حالت چطوره؟ sghl":
        journal.push(ch)

    span, length = journal.last_sentence_span()
    assert span == "sghl"
    assert length == 4


def test_journal_last_sentence_span_after_newline() -> None:
    journal = KeystrokeJournal(maxlen=256)
    for ch in "خط اول\nsghl plndn":
        journal.push(ch)

    span, length = journal.last_sentence_span()
    assert span == "sghl plndn"
    assert length == len("sghl plndn")


def test_journal_last_sentence_span_empty() -> None:
    journal = KeystrokeJournal(maxlen=256)
    span, length = journal.last_sentence_span()
    assert span == ""
    assert length == 0


class _MockOverlay:
    def __init__(self) -> None:
        self.visible = False
        self.predicting = False
        self.clipboard_open = False

    def hide(self) -> None:
        self.visible = False
        self.predicting = False

    def show(self, *args, **kwargs) -> None:
        self.visible = True

    def destroy(self) -> None:
        pass

    def tick(self) -> None:
        pass


def test_paste_ctrl_v_suppresses_prediction_and_clears_journal() -> None:
    cfg = Config()
    app = RavanApp(cfg, overlay=_MockOverlay())
    app.journal.push("s")
    app.journal.push("g")
    app.journal.push("h")
    app.journal.push("l")
    app.overlay.visible = True
    app.overlay.predicting = True
    app._pending_predict = True

    # Simulate Ctrl+V key press
    with patch("ravan.platform.keys.modifiers_down") as mock_mods:
        def mods_impl(mods, exact=False):
            return "ctrl" in mods

        mock_mods.side_effect = mods_impl
        event = HookEvent(vk_code=ord("V"), flags=0, scan_code=0, is_key_down=True)
        app._handle_key(event)

    assert app.overlay.visible is False
    assert app._pending_predict is False
    assert len(app.journal.text()) == 0


def test_paste_shift_insert_suppresses_prediction_and_clears_journal() -> None:
    cfg = Config()
    app = RavanApp(cfg, overlay=_MockOverlay())
    app.journal.push("t")
    app.journal.push("e")
    app.journal.push("s")
    app.journal.push("t")
    app.overlay.visible = True
    app._pending_predict = True

    with (
        patch("ravan.platform.keys.modifiers_down", return_value=False),
        patch("ravan.ui.key_handler._is_shift_pressed", return_value=True),
    ):
        event = HookEvent(vk_code=w.VK_INSERT, flags=0, scan_code=0, is_key_down=True)
        app._handle_key(event)

    assert app.overlay.visible is False
    assert app._pending_predict is False
    assert len(app.journal.text()) == 0


def test_copy_ctrl_c_suppresses_prediction_and_preserves_journal() -> None:
    cfg = Config()
    app = RavanApp(cfg, overlay=_MockOverlay())
    app.journal.push("t")
    app.journal.push("e")
    app.journal.push("s")
    app.journal.push("t")
    app.overlay.visible = True
    app._pending_predict = True

    with patch("ravan.platform.keys.modifiers_down") as mock_mods:
        def mods_impl(mods, exact=False):
            return "ctrl" in mods

        mock_mods.side_effect = mods_impl
        event = HookEvent(vk_code=ord("C"), flags=0, scan_code=0, is_key_down=True)
        app._handle_key(event)

    assert app.overlay.visible is False
    assert app._pending_predict is False
    assert app.journal.text() == "test"


def test_cut_ctrl_x_suppresses_prediction_and_clears_journal() -> None:
    cfg = Config()
    app = RavanApp(cfg, overlay=_MockOverlay())
    app.journal.push("t")
    app.journal.push("e")
    app.journal.push("s")
    app.journal.push("t")
    app.overlay.visible = True
    app._pending_predict = True

    with patch("ravan.platform.keys.modifiers_down") as mock_mods:
        def mods_impl(mods, exact=False):
            return "ctrl" in mods

        mock_mods.side_effect = mods_impl
        event = HookEvent(vk_code=ord("X"), flags=0, scan_code=0, is_key_down=True)
        app._handle_key(event)

    assert app.overlay.visible is False
    assert app._pending_predict is False
    assert len(app.journal.text()) == 0


def test_convert_last_sentence_toggle_bidirectional() -> None:
    cfg = Config()
    cfg.convert_scope = "sentence"
    app = RavanApp(cfg, overlay=_MockOverlay())
    app._maybe_switch_keyboard_layout = MagicMock()

    # User typed "sghl llk,k" with English layout intending to type "سلام ممنون"
    for ch in "sghl llk,k":
        app.journal.push(ch)

    with (
        patch("ravan.platform.clipboard.try_convert_selection", return_value=False),
        patch("ravan.ui.app_actions.replace_last_n_with") as mock_replace,
    ):
        # 1. First press: converts last sentence to Persian
        app._convert_selection_or_last_word()
        mock_replace.assert_called_once_with(len("sghl llk,k"), "سلام ممنون")
        assert app.journal.text() == "سلام ممنون"
        app._maybe_switch_keyboard_layout.assert_called_with("fa")

        # 2. Second press within 2 seconds: toggles back to "sghl llk,k"
        mock_replace.reset_mock()
        app._maybe_switch_keyboard_layout.reset_mock()
        app._convert_selection_or_last_word()
        mock_replace.assert_called_once_with(len("سلام ممنون"), "sghl llk,k")
        assert app.journal.text() == "sghl llk,k"
        app._maybe_switch_keyboard_layout.assert_called_with("en")


def test_convert_selection_switches_layout() -> None:
    cfg = Config()
    app = RavanApp(cfg, overlay=_MockOverlay())
    app._maybe_switch_keyboard_layout = MagicMock()

    # Selection conversion returns True and puts Persian text in clipboard
    with (
        patch("ravan.platform.clipboard.try_convert_selection", return_value=True),
        patch("ravan.platform.clipboard.get_clipboard_text", return_value="سلام دوست من"),
    ):
        app._convert_selection_or_last_word()
        app._maybe_switch_keyboard_layout.assert_called_once_with("fa")
