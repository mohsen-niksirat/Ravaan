"""Automated CI Quality Gate: Layout Auto-Detection Accuracy & Safety Test (Phase 2).

Enforces:
1. False-Positive Rate < 0.100% on the realistic 594-token corpus (strict 0.000%).
2. Detection Precision >= 98.00% on mixed EN/FA test sets.
3. Detection Recall >= 90.00%.
"""

from __future__ import annotations

from pathlib import Path

from ravan.core.autofix import AutoFixEngine
from ravan.core.dict import Dictionary
from scripts.check_layout_autodetect import (
    run_accuracy_evaluation,
    run_false_positive_evaluation,
)


def test_layout_autodetect_ci_quality_gate():
    corpus_path = Path(__file__).resolve().parent / "data" / "false_positive_corpus.json"
    assert corpus_path.is_file(), f"Corpus not found at {corpus_path}"

    en_dict = Dictionary.english()
    fa_dict = Dictionary.persian()
    engine = AutoFixEngine(en_dict=en_dict, fa_dict=fa_dict, mode="safe")

    # 1. False Positive Rate Gate
    total_tokens, false_positives, fp_details = run_false_positive_evaluation(
        engine, corpus_path
    )
    assert total_tokens > 500, f"Expected > 500 tokens, got {total_tokens}"
    fpr = (false_positives / total_tokens) * 100.0

    error_summary = "\n".join(
        f"  [{d['category']}] '{d['token']}' -> '{d['converted_to']}' ({d['target_lang']})"
        for d in fp_details
    )
    assert fpr < 0.10, (
        f"False-positive rate {fpr:.3f}% exceeds target limit (< 0.100%).\n"
        f"Errors:\n{error_summary}"
    )

    # 2. Accuracy Gate (Precision & Recall)
    tp, fp, fn, precision, recall = run_accuracy_evaluation(
        engine, en_dict, fa_dict, sample_size=75
    )
    assert precision >= 0.98, f"Precision {precision * 100.0:.2f}% < 98.00%"
    assert recall >= 0.90, f"Recall {recall * 100.0:.2f}% < 90.00%"
