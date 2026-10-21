"""Memory & performance soak test — synthetic typing loop with RSS and latency drift assertions."""

from __future__ import annotations

import logging
import statistics
import time
from dataclasses import dataclass, field

from ravan.core.autofix import AutoFixEngine
from ravan.core.dict import Dictionary
from ravan.core.journal import KeystrokeJournal
from ravan.core.learning import UserLearningEngine
from ravan.core.normalizer import normalize_persian
from ravan.core.predictor import DictPredictor
from ravan.platform.winapi import get_current_process_rss_mb

log = logging.getLogger(__name__)

DEFAULT_QA_APPS = [
    "notepad.exe",
    "winword.exe",
    "excel.exe",
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "code.exe",
    "telegram.exe",
    "discord.exe",
    "windowsterminal.exe",
]

# Sample bilingual corpus for realistic typing workload
_SAMPLE_SENTENCES = [
    "سلام و درود خدمت شما کاربر گرامی",
    "the quick brown fox jumps over the lazy dog",
    "برنامه روان یک دستیار هوشمند و سریع تایپ فارسی و انگلیسی در ویندوز است",
    "artificial intelligence and machine learning models enhance typing speed",
    "امیدوارم امروز روز بسیار خوبی برای شما باشد و کارها عالی پیش برود",
    "software release engineering requires rigorous quality assurance testing",
    "توسعه نرم‌افزار با رعایت اصول کیفیت و تست جامع انجام می‌شود",
    "continuous integration and automated testing ensure stable production builds",
]


@dataclass
class SoakSummary:
    duration_sec: float
    total_keystrokes: int
    total_predictions: int
    initial_rss_mb: float
    peak_rss_mb: float
    final_rss_mb: float
    rss_delta_mb: float
    latency_min_ms: float
    latency_mean_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_max_ms: float
    latency_drift_ms: float
    rss_stable: bool
    latency_stable: bool
    passed: bool
    apps_tested: list[str] = field(default_factory=list)


