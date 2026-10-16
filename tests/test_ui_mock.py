"""Unit tests for ravan/ui modules with mocks and helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from ravan.core.config import Config, Snippet
from ravan.core.events import Candidate, CandidateKind
from ravan.ui.diagnostics import DiagnosticsWindow
from ravan.ui.overlay import OverlayWindow
from ravan.ui.settings import SettingsWindow
from ravan.ui.snippet_editor import SnippetEditorWindow


def test_overlay_rgb():
    assert OverlayWindow._rgb([255, 255, 255]) == "#ffffff"
    assert OverlayWindow._rgb([0, 0, 0]) == "#000000"
    assert OverlayWindow._rgb([255, 128, 0]) == "#ff8000"
    assert OverlayWindow._rgb([16, 32, 48]) == "#102030"


def test_overlay_row_text_formatting():
    c_comp = Candidate(text="سلام", score=0.9, kind=CandidateKind.COMPLETION)
    row_selected = OverlayWindow._row_text(None, 0, c_comp, selected=True)
    assert row_selected == "▶ 1  سلام"

    row_unselected = OverlayWindow._row_text(None, 1, c_comp, selected=False)
    assert row_unselected == "   2  سلام"

    c_auto = Candidate(text="خورد", score=1.0, kind=CandidateKind.AUTOCORRECT)
    row_auto = OverlayWindow._row_text(None, 2, c_auto, selected=False)
    assert row_auto == "   3  خورد  ≈"

    c_next = Candidate(text="عزیز", score=0.9, kind=CandidateKind.NEXT_WORD)
    row_next = OverlayWindow._row_text(None, 0, c_next, selected=True)
    assert row_next == "▶ 1  عزیز  [بعدی]"


def test_snippet_editor_isolation():
    initial_snippets = [Snippet(trigger="@@", replacement="test@test.com")]
    editor = SnippetEditorWindow(initial_snippets, on_saved=MagicMock())

    # Modifying the original input list must not affect editor.snippets (deepcopy check)
    initial_snippets.append(Snippet(trigger="!!", replacement="alert"))
    assert len(editor.snippets) == 1
    assert editor.open is False

    editor.show()
    assert editor.open is True


def test_snippet_editor_save_dispatches_callback():
    saved_snippets: list[Snippet] = []

    def fake_on_saved(snips: list[Snippet]) -> None:
        saved_snippets.extend(snips)

    editor = SnippetEditorWindow(
        [Snippet(trigger="hi", replacement="hello")],
        on_saved=fake_on_saved,
    )
    editor.snippets.append(Snippet(trigger="bye", replacement="goodbye"))
    editor.on_saved(editor.snippets)

    assert len(saved_snippets) == 2
    assert saved_snippets[0].trigger == "hi"
    assert saved_snippets[1].trigger == "bye"


def test_settings_window_build_and_state():
    import tkinter as tk

    cfg = Config()
    saved = []
    root = tk.Tk()
    root.withdraw()
    try:
        sw = SettingsWindow(cfg, on_saved=lambda c: saved.append(c))
        assert sw.open is False
        sw.show()
        assert sw.open is True
        assert len(sw._managed_snippets) == len(cfg.snippets)

        # Verify build does not fail or raise
        sw._build()
        assert sw._root is not None
        sw._close()
        assert sw._root is None
        assert sw.open is False
    finally:
        root.destroy()


def test_diagnostics_window_state():
    sample_snapshot = {
        "version": "0.4.0",
        "hook_active": True,
        "foreground_exe": "code.exe",
        "foreground_pid": 1234,
        "window_title": "Editor",
        "is_excluded": False,
        "layout": "fa-IR (Persian)",
        "caret_source": "UIA",
        "caret_pos": "(100, 200)",
        "recent_events": [],
    }
    diag = DiagnosticsWindow(snapshot_fn=lambda: sample_snapshot)
    assert diag.open is False
    diag.show()
    assert diag.open is True
    assert diag.snapshot_fn()["version"] == "0.4.0"
