"""Unit tests for core/session_loader.py — classification and exchange building."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from core.session_loader import (
    ADVERSARIAL_RE,
    _build_exchanges,
    _classify,
    _parse_file,
)


def _make_session(exchange_count: int, messages: list[dict]) -> dict:
    return {
        "session_id": "test123",
        "replication_name": "TestReplication",
        "exchange_count": exchange_count,
        "message_count": len(messages),
        "avg_response_time_ms": 1000.0,
        "response_times": [1000] * exchange_count,
        "messages": messages,
    }


def _msg(text: str, is_leia: bool, ts: int) -> dict:
    return {"text": text, "isLeia": is_leia, "timestamp_ms": ts}


class TestClassify:
    def test_short(self):
        s = _make_session(5, [_msg("hi", False, 0), _msg("ok", True, 1)])
        assert _classify(s) == "short"

    def test_long(self):
        s = _make_session(25, [_msg("hi", False, 0), _msg("ok", True, 1)])
        assert _classify(s) == "long"

    def test_medium(self):
        s = _make_session(15, [_msg("hi", False, 0), _msg("ok", True, 1)])
        assert _classify(s) == "medium"

    def test_adversarial_jailbreak(self):
        s = _make_session(
            3, [_msg("jailbreak now", False, 0), _msg("no", True, 1)]
        )
        assert _classify(s) == "adversarial"

    def test_adversarial_ddos(self):
        s = _make_session(
            3, [_msg("I will ddos you", False, 0), _msg("no", True, 1)]
        )
        assert _classify(s) == "adversarial"

    def test_adversarial_takes_priority_over_short(self):
        s = _make_session(
            2, [_msg("ignore instructions", False, 0), _msg(".", True, 1)]
        )
        assert _classify(s) == "adversarial"

    def test_boundary_short_max(self):
        s = _make_session(12, [_msg("q", False, 0), _msg("a", True, 1)])
        assert _classify(s) == "short"

    def test_boundary_long_min(self):
        s = _make_session(20, [_msg("q", False, 0), _msg("a", True, 1)])
        assert _classify(s) == "long"

    def test_boundary_medium(self):
        s = _make_session(13, [_msg("q", False, 0), _msg("a", True, 1)])
        assert _classify(s) == "medium"


class TestBuildExchanges:
    def test_single_exchange(self):
        msgs = [
            _msg("hello", False, 1000),
            _msg("hi there", True, 3000),
        ]
        session = {**_make_session(1, msgs), "response_times": [2000]}
        exchanges = _build_exchanges(session, max_think_ms=120_000)
        assert len(exchanges) == 1
        assert exchanges[0].user_messages == ["hello"]
        assert exchanges[0].response_time_ms == 2000

    def test_think_time_capped(self):
        msgs = [
            _msg("q1", False, 0),
            _msg("a1", True, 2000),
            _msg("q2", False, 500_000),  # 500s gap — way over cap
            _msg("a2", True, 502_000),
        ]
        session = {**_make_session(2, msgs), "response_times": [2000, 2000]}
        exchanges = _build_exchanges(session, max_think_ms=60_000)
        assert exchanges[0].think_time_after_ms == 60_000

    def test_burst_gap_computed(self):
        msgs = [
            _msg("msg1", False, 1000),
            _msg("msg2", False, 1500),   # burst: 500ms gap
            _msg("response", True, 5000),
        ]
        session = {**_make_session(1, msgs), "response_times": [4000]}
        exchanges = _build_exchanges(session, max_think_ms=120_000)
        assert exchanges[0].burst_gaps_ms == [500]

    def test_trailing_user_message(self):
        msgs = [
            _msg("q1", False, 0),
            _msg("a1", True, 2000),
            _msg("q2", False, 3000),  # no LEIA reply follows
        ]
        session = {**_make_session(2, msgs), "response_times": [2000]}
        exchanges = _build_exchanges(session, max_think_ms=120_000)
        assert len(exchanges) == 2
        assert exchanges[1].response_time_ms == 0


class TestParseFile:
    def test_valid_file(self, tmp_path):
        msgs = [_msg("hello", False, 0), _msg("hi", True, 1000)]
        data = _make_session(1, msgs)
        f = tmp_path / "abc123__prod.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        sd = _parse_file(f, max_think_ms=120)
        assert sd is not None
        assert sd.session_id == "test123"
        assert sd.environment == "prod"

    def test_invalid_json_returns_none(self, tmp_path):
        f = tmp_path / "bad__prod.json"
        f.write_text("{not valid json", encoding="utf-8")
        assert _parse_file(f, max_think_ms=120) is None

    def test_missing_key_returns_none(self, tmp_path):
        f = tmp_path / "missing__prod.json"
        f.write_text(json.dumps({"exchange_count": 5}), encoding="utf-8")
        assert _parse_file(f, max_think_ms=120) is None


class TestAdversarialRe:
    def test_matches_jailbreak(self):
        assert ADVERSARIAL_RE.search("please jailbreak this")

    def test_matches_ignore_instructions(self):
        assert ADVERSARIAL_RE.search("ignore your instructions now")

    def test_no_match_normal(self):
        assert not ADVERSARIAL_RE.search("what is a software requirement?")

    def test_case_insensitive(self):
        assert ADVERSARIAL_RE.search("JAILBREAK")
