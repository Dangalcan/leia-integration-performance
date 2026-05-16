"""
Main Locust entry point.

Run all scenarios:
    locust -f locust/locustfile.py

Run a specific scenario:
    locust -f locust/locustfile.py ShortConversationUser
    locust -f locust/locustfile.py LongConversationUser
    locust -f locust/locustfile.py AdversarialUser
    locust -f locust/locustfile.py RealisticMixedUser
"""
import logging
from pathlib import Path

import requests as _requests
from locust import events

import config
from core.metrics import (
    clear_samples,
    export_ai_latency_summary,
    print_ai_latency_summary,
)
from core.session_loader import ALL_SESSIONS, BY_CLASS

from scenarios.short_conversation import ShortConversationUser
from scenarios.long_conversation import LongConversationUser
from scenarios.adversarial import AdversarialUser
from scenarios.realistic_mixed import RealisticMixedUser

__all__ = [
    "ShortConversationUser",
    "LongConversationUser",
    "AdversarialUser",
    "RealisticMixedUser",
]

_log = logging.getLogger("leia-perf")


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    config.validate_config()

    total = len(ALL_SESSIONS)
    counts = {cls: len(s) for cls, s in BY_CLASS.items()}
    _log.info(
        "Sessions loaded: %d total — "
        "short=%d  medium=%d  long=%d  adversarial=%d",
        total,
        counts["short"],
        counts["medium"],
        counts["long"],
        counts["adversarial"],
    )
    _log.info("Target: %s", config.TARGET_HOST)
    _log.info("Provider: %s", config.DEFAULT_PROVIDER)
    _log.info(
        "Think cap: %ds | Burst gap cap: %dms | "
        "Timeout: %ds | Retries: %d",
        config.MAX_THINK_TIME_SECONDS,
        config.BURST_GAP_CAP_MS,
        config.REQUEST_TIMEOUT_SECONDS,
        config.RETRY_MAX,
    )

    if config.PREFLIGHT_CHECK:
        _run_preflight()


def _run_preflight() -> None:
    """Optional pre-test connectivity and auth check."""
    url = f"{config.TARGET_HOST}/api/v1/models"
    headers = {"Authorization": f"Bearer {config.RUNNER_KEY}"}
    try:
        resp = _requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            _log.info("Preflight passed (GET /api/v1/models -> 200)")
        elif resp.status_code in (401, 403):
            _log.warning(
                "Preflight: auth failed (%d) — check RUNNER_KEY",
                resp.status_code,
            )
        else:
            _log.warning(
                "Preflight: GET /api/v1/models returned %d",
                resp.status_code,
            )
    except _requests.exceptions.ConnectionError:
        _log.warning(
            "Preflight: cannot connect to %s — check TARGET_HOST",
            config.TARGET_HOST,
        )
    except _requests.exceptions.Timeout:
        _log.warning(
            "Preflight: connection to %s timed out",
            config.TARGET_HOST,
        )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    clear_samples()


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print_ai_latency_summary()
    export_ai_latency_summary(Path("reports/ai_latency_summary.json"))
