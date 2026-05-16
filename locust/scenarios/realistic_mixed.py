"""
RealisticMixedUser — samples all sessions weighted by real distribution.
Best represents actual ALMA production load. Probes utility endpoints.
"""
from __future__ import annotations

import random

from locust import constant, task

from core.base_scenario import BaseReplayUser
from core.leia_client import get_cache_stats, get_models
from core.session_loader import BY_CLASS, SessionData


def _build_weighted_pool() -> tuple[list[SessionData], list[float]]:
    """
    Returns (sessions, weights) for random.choices().

    Weights ensure class distribution matches observed prod usage:
      short ~40%, medium ~43%, long ~11%, adversarial ~6%

    Each session within a class gets an equal share of its class
    probability so the sum of all weights equals 1.0.
    """
    target_class_probs = {
        "short": 0.40,
        "medium": 0.43,
        "long": 0.11,
        "adversarial": 0.06,
    }
    sessions: list[SessionData] = []
    weights: list[float] = []
    for cls, cls_sessions in BY_CLASS.items():
        if not cls_sessions:
            continue
        w = target_class_probs.get(cls, 0.0) / len(cls_sessions)
        for s in cls_sessions:
            sessions.append(s)
            weights.append(w)
    return sessions, weights


_POOL, _WEIGHTS = _build_weighted_pool()


class RealisticMixedUser(BaseReplayUser):
    wait_time = constant(0)
    scenario_type = "mixed"

    def _pick_session(self) -> SessionData | None:
        if not _POOL:
            return None
        return random.choices(_POOL, weights=_WEIGHTS, k=1)[0]

    def _scenario_label(self, session: SessionData) -> str:
        return f"mixed/{session.classification}"

    @task(93)
    def run_session(self):
        self.replay_session()

    @task(5)
    def probe_models(self):
        get_models(self.client)

    @task(2)
    def probe_cache_stats(self):
        get_cache_stats(self.client)
