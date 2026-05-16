"""
Shared session-replay logic for all scenario classes.
Subclasses declare wait_time, scenario_type, and implement _pick_session().
"""
from __future__ import annotations

import time
from uuid import uuid4

from locust import HttpUser

import config
from core.leia_client import create_leia_session, send_message
from core.metrics import (
    report_ai_latency,
    report_session_complete,
    report_session_failed,
)
from core.session_loader import SessionData


class BaseReplayUser(HttpUser):
    abstract = True
    scenario_type: str = "base"

    def _pick_session(self) -> SessionData | None:
        """Return the session to replay, or None to skip this task."""
        return None

    def _scenario_label(self, session: SessionData) -> str:
        """Return the metric label. Override for dynamic labels."""
        return self.scenario_type

    def _on_message_pre(self, text: str) -> None:
        """Hook called before each message. Override for side-effects."""

    def _request_name(self) -> str:
        return "POST /api/v1/leias/{sessionId}/messages"

    def replay_session(self) -> None:
        session = self._pick_session()
        if session is None:
            return

        scenario_type = self._scenario_label(session)
        unique_id = str(uuid4())
        session_start = time.time()

        ok = create_leia_session(
            self.client,
            unique_id,
            session.replication_name,
            config.DEFAULT_PROVIDER,
        )
        if not ok:
            report_session_failed(self.environment, scenario_type)
            time.sleep(config.FAILURE_BACKOFF_SECONDS)
            return

        request_name = self._request_name()
        for i, exchange in enumerate(session.exchanges):
            for j, text in enumerate(exchange.user_messages):
                if j > 0:
                    gap_s = (
                        min(
                            exchange.burst_gaps_ms[j - 1],
                            config.BURST_GAP_CAP_MS,
                        )
                        / 1000
                    )
                    time.sleep(gap_s)

                self._on_message_pre(text)

                msg_start = time.time()
                success, resp_len = send_message(
                    self.client,
                    unique_id,
                    text,
                    i,
                    request_name=request_name,
                )
                ai_latency_ms = (time.time() - msg_start) * 1000

                if not success:
                    if config.CONTINUE_ON_MESSAGE_FAILURE:
                        continue
                    report_session_failed(self.environment, scenario_type)
                    return

                report_ai_latency(
                    self.environment,
                    scenario_type,
                    i,
                    ai_latency_ms,
                    int(resp_len),
                )

            if i < len(session.exchanges) - 1:
                think_s = (
                    min(
                        exchange.think_time_after_ms,
                        config.MAX_THINK_TIME_SECONDS * 1000,
                    )
                    / 1000
                )
                if think_s > 0:
                    time.sleep(think_s)

        duration_ms = (time.time() - session_start) * 1000
        report_session_complete(self.environment, scenario_type, duration_ms)
