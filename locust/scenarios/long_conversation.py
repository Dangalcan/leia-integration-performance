"""
LongConversationUser — replays sessions with long exchange counts.
Tasks can run for 10+ minutes; use lower user count (--users 5).
"""
from __future__ import annotations

import random

from locust import constant, task

from core.base_scenario import BaseReplayUser
from core.session_loader import BY_CLASS


class LongConversationUser(BaseReplayUser):
    wait_time = constant(0)
    scenario_type = "long"

    def _pick_session(self):
        pool = BY_CLASS["long"]
        return random.choice(pool) if pool else None

    @task
    def replay_long_session(self):
        self.replay_session()
