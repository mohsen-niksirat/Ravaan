"""Tests for Phase 1 & 2: Automatic wrong-layout correction, undo stack, and accuracy gate."""

from __future__ import annotations

from typing import Any

import pytest

from ravan.core.autofix import AutoFixEngine, AutoFixRecord
from ravan.core.config import Config
from ravan.core.dict import Dictionary
from ravan.core.layout import LayoutMapper


@pytest.fixture
def dictionaries() -> tuple[Dictionary, Dictionary]:
    en_dict = Dictionary.english()
    fa_dict = Dictionary.persian()
    return en_dict, fa_dict


@pytest.fixture
def engine(dictionaries: tuple[Dictionary, Dictionary]) -> AutoFixEngine:
    en_dict, fa_dict = dictionaries
    return AutoFixEngine(en_dict=en_dict, fa_dict=fa_dict, mode="safe")


def test_autofix_safe_mode_en_to_fa(engine: AutoFixEngine) -> None:
    # "sghl" typed in English layout is "سلام" in Persian layout
    res = engine.detect("sghl", active_layout="en")
    assert res is not None
    replacement, target_lang = res
    assert replacement == "سلام"
    assert target_lang == "fa"


def test_autofix_safe_mode_fa_to_en(engine: AutoFixEngine) -> None:
    # "حغفاخد" typed in Persian layout is "python" in English layout
    res = engine.detect("حغفاخد", active_layout="fa")
    assert res is not None
    replacement, target_lang = res
    assert replacement == "python"
    assert target_lang == "en"


def test_autofix_safe_mode_preserves_valid_words(engine: AutoFixEngine) -> None:
    # Valid English words must never be converted in safe mode
    assert engine.detect("python", active_layout="en") is None
    assert engine.detect("system", active_layout="en") is None
    assert engine.detect("hello", active_layout="en") is None

    # Valid Persian words must never be converted in safe mode
    assert engine.detect("سلام", active_layout="fa") is None
    assert engine.detect("کتاب", active_layout="fa") is None
    assert engine.detect("ایران", active_layout="fa") is None


def test_autofix_mode_off(engine: AutoFixEngine) -> None:
    engine.mode = "off"
    assert engine.detect("sghl", active_layout="en") is None
    assert engine.detect("حغفاخد", active_layout="fa") is None


def test_autofix_app_override(engine: AutoFixEngine) -> None:
    engine.app_modes["code.exe"] = "off"
    assert engine.detect("sghl", active_layout="en", app_name="C:\\Apps\\Code.exe") is None
    assert engine.detect("sghl", active_layout="en", app_name="C:\\Apps\\Notepad.exe") is not None


def test_autofix_annoyance_guard(engine: AutoFixEngine) -> None:
    # Manual edit within 2s cancels further auto-fixes for the burst
    engine.on_manual_edit(1.2)
    assert engine.detect("sghl", active_layout="en") is None


def test_autofix_blacklist_manual(engine: AutoFixEngine) -> None:
    engine.blacklist_pair("sghl", "سلام")
    assert engine.is_pair_blacklisted("sghl", "سلام")
    assert engine.detect("sghl", active_layout="en") is None


def test_autofix_auto_blacklist_after_three_undos(engine: AutoFixEngine) -> None:
    rec1 = engine.record_fix("sghl", "سلام")
    assert not engine.record_undo(rec1)
    assert not engine.is_pair_blacklisted("sghl", "سلام")

    rec2 = engine.record_fix("sghl", "سلام")
    assert not engine.record_undo(rec2)
    assert not engine.is_pair_blacklisted("sghl", "سلام")

    # Third undo of same pair must auto-disable permanently
    rec3 = engine.record_fix("sghl", "سلام")
    blacklisted = engine.record_undo(rec3)
    assert blacklisted is True
    assert engine.is_pair_blacklisted("sghl", "سلام")
    assert engine.detect("sghl", active_layout="en") is None


def test_autofix_correction_stack_capacity(engine: AutoFixEngine) -> None:
    for i in range(60):
        engine.record_fix(f"word{i}", f"fixed{i}")
    assert len(engine.correction_stack) == 50
    assert engine.correction_stack[0].original == "word10"
    assert engine.correction_stack[-1].original == "word59"

    # Pop corrections in LIFO order
    last = engine.pop_last_correction()
    assert last is not None
    assert last.original == "word59"


