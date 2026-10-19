"""Baseline performance benchmark script for Ravaan.

Measures:
1. Cold start time (subprocess python -m ravan --version).
2. Module import & initialization latency.
3. Idle Working Set / RSS RAM in MB.
4. Hook callback event dispatch latency.
5. Prediction query latency (p50, p95, p99).
6. Auto wrong-layout detection latency.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def measure_cold_start() -> float:
    """Measure CLI cold startup time in milliseconds via subprocess."""
    t0 = time.perf_counter()
    res = subprocess.run(
        [sys.executable, "-m", "ravan", "--version"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        check=False,
    )
    t1 = time.perf_counter()
    if res.returncode != 0:
        raise RuntimeError(f"Cold start subprocess failed: {res.stderr}")
    return (t1 - t0) * 1000.0


def measure_import_and_init() -> tuple[float, float, float]:
    """Measure in-process import time, config load time, and predictor initialization time."""
    t0 = time.perf_counter()
    import ravan.core.config as cfg_mod
    import ravan.core.predictor as pred_mod
    import ravan.platform.winapi as wapi

    t1 = time.perf_counter()
    _ = cfg_mod.load_config()
    t2 = time.perf_counter()

    from ravan.core.dict import Dictionary
    from ravan.core.learning import UserLearningEngine

    en_dict = Dictionary.english()
    fa_dict = Dictionary.persian()
    learn = UserLearningEngine(auto_load=False)
    _predictor = pred_mod.DictPredictor(
        english=en_dict,
        persian=fa_dict,
        learning_engine=learn,
    )
    t3 = time.perf_counter()

    rss_mb = wapi.get_current_process_rss_mb()
    import_ms = (t1 - t0) * 1000.0
    config_ms = (t2 - t1) * 1000.0
    init_ms = (t3 - t2) * 1000.0

    return import_ms + config_ms + init_ms, rss_mb, (t3 - t0) * 1000.0


def measure_hook_latency(iterations: int = 5000) -> dict[str, float]:
    """Measure synthetic keyboard hook callback dispatch latency."""
    import ctypes

    from ravan.platform import winapi as w
    from ravan.platform.hook import KeyboardHook

    hook = KeyboardHook()
    kb = w.KBDLLHOOKSTRUCT()
    kb.vkCode = 65
    kb.scanCode = 30
    kb.flags = 0
    kb_ptr = ctypes.addressof(kb)

    # Warmup
    for _ in range(100):
        hook._callback(0, w.WM_KEYDOWN, kb_ptr)
        hook.poll()

    latencies: list[float] = []
    for i in range(iterations):
        kb.vkCode = 65 + (i % 26)
        w_param = w.WM_KEYDOWN if (i % 2 == 0) else w.WM_KEYUP
        t0 = time.perf_counter_ns()
        hook._callback(0, w_param, kb_ptr)
        t1 = time.perf_counter_ns()
        hook.poll()
        latencies.append((t1 - t0) / 1000.0)  # microseconds (us)

    latencies.sort()
    p50_us = statistics.median(latencies)
    p95_us = latencies[int(iterations * 0.95)]
    p99_us = latencies[int(iterations * 0.99)]
    mean_us = statistics.mean(latencies)

    return {
        "mean_us": round(mean_us, 2),
        "p50_us": round(p50_us, 2),
        "p95_us": round(p95_us, 2),
        "p99_us": round(p99_us, 2),
    }


def measure_prediction_latency(iterations: int = 500) -> dict[str, float]:
    """Measure prediction query latency across sample prefixes."""
    from ravan.core.dict import Dictionary
    from ravan.core.learning import UserLearningEngine
    from ravan.core.predictor import DictPredictor

    predictor = DictPredictor(
        english=Dictionary.english(),
        persian=Dictionary.persian(),
        learning_engine=UserLearningEngine(auto_load=False),
    )

    sample_queries = [
        ("سل", "سلام"),
        ("در", "باره"),
        ("تش", "تشکر"),
        ("th", "thank"),
        ("wh", "what"),
        ("pro", "program"),
    ]

    # Warmup
    for pfx, ctx in sample_queries:
        predictor.predict(pfx, ctx, limit=5)

    latencies_ms: list[float] = []
    for _ in range(iterations // len(sample_queries)):
        for pfx, ctx in sample_queries:
            t0 = time.perf_counter()
            _ = predictor.predict(pfx, ctx, limit=5)
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)

    latencies_ms.sort()
    return {
        "mean_ms": round(statistics.mean(latencies_ms), 3),
        "p50_ms": round(statistics.median(latencies_ms), 3),
        "p95_ms": round(latencies_ms[int(len(latencies_ms) * 0.95)], 3),
        "p99_ms": round(latencies_ms[int(len(latencies_ms) * 0.99)], 3),
    }


def measure_autofix_latency(iterations: int = 500) -> dict[str, float]:
    """Measure wrong-layout auto-fix detection latency."""
    from ravan.core.autofix import AutoFixEngine
    from ravan.core.dict import Dictionary

    engine = AutoFixEngine(
        en_dict=Dictionary.english(),
        fa_dict=Dictionary.persian(),
    )

    test_words = [
        ("slhl", "en"),
        ("سشمئ", "fa"),
        ("o,vn", "en"),
        ("hello", "en"),
        ("سلام", "fa"),
        ("randomword123", "en"),
    ]
    # Warmup
    for w, lay in test_words:
        engine.detect(w, active_layout=lay, app_name="notepad.exe")

    latencies_ms: list[float] = []
    for _ in range(iterations // len(test_words)):
        for w, lay in test_words:
            t0 = time.perf_counter()
            _ = engine.detect(w, active_layout=lay, app_name="notepad.exe")
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)

    latencies_ms.sort()
    return {
        "mean_ms": round(statistics.mean(latencies_ms), 3),
        "p50_ms": round(statistics.median(latencies_ms), 3),
        "p95_ms": round(latencies_ms[int(len(latencies_ms) * 0.95)], 3),
        "p99_ms": round(latencies_ms[int(len(latencies_ms) * 0.99)], 3),
    }


def run_benchmark(output_json: str | None = None) -> dict[str, object]:
    print("=" * 65)
    print("        Ravaan Baseline Performance Benchmark (Phase 0)       ")
    print("=" * 65)

    print("[1/5] Measuring cold start time (subprocess)...")
    cold_start_ms = round(measure_cold_start(), 1)
    print(f"      -> Cold start: {cold_start_ms} ms")

    print("[2/5] Measuring module import, config & engine initialization...")
    total_init_ms, rss_mb, _ = measure_import_and_init()
    print(f"      -> In-process initialization: {total_init_ms:.1f} ms")
    print(f"      -> Idle Working Set (RSS): {rss_mb:.2f} MB")

    print("[3/5] Measuring synthetic hook event dispatch latency (5,000 events)...")
    hook_stats = measure_hook_latency()
    print(f"      -> Hook latency mean: {hook_stats['mean_us']} us | p95: {hook_stats['p95_us']} us")

    print("[4/5] Measuring prediction lookup latency...")
    pred_stats = measure_prediction_latency()
    print(f"      -> Prediction latency mean: {pred_stats['mean_ms']} ms | p95: {pred_stats['p95_ms']} ms")

    print("[5/5] Measuring automatic wrong-layout evaluation latency...")
    autofix_stats = measure_autofix_latency()
    print(f"      -> Auto-fix evaluation mean: {autofix_stats['mean_ms']} ms | p95: {autofix_stats['p95_ms']} ms")

    print("=" * 65)
    print("SUMMARY")
    print(f"  * Cold Start Time:       {cold_start_ms} ms")
    print(f"  * Idle RAM (RSS):         {rss_mb:.2f} MB")
    print(f"  * Hook Callback (p95):    {hook_stats['p95_us']} us ({hook_stats['p95_us'] / 1000.0:.3f} ms)")
    print(f"  * Prediction p95:         {pred_stats['p95_ms']} ms")
    print(f"  * Auto-fix p95:           {autofix_stats['p95_ms']} ms")
    print("=" * 65)

    results: dict[str, object] = {
        "cold_start_ms": cold_start_ms,
        "init_ms": round(total_init_ms, 2),
        "idle_ram_mb": rss_mb,
        "hook_latency_us": hook_stats,
        "prediction_latency_ms": pred_stats,
        "autofix_latency_ms": autofix_stats,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    if output_json:
        out_path = Path(output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Benchmark results written to {out_path}")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Ravaan Baseline Benchmark")
    parser.add_argument("--json", dest="output_json", default=None, help="Output JSON path")
    args = parser.parse_args()

    run_benchmark(output_json=args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
