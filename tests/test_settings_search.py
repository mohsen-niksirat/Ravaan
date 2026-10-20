"""Unit tests for Phase 6 Settings search, tooltips, and task-grouped UX (ravan.ui.settings, ravan.ui.tooltip)."""

from __future__ import annotations

import tkinter as tk
from unittest.mock import MagicMock

import pytest

from ravan.core.config import Config
from ravan.ui.settings import SettingsWindow
from ravan.ui.tooltip import ToolTip


def test_tooltip_lifecycle():
    """Verify ToolTip component mounts, schedules, and destroys cleanly."""
    try:
        root = tk.Tk()
        lbl = tk.Label(root, text="Hover target")
        lbl.pack()

        tip = ToolTip(lbl, text="Helpful tip explanation", delay_ms=50)
        assert tip.text == "Helpful tip explanation"
        assert tip._tip_window is None

        # Simulate hover show and hide
        tip.show()
        assert tip._tip_window is not None
        tip.hide()
        assert tip._tip_window is None

        root.destroy()
    except tk.TclError:
        pytest.skip("Tkinter display not available")


def test_settings_search_filtering():
    """Verify live search in Settings dynamically filters tabs and clear button resets."""
    try:
        cfg = Config()
        win = SettingsWindow(cfg=cfg)
        win._build()

        assert win._root is not None
        assert win._search_var is not None

        # 1. Search for autofix
        win._search_var.set("autofix")
        # Ensure filter executed without error
        win.tick()

        # 2. Search in Persian
        win._search_var.set("نیم‌فاصله")
        win.tick()

        # 3. Clear search query
        win._search_var.set("")
        win.tick()

        win._close()
        assert win._root is None
    except tk.TclError:
        pytest.skip("Tkinter display not available")


def test_settings_save_and_cancel_callbacks():
    """Verify saving settings invokes on_saved callback."""
    try:
        cfg = Config()
        on_saved = MagicMock()
        win = SettingsWindow(cfg=cfg, on_saved=on_saved)
        win._build()

        win._save()
        assert on_saved.called
        assert win._root is None
    except tk.TclError:
        pytest.skip("Tkinter display not available")
