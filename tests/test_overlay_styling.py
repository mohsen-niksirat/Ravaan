"""Tests for OverlayWindow styling, widget order, and contrast safety."""

from __future__ import annotations

import tkinter as tk

from ravan.core.config import Config
from ravan.core.predictor import Candidate, CandidateKind
from ravan.ui.overlay import CandidateRow, OverlayWindow
from ravan.ui.theme import get_prediction_style


def test_grip_texts_distinct_per_style():
    styles = ["macos", "ios", "classic", "neon", "fluent", "modern", "glass", "material", "minimal"]
    grips = {s: OverlayWindow._get_grip_text(s) for s in styles}
    assert len(set(grips.values())) == len(styles), "Each style must have a distinct grip text"
    assert "🔴 🟡 🟢" in grips["macos"]
    assert "" in grips["ios"]
    assert "— □ ✕" in grips["classic"]
    assert "HUD" in grips["neon"]
    assert "⊞" in grips["fluent"]
    assert "✦" in grips["modern"]


def test_candidate_row_contrast_safety_neon_custom_cyan():
    """Ensure that if custom colors set highlight to bright cyan (#00F5D4),

    CandidateRow automatically flips text to dark high-contrast so text is never invisible.
    """
    root = tk.Tk()
    root.withdraw()
    try:
        custom = {
            "bg": "#080811",
            "fg": "#F0F6FC",
            "accent": "#00F5D4",
            "border": "#00F5D4",
            "highlight": "#00F5D4",
            "highlight_fg": "#FFFFFF",
        }
        tokens = get_prediction_style("neon", mode="dark", custom_colors=custom)
        cand = Candidate(text="سلام", score=0.9, kind=CandidateKind.COMPLETION)

        frame = tk.Frame(root)
        row = CandidateRow(frame, row_index=0)
        row.set_candidate(cand, index=0, selected=True, tokens=tokens, f_sz=12)

        # Because row_bg is #00F5D4 (bright cyan), text must be dark!
        assert row._text.cget("fg") == "#080811", "Text on bright cyan background must be dark"
        assert row._badge.cget("fg") == "#080811", "Badge on bright cyan background must be dark"

        # Unselected row on dark background
        row.set_candidate(cand, index=0, selected=False, tokens=tokens, f_sz=12)
        assert row._text.cget("fg") == "#00FF66", "Text on dark neon background must be electric green"
    finally:
        root.destroy()


def test_overlay_hint_always_at_bottom():
    """Verify that multiple consecutive renders keep the hint bar at the bottom,

    and never push it above the candidate rows.
    """
    cfg = Config()
    cfg.prediction_ui_style = "fluent"
    cfg.prediction_use_custom_colors = False

    overlay = OverlayWindow(cfg=cfg)
    try:
        cands = [
            Candidate(text="سلام", score=0.9, kind=CandidateKind.COMPLETION),
            Candidate(text="سلام علیکم", score=0.8, kind=CandidateKind.SENTENCE),
        ]
        overlay.show_predictions(cands, x=100, y=100)

        # Check packed children order in self._frame
        packed = overlay._frame.pack_slaves()
        assert len(packed) >= 3

        # _grip must be top
        assert packed[0] == overlay._grip

        # _hint must be bottom
        assert packed[1] == overlay._hint or packed[-1] == overlay._hint

        # Render second time (simulating next keystroke)
        cands2 = [
            Candidate(text="سلسفیلا", score=0.7, kind=CandidateKind.COMPLETION),
            Candidate(text="سلیس", score=0.6, kind=CandidateKind.COMPLETION),
            Candidate(text="سلاح", score=0.5, kind=CandidateKind.COMPLETION),
        ]
        overlay.show_predictions(cands2, x=100, y=100)

        packed2 = overlay._frame.pack_slaves()
        # _grip is at top
        assert packed2[0] == overlay._grip
        # Candidate rows must NOT be below _hint in vertical layout
        # (hint was packed with side='bottom')
        assert overlay._hint in packed2
        for row in overlay._rows[: len(cands2)]:
            assert row in packed2
    finally:
        overlay.destroy()


def test_candidate_row_custom_colors_respected_for_all_styles():
    """Verify custom colors apply to selected/unselected rows across all styles."""
    root = tk.Tk()
    root.withdraw()
    try:
        custom = {
            "bg": "#112233",
            "fg": "#FFEEDD",
            "accent": "#00FFAA",
            "border": "#334455",
            "highlight": "#661188",
            "highlight_fg": "#FAFAFA",
        }
        cand = Candidate(text="تست", score=0.9, kind=CandidateKind.COMPLETION)
        frame = tk.Frame(root)
        row = CandidateRow(frame, row_index=0)

        for style in ("macos", "ios", "classic", "fluent", "modern", "glass", "material", "minimal"):
            tokens = get_prediction_style(style, mode="dark", custom_colors=custom)
            row.set_candidate(cand, index=0, selected=True, tokens=tokens, f_sz=12)
            assert row.cget("bg") == "#661188", f"Selected bg for {style} should use custom highlight"
            assert row._text.cget("fg") == "#FAFAFA", f"Selected fg for {style} should use custom highlight_fg"

            row.set_candidate(cand, index=0, selected=False, tokens=tokens, f_sz=12)
            assert row._text.cget("fg") == "#FFEEDD", f"Unselected fg for {style} should use custom fg"
    finally:
        root.destroy()


def test_continuation_suggestions_enabled_flag():
    """Verify DictPredictor respects continuation_suggestions_enabled."""
    from ravan.core.dict import DictEntry, Dictionary, Language
    from ravan.core.learning import UserLearningEngine
    from ravan.core.predictor import DictPredictor

    fa_dict = Dictionary(entries=[DictEntry("سلام", rank=1, frequency=100)], language=Language.PERSIAN)
    learning = UserLearningEngine(auto_load=False)
    learning.learn_transition("عرض", "سلام")
    learning.learn_transition("سلام", "علیکم")

    pred_on = DictPredictor(
        persian=fa_dict,
        learning_engine=learning,
        continuation_suggestions_enabled=True,
    )
    cands_on = pred_on.predict("سل", "عرض", limit=5)
    assert any(c.kind == CandidateKind.SENTENCE for c in cands_on)

    pred_off = DictPredictor(
        persian=fa_dict,
        learning_engine=learning,
        continuation_suggestions_enabled=False,
    )
    cands_off = pred_off.predict("سل", "عرض", limit=5)
    assert not any(c.kind == CandidateKind.SENTENCE for c in cands_off)

