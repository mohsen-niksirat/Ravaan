"""Automated CI Quality Gate: Autocorrect False-Positive Rate Test.

Ensures that Ravaan's safe autocorrect does not wrongly mutate valid text
across formal Persian, chat Persian, mixed FA/EN, and code snippets.
Target: FPR < 0.1% (strictly enforced in CI).
"""

from __future__ import annotations

from pathlib import Path

from scripts.check_false_positives import run_benchmark


def test_autocorrect_false_positive_rate_ci_gate():
    corpus_path = Path(__file__).resolve().parent / "data" / "false_positive_corpus.json"
    assert corpus_path.is_file(), f"Corpus not found at {corpus_path}"

    total_tokens, false_positives, details = run_benchmark(corpus_path)
    assert total_tokens > 500, f"Expected at least 500 tokens in corpus, got {total_tokens}"

    fpr = (false_positives / total_tokens) * 100.0
    error_summary = "\n".join(
        f"  [{d['category']}] '{d['original']}' -> '{d['corrected']}' ({d['lang']})"
        for d in details
    )

    assert fpr < 0.1, (
        f"False-positive rate {fpr:.3f}% exceeds target limit (< 0.100%).\n"
        f"False positive detections:\n{error_summary}"
    )
