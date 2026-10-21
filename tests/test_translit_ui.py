"""Automated tests for Phase 7: Interactive Candidate Selection, Instant Undo, and UI Settings."""

from __future__ import annotations

import tempfile
from unittest.mock import MagicMock, patch

import pytest

from ravan.core.config import Config, HotkeySpec
from ravan.core.events import Candidate, CandidateKind
from ravan.ui.app import RavanApp


class MockOverlay:
    def __init__(self) -> None:
        self.shown = False
        self.candidates: list[Candidate] = []
        self.on_accept = None

    def show_predictions(self, cands, x, y, height=0, on_accept=None):
        self.shown = True
        self.candidates = cands
        self.on_accept = on_accept

    def hide(self) -> None:
        self.shown = False

    def destroy(self) -> None:
        pass

    def tick(self) -> None:
        pass


@pytest.fixture
def mock_app():
    with patch("ravan.ui.app.KeyboardHook"), patch("ravan.ui.toast.ToastPopup.show"):
        cfg = Config()
        cfg.translit_enabled = True
        cfg.quickpick_digits = True
        overlay = MockOverlay()
        app = RavanApp(cfg, overlay=overlay)
        if hasattr(app, "translit") and app.translit is not None:
            app.translit.user_frequency = {}
            app.translit.user_dict_path = None
        try:
            yield app, overlay
        finally:
            app.stop()


def test_translit_candidate_replacement_safety(mock_app):
    """Verify selecting candidate 2 replaces candidate 1 on screen, not orig_word."""
    app, overlay = mock_app

    # Mock caretaker / winapi injection
    replaced_calls = []

    def mock_replace(old, new, delimiter="", cursor_offset=None):
        replaced_calls.append((old, new, delimiter))

    app._replace_word = mock_replace

    with patch("ravan.platform.caret.get_caret_rect") as mock_caret, \
         patch("ravan.platform.hook.set_popup_visible"):
        mock_caret.return_value = MagicMock(x=100, y=200, height=20)

        # Trigger transliteration for "salam"
        handled = app._maybe_translit_word("salam", delimiter=" ")
        assert handled is True
        assert len(replaced_calls) == 1
        # First insertion: replaced original Finglish "salam" with top candidate "سلام"
        assert replaced_calls[0] == ("salam", "سلام", " ")
        assert overlay.shown is True

        # Now simulate user picking candidate #2 from popup: "سالم"
        cand2 = Candidate(text="سالم", score=0.8, kind=CandidateKind.COMPLETION)
        overlay.on_accept(cand2)

        # Second replacement must replace "سلام" (what was on screen), NOT "salam"!
        assert len(replaced_calls) == 2
        assert replaced_calls[1] == ("سلام", "سالم", " ")


def test_translit_instant_undo_from_backspace(mock_app):
    """Verify immediate Backspace after transliteration reverts text back to Finglish."""
    app, _ = mock_app

    with patch("ravan.platform.inject.replace_last_n_with") as mock_replace:
        handled = app._maybe_translit_word("salam", delimiter=" ")
        assert handled is True

        # Backspace immediately (< 2.5s)
        undo_handled = app._undo_last_correction_from_backspace()
        assert undo_handled is True

        # Verify replacement reverted "سلام " (5 chars: 4 + 1) back to "salam "
        mock_replace.assert_called_once()
        args = mock_replace.call_args[0]
        # Length of "سلام" (4) + delimiter (1) = 5
        assert args[0] == len("سلام") + len(" ")
        assert args[1] == "salam "


def test_translit_global_undo_hotkey(mock_app):
    """Verify global undo (Ctrl+Shift+Z) reverts transliteration."""
    app, _ = mock_app

    with patch("ravan.platform.inject.replace_last_n_with") as mock_replace:
        app._maybe_translit_word("chetori", delimiter=" ")

        # Global undo triggered
        undone = app._undo_last_correction()
        assert undone is True

        mock_replace.assert_called_once()
        args = mock_replace.call_args[0]
        assert args[0] == len("چطوری") + len(" ")
        assert args[1] == "chetori "


def test_translit_settings_persistence():
    """Verify settings window enables/disables translit mode and saves properly."""
    import tkinter as tk

    from ravan.ui.settings import SettingsWindow

    with tempfile.TemporaryDirectory():
        cfg = Config()
        cfg.translit_enabled = False
        cfg.translit_hotkey = HotkeySpec("T", ["Ctrl", "Alt"])

        try:
            root = tk.Tk()
        except (tk.TclError, Exception) as exc:
            pytest.skip(f"Tkinter display not available: {exc}")
        root.withdraw()
        try:
            win = SettingsWindow(cfg, on_saved=lambda c: None)
            win.show()
            win.tick()

            # Check initial state
            assert hasattr(win, "_translit_var")
            assert win._translit_var.get() is False

            assert hasattr(win, "_translit_hotkey_var")
            assert win._translit_hotkey_var.get() == "Ctrl+Alt+T"

            # Toggle on
            win._translit_var.set(True)
            win._save()

            assert win.cfg.translit_enabled is True

            # Reset tab defaults
            with patch("tkinter.messagebox.askyesno", return_value=True):
                win._reset_tab_defaults("general")
                # Default is disabled (safe opt-in default)
                assert win._translit_var.get() is False

            win._close()
        finally:
            root.destroy()
