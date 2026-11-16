"""Automated soak test asserting stable RSS memory and latency stability."""

from __future__ import annotations

import json
import subprocess
import sys

from ravan.core.soak import SoakSummary, format_soak_report, run_soak_test


def test_soak_test_fast_run():
    """Run a fast synthetic typing loop in an isolated process and assert RSS/latency stability."""
    # Execute in a clean child process so RSS reflects Ravaan's own runtime footprint
    # rather than accumulated Tkinter/Pillow allocations from hundreds of earlier UI tests.
    script = (
        "import dataclasses, json; "
        "from ravan.core.soak import run_soak_test; "
        "s = run_soak_test(duration_seconds=1.5, max_keystrokes=200, sample_interval=0.5); "
        "print(json.dumps(dataclasses.asdict(s)))"
    )
    res = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
    summary = SoakSummary(**json.loads(res.stdout.strip().splitlines()[-1]))

    assert summary.total_keystrokes > 0
    assert summary.total_predictions > 0
    assert summary.final_rss_mb < 150.0
    assert summary.rss_delta_mb < 35.0
    assert summary.rss_stable is True
    assert summary.latency_stable is True
    assert summary.passed is True

    report = format_soak_report(summary)
    assert "RAVAAN (روان) — MEMORY & LATENCY SOAK TEST REPORT" in report
    assert "PASS — PRODUCTION READY" in report

    # Also exercise run_soak_test directly in-process for delta/latency & coverage
    in_proc = run_soak_test(duration_seconds=0.5, max_keystrokes=120, sample_interval=0.25)
    assert in_proc.total_keystrokes > 0
    assert in_proc.rss_delta_mb < 35.0
    assert in_proc.latency_stable is True
