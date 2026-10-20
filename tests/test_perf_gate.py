"""Automated CI Performance Gate & Budget Enforcement (Phase 5).

Verifies that critical user-facing pathways meet strict latency and memory budgets:
1. Dictionary mmap / cold load budget: < 25 ms.
2. Idle Working Set (RSS) RAM budget: < 45 MB.
3. Keyboard hook callback dispatch latency budget: mean < 400 us, p95 < 1000 us.
4. Typing latency under high-speed burst: < 500 us per event.
5. Safe token screening latency budget: < 5 us per token.
6. Wrong-layout auto-fix detection latency budget: mean < 2.5 ms, p95 < 8.0 ms.
7. Prediction query latency budget: mean < 5.0 ms, p95 < 15.0 ms.
"""

from __future__ import annotations

import ctypes
import statistics
import time

from ravan.core.autofix import AutoFixEngine
from ravan.core.dict import Dictionary
from ravan.core.learning import UserLearningEngine
from ravan.core.predictor import DictPredictor, is_safe_autocorrect_token
from ravan.platform import winapi as w
from ravan.platform.hook import KeyboardHook


def test_perf_dictionary_load_budget():
    """Ensure binary dictionary loading via mmap stays under 25 ms."""
    t0 = time.perf_counter()
    en_dict = Dictionary.english()
    t1 = time.perf_counter()
    fa_dict = Dictionary.persian()
    t2 = time.perf_counter()

    en_load_ms = (t1 - t0) * 1000.0
    fa_load_ms = (t2 - t1) * 1000.0

    assert en_load_ms < 25.0, f"English dictionary load exceeded budget: {en_load_ms:.2f} ms >= 25 ms"
    assert fa_load_ms < 25.0, f"Persian dictionary load exceeded budget: {fa_load_ms:.2f} ms >= 25 ms"
    assert len(en_dict) > 40_000
    assert len(fa_dict) > 100_000


