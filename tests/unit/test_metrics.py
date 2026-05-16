"""Unit tests for metrics.py — percentile correctness and thread safety."""
from __future__ import annotations

import threading

from core.metrics import _percentile, _percentile_targets, clear_samples
from core import metrics as _m


class TestPercentile:
    def test_single_value(self):
        assert _percentile([42.0], 50) == 42.0
        assert _percentile([42.0], 99) == 42.0

    def test_empty(self):
        assert _percentile([], 50) == 0.0

    def test_two_values_p50(self):
        # P50 of [0, 100] = 50.0 (linear interp at midpoint)
        assert _percentile([0.0, 100.0], 50) == 50.0

    def test_p100_returns_max(self):
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert _percentile(data, 100) == 5.0

    def test_p0_returns_min(self):
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert _percentile(data, 0) == 1.0

    def test_p99_correct_for_small_n(self):
        # With n=10, old formula int(10*0.99)=9 → s[9] (the max).
        # Linear interp: idx = 0.99*9 = 8.91 → between s[8] and s[9].
        data = sorted(float(i) for i in range(10))  # [0..9]
        result = _percentile(data, 99)
        assert result == 8.91

    def test_p50_symmetric(self):
        data = [1.0, 3.0]
        assert _percentile(data, 50) == 2.0

    def test_monotonic(self):
        data = sorted(float(i) for i in range(100))
        p50 = _percentile(data, 50)
        p90 = _percentile(data, 90)
        p99 = _percentile(data, 99)
        assert p50 < p90 < p99


class TestPercentileTargets:
    def test_defaults(self):
        assert _percentile_targets() == [50, 90, 99]

    def test_custom(self):
        assert _percentile_targets("25,75,95") == [25, 75, 95]

    def test_invalid_values_skipped(self):
        assert _percentile_targets("50,abc,99") == [50, 99]


class TestClearSamples:
    def test_clear_empties_dict(self):
        with _m._lock:
            _m._ai_latency_samples["test_scenario"].append(100.0)

        clear_samples()

        with _m._lock:
            assert len(_m._ai_latency_samples) == 0

    def test_thread_safe_accumulation(self):
        clear_samples()
        errors: list[Exception] = []

        def writer():
            try:
                for _ in range(1000):
                    with _m._lock:
                        _m._ai_latency_samples["concurrent"].append(1.0)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        with _m._lock:
            assert len(_m._ai_latency_samples["concurrent"]) == 10_000
