"""
ShortConversationUser — replays sessions with short exchange counts.
Suitable for high concurrency; tasks finish in ~2-3 minutes.
"""
from __future__ import annotations

import random

from locust import constant, task

from core.base_scenario import BaseReplayUser
from core.session_loader import BY_CLASS


class ShortConversationUser(BaseReplayUser):
    wait_time = constant(0)
    scenario_type = "short"

    def _pick_session(self):
        pool = BY_CLASS["short"]
        return random.choice(pool) if pool else None

    @task
    def replay_short_session(self):
        self.replay_session()