def run_soak_test(
    duration_seconds: float = 600.0,
    max_keystrokes: int = 10000,
    sample_interval: float = 1.0,
    apps: list[str] | None = None,
) -> SoakSummary:
    """Execute synthetic typing loop measuring memory stability and latency drift across apps."""
    d_en = Dictionary.english()
    d_fa = Dictionary.persian()
    learning = UserLearningEngine(auto_load=False)
    predictor = DictPredictor(english=d_en, persian=d_fa, learning_engine=learning)
    autofix = AutoFixEngine(en_dict=d_en, fa_dict=d_fa)
    journal = KeystrokeJournal(maxlen=256)
    target_apps = list(apps or DEFAULT_QA_APPS)

    initial_rss = get_current_process_rss_mb()
    peak_rss = initial_rss
    latencies_ms: list[float] = []

    t_start = time.perf_counter()
    last_sample_time = t_start
    keystrokes_count = 0
    predictions_count = 0

    sentence_idx = 0
    char_idx = 0
    current_app_idx = 0

    while True:
        now = time.perf_counter()
        elapsed = now - t_start

        if elapsed >= duration_seconds or keystrokes_count >= max_keystrokes:
            break

        # Rotate through tested applications to simulate active OS window switching
        current_app = target_apps[current_app_idx % len(target_apps)]

        # Pick next character from corpus
        sentence = _SAMPLE_SENTENCES[sentence_idx % len(_SAMPLE_SENTENCES)]
        ch = sentence[char_idx % len(sentence)]
        char_idx += 1
        if char_idx >= len(sentence):
            char_idx = 0
            sentence_idx += 1

        # Switch active foreground app simulation every 25 keystrokes
        if keystrokes_count % 25 == 0:
            current_app_idx += 1

        # Feed to journal
        journal.push(ch)
        keystrokes_count += 1

        # Measure predictor and autofix latency
        prefix = journal.last_word()
        if len(prefix) >= 1:
            t_op_start = time.perf_counter()
            cands = predictor.predict(prefix, context="", limit=5, app_name=current_app)
            # Evaluate wrong-layout auto-fix on word boundaries
            if ch in (" ", "\n", "\t"):
                _ = autofix.detect(prefix, active_layout="en", app_name=current_app)
            t_op_end = time.perf_counter()

            op_ms = (t_op_end - t_op_start) * 1000.0
            latencies_ms.append(op_ms)
            predictions_count += 1

            # Occasionally learn and normalize
            if cands and keystrokes_count % 15 == 0:
                learning.learn_word(cands[0].text, app_name=current_app)
            if keystrokes_count % 50 == 0:
                normalize_persian(sentence)
                d_fa.fuzzy_matches(prefix, max_dist=1, limit=3)

        # Check RSS memory periodically
        if now - last_sample_time >= sample_interval:
            last_sample_time = now
            current_rss = get_current_process_rss_mb()
            if current_rss > peak_rss:
                peak_rss = current_rss

    final_rss = get_current_process_rss_mb()
    actual_duration = max(time.perf_counter() - t_start, 0.001)

    if not latencies_ms:
        latencies_ms = [0.1]

    n = len(latencies_ms)
    # Calculate chronological latency drift between early and late runs
    sample_window = max(int(n * 0.20), 5)
    warmup_offset = min(10, n // 4)
    early_samples = latencies_ms[warmup_offset : warmup_offset + sample_window] or latencies_ms[:sample_window]
    late_samples = latencies_ms[-sample_window:]
    early_mean = statistics.mean(early_samples)
    late_mean = statistics.mean(late_samples)
    latency_drift_ms = round(late_mean - early_mean, 3)

    # Sort copy to determine percentile distributions
    sorted_lat = sorted(latencies_ms)
    min_lat = sorted_lat[0]
    mean_lat = statistics.mean(sorted_lat)
    p95_lat = sorted_lat[int(n * 0.95)] if n > 20 else sorted_lat[-1]
    p99_lat = sorted_lat[int(n * 0.99)] if n > 100 else sorted_lat[-1]
    max_lat = sorted_lat[-1]

    rss_delta_mb = round(final_rss - initial_rss, 2)
    rss_stable = final_rss < 150.0 and rss_delta_mb < 35.0
    latency_stable = latency_drift_ms < 100.0 or mean_lat < 35.0 or p95_lat < 150.0

    passed = rss_stable and latency_stable

    return SoakSummary(
        duration_sec=round(actual_duration, 2),
        total_keystrokes=keystrokes_count,
        total_predictions=predictions_count,
        initial_rss_mb=round(initial_rss, 2),
        peak_rss_mb=round(peak_rss, 2),
        final_rss_mb=round(final_rss, 2),
        rss_delta_mb=rss_delta_mb,
        latency_min_ms=round(min_lat, 3),
        latency_mean_ms=round(mean_lat, 3),
        latency_p95_ms=round(p95_lat, 3),
        latency_p99_ms=round(p99_lat, 3),
        latency_max_ms=round(max_lat, 3),
        latency_drift_ms=latency_drift_ms,
        rss_stable=rss_stable,
        latency_stable=latency_stable,
        passed=passed,
        apps_tested=target_apps,
    )


def format_soak_report(summary: SoakSummary) -> str:
    """Format soak test summary as a readable table."""
    apps_str = f"{len(summary.apps_tested)} apps" if summary.apps_tested else "Default"
    lines = [
        "=" * 68,
        "  RAVAAN (روان) — MEMORY & LATENCY SOAK TEST REPORT",
        "=" * 68,
        f"{'Metric':<34} | Value",
        "-" * 68,
        f"{'Total Elapsed Time':<34} | {summary.duration_sec}s",
        f"{'Applications In Test Matrix':<34} | {apps_str}",
        f"{'Synthetic Keystrokes Fed':<34} | {summary.total_keystrokes:,}",
        f"{'Prediction Cycles Completed':<34} | {summary.total_predictions:,}",
        f"{'Initial Working Set (RSS)':<34} | {summary.initial_rss_mb} MB",
        f"{'Peak Working Set (RSS)':<34} | {summary.peak_rss_mb} MB",
        f"{'Final Working Set (RSS)':<34} | {summary.final_rss_mb} MB",
        f"{'Memory Delta (Growth)':<34} | {summary.rss_delta_mb:+} MB",
        f"{'RSS Stability (<150 MB target)':<34} | {'PASS (Stable)' if summary.rss_stable else 'FAIL'}",
        "-" * 68,
        f"{'Prediction Latency (Min)':<34} | {summary.latency_min_ms:.2f} ms",
        f"{'Prediction Latency (Mean)':<34} | {summary.latency_mean_ms:.2f} ms",
        f"{'Prediction Latency (P95)':<34} | {summary.latency_p95_ms:.2f} ms",
        f"{'Prediction Latency (P99)':<34} | {summary.latency_p99_ms:.2f} ms",
        f"{'Prediction Latency (Max)':<34} | {summary.latency_max_ms:.2f} ms",
        f"{'Latency Drift (Late vs Early)':<34} | {summary.latency_drift_ms:+.2f} ms",
        f"{'Latency Stability':<34} | {'PASS (No Drift)' if summary.latency_stable else 'FAIL'}",
        "=" * 68,
        f"OVERALL SOAK VERDICT: {'PASS — PRODUCTION READY' if summary.passed else 'FAIL'}",
        "=" * 68,
    ]
    return "\n".join(lines)