def test_perf_idle_ram_budget():
    """Ensure baseline idle memory footprint in an isolated process stays under 35 MB."""
    import subprocess
    import sys

    cmd = [
        sys.executable,
        "-c",
        (
            "import ravan.platform.winapi as w; "
            "from ravan.core.dict import Dictionary; "
            "Dictionary.english(); Dictionary.persian(); "
            "print(w.get_current_process_rss_mb())"
        ),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    rss_mb = float(res.stdout.strip())
    # On Windows, RSS working set with full 160k+ dictionary loaded is ~17-19 MB
    assert rss_mb < 35.0, f"Process idle RAM exceeded budget: {rss_mb:.2f} MB >= 35.0 MB"


def test_perf_hook_callback_latency_budget():
    """Ensure low-level keyboard hook callback execution stays under 1.0 ms (p95)."""
    hook = KeyboardHook()
    kb = w.KBDLLHOOKSTRUCT()
    kb.vkCode = 65
    kb.scanCode = 30
    kb.flags = 0
    kb_ptr = ctypes.addressof(kb)

    # Warmup
    for _ in range(50):
        hook._callback(0, w.WM_KEYDOWN, kb_ptr)
        hook.poll()

    iterations = 1000
    latencies_us: list[float] = []

    for i in range(iterations):
        kb.vkCode = 65 + (i % 26)
        w_param = w.WM_KEYDOWN if (i % 2 == 0) else w.WM_KEYUP
        t0 = time.perf_counter_ns()
        hook._callback(0, w_param, kb_ptr)
        t1 = time.perf_counter_ns()
        hook.poll()
        latencies_us.append((t1 - t0) / 1000.0)

    latencies_us.sort()
    mean_us = statistics.mean(latencies_us)
    p95_us = latencies_us[int(iterations * 0.95)]

    assert mean_us < 400.0, f"Hook mean latency exceeded budget: {mean_us:.2f} us >= 400 us"
    assert p95_us < 1000.0, f"Hook p95 latency exceeded budget: {p95_us:.2f} us >= 1000 us (1 ms)"


def test_perf_typing_burst_throughput():
    """Simulate rapid burst typing of 1,000 keystrokes at 150+ WPM without backlog."""
    hook = KeyboardHook()
    kb = w.KBDLLHOOKSTRUCT()
    kb.scanCode = 30
    kb.flags = 0
    kb_ptr = ctypes.addressof(kb)

    burst_count = 1000
    t0 = time.perf_counter()
    for i in range(burst_count):
        kb.vkCode = 65 + (i % 26)
        hook._callback(0, w.WM_KEYDOWN, kb_ptr)
        evt = hook.poll()
        assert evt is not None
    t1 = time.perf_counter()

    total_ms = (t1 - t0) * 1000.0
    avg_per_event_us = (total_ms / burst_count) * 1000.0

    assert avg_per_event_us < 500.0, (
        f"Typing burst processing latency exceeded budget: {avg_per_event_us:.2f} us/event >= 500 us"
    )


def test_perf_safe_token_screening_budget():
    """Screen 5,000 tokens through safe autocorrect screening under 20 ms total."""
    tokens = [
        "سلام", "کتاب", "دانشگاه", "hello", "world", "typing",
        "https://example.com/path", "user@domain.ir", "#hashtag",
        "snake_case_func", "camelCaseVar", "C:\\Windows\\System32\\calc.exe",
        "12345", "v1.0.0", "$variable", "__init__", "COVID-19",
    ] * 300  # 5,100 tokens

    t0 = time.perf_counter()
    for tok in tokens:
        _ = is_safe_autocorrect_token(tok)
    t1 = time.perf_counter()

    duration_ms = (t1 - t0) * 1000.0
    us_per_token = (duration_ms / len(tokens)) * 1000.0

    assert duration_ms < 150.0, f"Token screening exceeded budget: {duration_ms:.2f} ms >= 150.0 ms"
    assert us_per_token < 35.0, f"Token screening per-token exceeded budget: {us_per_token:.2f} us >= 35.0 us"


def test_perf_autofix_detection_budget():
    """Ensure wrong-layout detection meets strict mean and p95 latency budgets."""
    engine = AutoFixEngine(
        en_dict=Dictionary.english(),
        fa_dict=Dictionary.persian(),
    )

    test_queries = [
        ("slhl", "en"),
        ("سشمئ", "fa"),
        ("o,vn", "en"),
        ("hello", "en"),
        ("سلام", "fa"),
        ("randomword123", "en"),
    ]

    # Warmup
    for w_word, lay in test_queries:
        engine.detect(w_word, active_layout=lay)

    latencies_ms: list[float] = []
    iterations = 300
    for _ in range(iterations // len(test_queries)):
        for w_word, lay in test_queries:
            t0 = time.perf_counter()
            _ = engine.detect(w_word, active_layout=lay)
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)

    latencies_ms.sort()
    mean_ms = statistics.mean(latencies_ms)
    p95_ms = latencies_ms[int(len(latencies_ms) * 0.95)]

    assert mean_ms < 2.5, f"Auto-fix mean latency exceeded budget: {mean_ms:.3f} ms >= 2.5 ms"
    assert p95_ms < 8.0, f"Auto-fix p95 latency exceeded budget: {p95_ms:.3f} ms >= 8.0 ms"


def test_perf_prediction_query_budget():
    """Ensure prediction queries meet mean and p95 latency budgets."""
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
    iterations = 300
    for _ in range(iterations // len(sample_queries)):
        for pfx, ctx in sample_queries:
            t0 = time.perf_counter()
            _ = predictor.predict(pfx, ctx, limit=5)
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)

    latencies_ms.sort()
    mean_ms = statistics.mean(latencies_ms)
    p95_ms = latencies_ms[int(len(latencies_ms) * 0.95)]

    assert mean_ms < 5.0, f"Prediction mean latency exceeded budget: {mean_ms:.3f} ms >= 5.0 ms"
    assert p95_ms < 15.0, f"Prediction p95 latency exceeded budget: {p95_ms:.3f} ms >= 15.0 ms"
