"""Unit tests for Phase 6 Enhanced First-Run Onboarding Wizard (ravan.ui.wizard)."""

from __future__ import annotations

import tkinter as tk
from unittest.mock import MagicMock

import pytest

from ravan.core.config import Config
from ravan.ui.wizard import FirstRunWizard, apply_preset


def test_apply_preset_configurations():
    """Verify presets properly configure application features."""
    cfg = Config()

    # Simple preset
    apply_preset(cfg, "simple")
    assert cfg.word_prediction_enabled is False
    assert cfg.next_word_prediction is False
    assert cfg.autofix_wrong_layout is False
    assert cfg.auto_zwnj is True
    assert cfg.fix_punctuation is True
    assert cfg.clipboard_history_enabled is False
    assert cfg.inline_calc_enabled is False

    # Standard preset (Recommended)
    apply_preset(cfg, "standard")
    assert cfg.word_prediction_enabled is True
    assert cfg.next_word_prediction is False
    assert cfg.autofix_wrong_layout is True
    assert cfg.auto_zwnj is True
    assert cfg.fix_punctuation is True

    # Power user preset
    apply_preset(cfg, "power")
    assert cfg.word_prediction_enabled is True
    assert cfg.next_word_prediction is True
    assert cfg.autofix_wrong_layout is True
    assert cfg.clipboard_history_enabled is True
    assert cfg.inline_calc_enabled is True


def test_wizard_navigation_and_step_flow():
    """Verify 3-step navigation flow: step 1 -> step 2 -> step 3 -> completion."""
    try:
        cfg = Config()
        on_done = MagicMock()
        wiz = FirstRunWizard(cfg=cfg, on_complete=on_done)
        wiz._build()

        assert wiz._step == 1
        assert wiz._root is not None

        # Advance to step 2 (Hotkeys)
        wiz._next_step()
        assert wiz._step == 2

        # Advance to step 3 (Demo)
        wiz._next_step()
        assert wiz._step == 3

        # Step 3 cannot advance further
        wiz._next_step()
        assert wiz._step == 3

        # Back to step 2
        wiz._prev_step()
        assert wiz._step == 2

        # Forward to step 3 and finish
        wiz._next_step()
        wiz._close(completed=True)

        assert wiz._root is None
        assert cfg.has_seen_onboarding is True
        assert on_done.called
    except tk.TclError:
        pytest.skip("Tkinter display not available")


def test_wizard_demo_typing_simulation():
    """Verify the 30-second interactive typing demo triggers auto-fix and ZWNJ."""
    try:
        cfg = Config()
        wiz = FirstRunWizard(cfg=cfg)
        wiz._build()
        wiz._step = 3
        wiz._render_step()

        assert wiz._demo_entry is not None
        assert wiz._demo_badge is not None

        # Simulate typing 'sghl '
        wiz._demo_entry.insert(0, "sghl ")
        wiz._on_demo_typing(None)

        # Must auto-convert to 'سلام '
        assert "سلام " in wiz._demo_entry.get()
        assert "Layout Converted" in wiz._demo_badge.cget("text") or "اصلاح شد" in wiz._demo_badge.cget("text")

        # Simulate typing 'می '
        wiz._demo_entry.delete(0, tk.END)
        wiz._demo_entry.insert(0, "می ")
        wiz._on_demo_typing(None)

        # Must insert ZWNJ: 'می‌'
        assert wiz._demo_entry.get() == "می\u200c"
        assert "ZWNJ" in wiz._demo_badge.cget("text") or "نیم‌فاصله" in wiz._demo_badge.cget("text")

        wiz._close(completed=False)
    except tk.TclError:
        pytest.skip("Tkinter display not available")


def test_wizard_preset_selection_persists():
    """Verify selecting Power user preset in wizard saves to config upon finish."""
    try:
        cfg = Config()
        wiz = FirstRunWizard(cfg=cfg)
        wiz._build()

        # Select power user preset
        wiz._preset_var.set("power")
        wiz._convert_hk_var.set("Alt+L")

        wiz._close(completed=True)

        assert cfg.has_seen_onboarding is True
        assert cfg.clipboard_history_enabled is True
        assert cfg.next_word_prediction is True
        assert cfg.convert_hotkey.key == "Alt+L"
    except tk.TclError:
        pytest.skip("Tkinter display not available")
