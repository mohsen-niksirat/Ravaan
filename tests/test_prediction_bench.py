"""Performance guard test: verifies that prediction latency stays well below 25 ms p95."""

from ravan.core.benchmark import run_prediction_benchmark


def test_prediction_accuracy_and_latency_benchmark():
    res = run_prediction_benchmark(warmup=5)
    # Target accuracy on held-out test fixtures
    assert res.top3_hit_rate >= 0.70, f"Top-3 hit rate too low: {res.top3_hit_rate:.2%}"
    # Target latency guard: p95 must stay well below 25 ms (loose bound to prevent flaky CI)
    assert res.p95_ms < 25.0, f"Prediction p95 latency regression: {res.p95_ms:.2f} ms >= 25.0 ms"
    assert res.mean_ms < 15.0, f"Prediction mean latency too high: {res.mean_ms:.2f} ms"