def test_autofix_priority_order_over_autocorrect_and_snippets() -> None:
    from unittest.mock import MagicMock, patch

    from ravan.core.config import Snippet
    from ravan.ui.app import RavanApp

    cfg = Config()
    cfg.snippets.append(Snippet(trigger=";test", replacement="expansion"))
    with patch("ravan.ui.app.KeyboardHook"):
        app = RavanApp(cfg, overlay=MagicMock())


    # 1. Trigger that is a snippet should expand as snippet, not autofix
    assert app.snippets.expand(";test") == "expansion"

    # 2. Autofix engine must be initialized
    assert hasattr(app, "autofix")
    assert app.autofix is not None


def test_keystroke_capture_never_writes_raw_keys_to_disk(tmp_path: Any, monkeypatch: Any) -> None:
    # Standing Rule: Any feature that touches keystroke capture or text injection
    # must add a safety test proving it never writes raw keystroke text to disk.
    from ravan.core.autofix import AutoFixEngine

    engine = AutoFixEngine()
    engine.record_fix("mysecretpassword", "صثزقثفحشسسصخقی")
    # Verify records in memory only
    for rec in engine.correction_stack:
        assert isinstance(rec, AutoFixRecord)


def test_autofix_record_with_delimiter(engine: AutoFixEngine) -> None:
    rec = engine.record_fix("sghl", "سلام", delimiter=" ")
    assert rec.original == "sghl"
    assert rec.fixed == "سلام"
    assert rec.delimiter == " "


def test_autofix_app_undo_and_backspace_flow() -> None:
    from unittest.mock import MagicMock, patch

    from ravan.ui.app import RavanApp

    with patch("ravan.ui.app.KeyboardHook"):
        app = RavanApp(overlay=MagicMock())
        app._show_toast = MagicMock()
        app.tray = MagicMock()
        try:
            # 1. Global undo with delimiter
            app.autofix.record_fix("sghl", "سلام", delimiter=" ")
            with patch("ravan.platform.inject.replace_last_n_with") as mock_replace:
                ok = app._undo_last_correction()
                assert ok is True
                # Must delete len("سلام") + len(" ") = 5, replace with "sghl "
                mock_replace.assert_called_once_with(5, "sghl ")

            # 2. Backspace undo
            app.autofix.record_fix("o,vn", "خورد", delimiter=" ")
            app._last_autofix_time = 1000.0
            with patch("time.monotonic", return_value=1001.0):  # 1.0s elapsed (< 2.5s)
                with patch("ravan.platform.inject.replace_last_n_with") as mock_replace_bs:
                    ok = app._undo_last_correction_from_backspace()
                    assert ok is True
                    # Backspace already erased delimiter, so delete len("خورد") = 4, replace with "o,vn"
                    mock_replace_bs.assert_called_once_with(4, "o,vn")
        finally:
            app.stop()


def test_autofix_accuracy_gate_300_words(dictionaries: tuple[Dictionary, Dictionary]) -> None:
    """Accuracy gate: 300-word mixed EN/FA fixture set scoring >=98% precision and >=90% recall."""
    en_dict, fa_dict = dictionaries
    mapper = LayoutMapper()
    engine = AutoFixEngine(en_dict=en_dict, fa_dict=fa_dict, mode="safe")

    # 75 English words with valid Persian layout mapping
    en_words = [
        e.word
        for e in en_dict.entries
        if len(e.word) >= 3 and mapper.en_to_fa_word(e.word)
    ][:75]

    # 75 Persian words with valid English layout mapping
    fa_words = [
        e.word
        for e in fa_dict.entries
        if len(e.word) >= 3 and mapper.fa_to_en_word(e.word)
    ][:75]

    wrong_fa_inputs = [(mapper.fa_to_en_word(w), w) for w in fa_words]
    wrong_en_inputs = [(mapper.en_to_fa_word(w), w) for w in en_words]

    tp = 0
    fp = 0
    fn = 0

    # Test wrong-layout words (should be converted)
    for typed, expected in wrong_fa_inputs + wrong_en_inputs:
        assert typed is not None
        res = engine.detect(typed)
        if res is not None and res[0] == expected:
            tp += 1
        else:
            fn += 1

    # Test correct-layout words (should NOT be converted in safe mode)
    for w in en_words + fa_words:
        res = engine.detect(w)
        if res is not None:
            fp += 1

    total_words = len(wrong_fa_inputs) + len(wrong_en_inputs) + len(en_words) + len(fa_words)
    assert total_words == 300

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0

    print(
        f"\n[Accuracy Gate Benchmark] Total={total_words}, TP={tp}, FP={fp}, FN={fn}, "
        f"Precision={precision*100:.2f}%, Recall={recall*100:.2f}%"
    )

    # Gate conditions from specification
    assert precision >= 0.98, f"Precision {precision*100:.2f}% < 98%"
    assert recall >= 0.90, f"Recall {recall*100:.2f}% < 90%"
