"""Smoke test — imports every module, instantiates core classes without GUI, and measures hook latency."""

from __future__ import annotations

import importlib
import sys
import time
from unittest.mock import patch


def test_import_all_core_modules():
    core_modules = [
        "ravan",
        "ravan.__main__",
        "ravan.cli",
        "ravan.core",
        "ravan.core.calc",
        "ravan.core.cliphistory",
        "ravan.core.config",
        "ravan.core.dict",
        "ravan.core.events",
        "ravan.core.jalali",
        "ravan.core.journal",
        "ravan.core.layout",
        "ravan.core.learning",
        "ravan.core.normalizer",
        "ravan.core.num2words",
        "ravan.core.predictor",
        "ravan.core.snippet",
        "ravan.core.transform",
        "ravan.core.user_dict",
        "ravan.core.zwnj",
    ]
    for mod in core_modules:
        m = importlib.import_module(mod)
        assert m is not None


def test_import_platform_and_ui_modules():
    if sys.platform != "win32":
        return

    win_modules = [
        "ravan.platform",
        "ravan.platform.winapi",
        "ravan.platform.keys",
        "ravan.platform.inject",
        "ravan.platform.hook",
        "ravan.platform.focus",
        "ravan.platform.lang",
        "ravan.platform.clipboard",
        "ravan.platform.singleinstance",
        "ravan.platform.sound",
        "ravan.platform.startup",
        "ravan.ui",
        "ravan.ui.log_setup",
        "ravan.ui.tray",
        "ravan.ui.overlay",
        "ravan.ui.settings",
        "ravan.ui.settings_builder",
        "ravan.ui.snippet_editor",
        "ravan.ui.diagnostics",
        "ravan.ui.key_handler",
        "ravan.ui.app_actions",
        "ravan.ui.app_polling",
        "ravan.ui.app",
    ]
    for mod in win_modules:
        m = importlib.import_module(mod)
        assert m is not None


def test_instantiate_core_classes_no_gui():
    from ravan.core.cliphistory import ClipboardHistory
    from ravan.core.config import Config
    from ravan.core.dict import Dictionary
    from ravan.core.jalali import JalaliDate
    from ravan.core.journal import KeystrokeJournal
    from ravan.core.layout import LayoutMapper
    from ravan.core.learning import UserLearningEngine
    from ravan.core.predictor import DictPredictor
    from ravan.core.snippet import SnippetEngine

    # 1. Config
    cfg = Config()
    assert cfg.convert_hotkey.key == "F12"

    # 2. LayoutMapper
    mapper = LayoutMapper()
    assert mapper.convert_word("o,vn") == "خورد"

    # 3. KeystrokeJournal
    journal = KeystrokeJournal()
    for ch in "test ":
        journal.push(ch)
    assert journal.last_word(allow_trailing_spaces=True) == "test"
    journal.clear()
    assert journal.text() == ""

    # 4. ClipboardHistory
    clip = ClipboardHistory(maxlen=10)
    assert clip.add("hello") is True
    assert clip.add("hello") is False  # dedupe top
    assert len(clip.items()) == 1

    # 5. JalaliDate
    j = JalaliDate.today()
    assert j.year >= 1400

    # 6. LearningEngine
    learning = UserLearningEngine(auto_load=False)
    learning.learn_word("آزمایش")
    assert learning.get_word_boost("آزمایش") >= 1.0

    # 7. SnippetEngine
    snippets = SnippetEngine([])
    expanded = snippets.expand("/today")
    assert expanded is not None

    # 8. Predictor
    en_dict = Dictionary.english()
    fa_dict = Dictionary.persian()
    pred = DictPredictor(english=en_dict, persian=fa_dict, learning_engine=learning)
    cands = pred.predict("سلام", "", 3)
    assert len(cands) >= 1
    assert any("سلام" in c.text for c in cands)



def test_hook_callback_non_blocking_latency():
    """Verify that hook callback executes in under 1 ms."""
    if sys.platform != "win32":
        return

    from ravan.platform import winapi as w
    from ravan.platform.hook import KeyboardHook

    hook = KeyboardHook()
    struct_bytes = w.KBDLLHOOKSTRUCT(
        vkCode=0x41, scanCode=0x1E, flags=0, time=0, dwExtraInfo=0
    )
    import ctypes

    l_param = ctypes.addressof(struct_bytes)

    with patch.object(w.user32, "CallNextHookEx", return_value=0):
        # Warmup
        hook._callback(w.HC_ACTION, w.WM_KEYDOWN, l_param)

        times: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter()
            hook._callback(w.HC_ACTION, w.WM_KEYDOWN, l_param)
            t1 = time.perf_counter()
            times.append(t1 - t0)

        # Drain events so queue doesn't stay full
        while hook.poll() is not None:
            pass

        median_time_ms = sorted(times)[len(times) // 2] * 1000
        # Must execute far below 1 millisecond
        assert median_time_ms < 1.0, f"Hook callback median latency too high: {median_time_ms:.3f} ms"
