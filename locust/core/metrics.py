"""
Custom Locust event helpers.
Fires additional request events so per-scenario AI latency
appears as separate rows in the Locust web UI and CSV exports.
"""
from __future__ import annotations

import json
import logging
import statistics
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import config

_log = logging.getLogger("leia-perf.metrics")
_lock = threading.Lock()
_ai_latency_samples: dict[str, list[float]] = defaultdict(list)


def _percentile(sorted_data: list[float], p: float) -> float:
    """Compute percentile p (0-100) via linear interpolation."""
    n = len(sorted_data)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_data[0]
    idx = (p / 100) * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (idx - lo)


def _percentile_targets(override: str | None = None) -> list[int]:
    raw = override if override is not None else config.PERCENTILES
    try:
        return [
            int(p.strip()) for p in raw.split(",") if p.strip().isdigit()
        ]
    except Exception:
        return [50, 90, 99]


def clear_samples() -> None:
    with _lock:
        _ai_latency_samples.clear()


def report_ai_latency(
    environment,
    scenario_type: str,
    exchange_index: int,
    latency_ms: float,
    response_length: int = 0,
) -> None:
    """Fire a custom request event for per-scenario AI latency tracking."""
    with _lock:
        _ai_latency_samples[scenario_type].append(latency_ms)
    environment.events.request.fire(
        request_type="ai_metric",
        name=f"ai_latency/{scenario_type}",
        response_time=latency_ms,
        response_length=response_length,
        exception=None,
        context={},
    )


def report_session_complete(
    environment,
    scenario_type: str,
    duration_ms: float,
) -> None:
    environment.events.request.fire(
        request_type="session_metric",
        name=f"session_complete/{scenario_type}",
        response_time=duration_ms,
        response_length=0,
        exception=None,
        context={},
    )


def report_session_failed(environment, scenario_type: str) -> None:
    environment.events.request.fire(
        request_type="session_metric",
        name=f"session_failed/{scenario_type}",
        response_time=0,
        response_length=0,
        exception=Exception("session_failed"),
        context={},
    )


def report_request_failed(
    environment, scenario_type: str, error_category: str
) -> None:
    """Fire a categorised failure event (auth_error, server_error, etc.)."""
    environment.events.request.fire(
        request_type="error_metric",
        name=f"request_failed/{scenario_type}/{error_category}",
        response_time=0,
        response_length=0,
        exception=Exception(error_category),
        context={},
    )


def report_injection_detected(environment, count: int = 1) -> None:
    for _ in range(count):
        environment.events.request.fire(
            request_type="adversarial_metric",
            name="injection_detected",
            response_time=0,
            response_length=0,
            exception=None,
            context={},
        )


def print_ai_latency_summary() -> None:
    """Log P50/P90/P99 (or configured percentiles) per scenario type."""
    with _lock:
        snapshot = {
            k: sorted(v) for k, v in _ai_latency_samples.items() if v
        }

    if not snapshot:
        return

    targets = _percentile_targets()
    pct_headers = "  ".join(f"P{p:>3}" for p in targets)
    _log.info("\n=== AI Latency Summary (ms) ===")
    _log.info("  %-24s %6s  %s", "scenario", "n", pct_headers)
    for scenario_type, s in sorted(snapshot.items()):
        pcts = "  ".join(f"{_percentile(s, p):7.0f}" for p in targets)
        _log.info("  %-24s %6d  %s", scenario_type, len(s), pcts)
    _log.info("")


def export_ai_latency_summary(output_path: Path) -> None:
    """Write full latency statistics to a JSON file."""
    with _lock:
        snapshot = {
            k: sorted(v) for k, v in _ai_latency_samples.items() if v
        }

    targets = _percentile_targets()
    result: dict = {
        "generated_at": datetime.now().isoformat(),
        "scenarios": {},
    }

    for scenario_type, s in sorted(snapshot.items()):
        n = len(s)
        entry: dict = {
            "count": n,
            "min": round(s[0], 1),
            "max": round(s[-1], 1),
            "mean": round(statistics.mean(s), 1),
            "stdev": round(statistics.stdev(s), 1) if n > 1 else 0.0,
        }
        for p in targets:
            entry[f"p{p}"] = round(_percentile(s, p), 1)
        result["scenarios"][scenario_type] = entry

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    _log.info("AI latency summary exported to %s", output_path)
