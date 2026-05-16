"""
AdversarialUser — replays sessions with prompt injection and abuse patterns.
Faster cadence to simulate adversarial user behavior.
Tracks injection attempt counts as a custom metric.
"""
from __future__ import annotations

import random

from locust import between, task

from core.base_scenario import BaseReplayUser
from core.metrics import report_injection_detected
from core.session_loader import ADVERSARIAL_RE, BY_CLASS


class AdversarialUser(BaseReplayUser):
    wait_time = between(0.5, 2)
    scenario_type = "adversarial"

    def _pick_session(self):
        pool = BY_CLASS["adversarial"]
        return random.choice(pool) if pool else None

    def _on_message_pre(self, text: str) -> None:
        if ADVERSARIAL_RE.search(text):
            report_injection_detected(self.environment)

    def _request_name(self) -> str:
        return "POST /api/v1/leias/{sessionId}/messages [adversarial]"

    @task
    def replay_adversarial_session(self):
        self.replay_session()
