"""Automated soak test asserting stable RSS memory and latency stability."""

from __future__ import annotations

from ravan.core.soak import format_soak_report, run_soak_test


def test_soak_test_fast_run():
    """Run a fast synthetic typing loop and assert stable RSS and latency stability."""
    # Run 1.5 seconds / 200 keystrokes for fast automated test run
    summary = run_soak_test(duration_seconds=1.5, max_keystrokes=200, sample_interval=0.5)

    assert summary.total_keystrokes > 0
    assert summary.total_predictions > 0
    assert summary.final_rss_mb < 150.0
    assert summary.rss_stable is True
    assert summary.latency_stable is True
    assert summary.passed is True

    report = format_soak_report(summary)
    assert "RAVAAN (روان) — MEMORY & LATENCY SOAK TEST REPORT" in report
    assert "PASS — PRODUCTION READY" in report
