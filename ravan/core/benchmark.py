"""Prediction engine benchmark: hit-rate accuracy and p95 latency performance guard."""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ravan.core.predictor import DictPredictor

# Held-out benchmark dataset: (context, prefix, expected_word)
BENCHMARK_FIXTURES: list[tuple[str, str, str]] = [
    # Persian context & prefixes
    ("با", "تش", "تشکر"),
    ("خیلی", "مم", "ممنون"),
    ("به", "نا", "نام"),
    ("به", "عن", "عنوان"),
    ("دست", "شم", "شما"),
    ("لطفا", "بر", "بررسی"),
    ("در", "با", "باره"),
    ("امیدوارم", "حا", "حال"),
    ("خواهش", "می", "می‌کنم"),
    ("ان‌شاءالله", "سل", "سلامت"),
    ("صبح", "بخ", "بخیر"),
    ("وقت", "شر", "شریف"),
    ("ارادتمند", "شم", "شما"),
    ("موفق", "با", "باشید"),
    ("در رابطه", "با", "با"),
    ("به عنوان", "مث", "مثال"),
    # Persian prefixes (standalone)
    ("", "سلا", "سلام"),
    ("", "برن", "برنامه"),
    ("", "پرو", "پروژه"),
    ("", "سیست", "سیستم"),
    ("", "دانش", "دانشگاه"),
    ("", "اطلا", "اطلاعات"),
    ("", "کشور", "کشور"),
    ("", "ایرا", "ایران"),
    ("", "تهرا", "تهران"),
    ("", "آموز", "آموزش"),
    # English context & prefixes
    ("thank", "yo", "you"),
    ("how", "ar", "are"),
    ("best", "re", "regards"),
    ("looking", "for", "forward"),
    ("would", "li", "like"),
    ("let", "kn", "know"),
    ("please", "ch", "check"),
    ("good", "mo", "morning"),
    ("as", "so", "soon"),
    ("in", "or", "order"),
    ("nice", "me", "meeting"),
    ("thank you", "ve", "very"),
    ("how are", "yo", "you"),
    ("let me", "kn", "know"),
    # English prefixes (standalone)
    ("", "prog", "program"),
    ("", "comp", "computer"),
    ("", "wind", "windows"),
    ("", "soft", "software"),
    ("", "appl", "application"),
    ("", "deve", "development"),
    ("", "lang", "language"),
    ("", "syst", "system"),
    ("", "time", "time"),
    ("", "user", "user"),
]


@dataclass
class BenchmarkResult:
    total_queries: int
    top1_hit_rate: float
    top3_hit_rate: float
    top5_hit_rate: float
    p50_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    max_ms: float

    def format_summary(self) -> str:
        return (
            "\n"
            "==========================================================\n"
            "         RAVAAN PREDICTION ENGINE BENCHMARK               \n"
            "==========================================================\n"
            f" Total Queries Tested : {self.total_queries}\n"
            "----------------------------------------------------------\n"
            " ACCURACY METRICS:\n"
            f"   • Top-1 Hit Rate   : {self.top1_hit_rate * 100:.1f}%\n"
            f"   • Top-3 Hit Rate   : {self.top3_hit_rate * 100:.1f}%\n"
            f"   • Top-5 Hit Rate   : {self.top5_hit_rate * 100:.1f}%\n"
            "----------------------------------------------------------\n"
            " LATENCY PERFORMANCE (Target: p95 < 15.0 ms):\n"
            f"   • Mean Latency     : {self.mean_ms:.2f} ms\n"
            f"   • Median (p50)     : {self.p50_ms:.2f} ms\n"
            f"   • 90th %-ile (p90) : {self.p90_ms:.2f} ms\n"
            f"   • 95th %-ile (p95) : {self.p95_ms:.2f} ms\n"
            f"   • 99th %-ile (p99) : {self.p99_ms:.2f} ms\n"
            f"   • Max Latency      : {self.max_ms:.2f} ms\n"
            "==========================================================\n"
        )


def run_prediction_benchmark(
    predictor: DictPredictor | None = None, warmup: int = 5
) -> BenchmarkResult:
    """Benchmark prediction hit-rate and latency against held-out test fixtures."""
    if predictor is None:
        from ravan.core.config import Config
        from ravan.core.predictor import DictPredictor

        cfg = Config()
        predictor = DictPredictor.from_config(cfg)

    # Warmup lazy loaders for both English and Persian, including n-gram indexes
    for _ in range(max(1, warmup)):
        for ctx, prf, _ in BENCHMARK_FIXTURES[:8]:
            predictor.predict(prf, ctx, limit=5)

    latencies_ms: list[float] = []
    top1_hits = 0
    top3_hits = 0
    top5_hits = 0

    for context, prefix, expected in BENCHMARK_FIXTURES:
        t0 = time.perf_counter()
        candidates = predictor.predict(prefix, context, limit=5)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

        cand_texts = [c.text.strip().lower() for c in candidates]
        exp_low = expected.strip().lower()

        if cand_texts and cand_texts[0] == exp_low:
            top1_hits += 1
        if any(c == exp_low for c in cand_texts[:3]):
            top3_hits += 1
        if any(c == exp_low for c in cand_texts[:5]):
            top5_hits += 1

    n = len(BENCHMARK_FIXTURES)
    sorted_lats = sorted(latencies_ms)

    def percentile(p: float) -> float:
        idx = int(p * len(sorted_lats))
        return sorted_lats[min(idx, len(sorted_lats) - 1)]

    return BenchmarkResult(
        total_queries=n,
        top1_hit_rate=top1_hits / n,
        top3_hit_rate=top3_hits / n,
        top5_hit_rate=top5_hits / n,
        p50_ms=percentile(0.50),
        p90_ms=percentile(0.90),
        p95_ms=percentile(0.95),
        p99_ms=percentile(0.99),
        mean_ms=statistics.mean(latencies_ms),
        max_ms=max(latencies_ms),
    )
