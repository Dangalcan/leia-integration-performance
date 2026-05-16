"""
Loads and classifies all session JSON files at module import time.
Each file represents a recorded ALMA conversation to replay.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import config  # locust/ is on sys.path when running locust -f locustfile.py

_log = logging.getLogger("leia-perf.session_loader")

ADVERSARIAL_RE = re.compile(
    r"destabiliz|ddos|houthi|myanmar|idf|jailbreak"
    r"|ignore.*instructions|fucking|idiot|moron"
    r"|dev_prompt|\bllm\b",
    re.IGNORECASE,
)


@dataclass
class Exchange:
    """One user turn (1+ messages) followed by one LEIA reply."""

    user_messages: list[str]
    burst_gaps_ms: list[int]   # gaps between consecutive user msgs
    response_time_ms: int      # AI latency recorded in session data
    think_time_after_ms: int   # delay after LEIA reply (0 on last)


@dataclass
class SessionData:
    session_id: str
    filename: str
    environment: str           # "prod" or "pre"
    replication_name: str
    exchange_count: int
    exchanges: list[Exchange]
    avg_response_time_ms: float
    is_adversarial: bool
    classification: str        # "short"|"medium"|"long"|"adversarial"


def _classify(session: dict) -> str:
    user_texts = [
        m["text"] for m in session["messages"] if not m["isLeia"]
    ]
    if any(ADVERSARIAL_RE.search(t) for t in user_texts):
        return "adversarial"
    ec = session["exchange_count"]
    if ec <= config.SHORT_MAX_EXCHANGES:
        return "short"
    if ec >= config.LONG_MIN_EXCHANGES:
        return "long"
    return "medium"


def _find_next_user(
    messages: list[dict], after_idx: int
) -> Optional[dict]:
    for msg in messages[after_idx + 1:]:
        if not msg["isLeia"]:
            return msg
    return None


def _build_exchanges(
    session: dict, max_think_ms: int
) -> list[Exchange]:
    """
    Groups raw messages into Exchange objects.
    Aligns response_times[i] with the i-th LEIA reply.
    """
    messages = session["messages"]
    response_times: list[int] = session.get("response_times", [])
    exchanges: list[Exchange] = []
    user_group: list[dict] = []
    leia_index = 0

    for msg_idx, msg in enumerate(messages):
        if not msg["isLeia"]:
            user_group.append(msg)
        else:
            if not user_group:
                leia_index += 1
                continue

            user_texts = [m["text"] for m in user_group]

            burst_gaps: list[int] = [
                max(
                    0,
                    user_group[i]["timestamp_ms"]
                    - user_group[i - 1]["timestamp_ms"],
                )
                for i in range(1, len(user_group))
            ]

            rt_ms = (
                response_times[leia_index]
                if leia_index < len(response_times)
                else 0
            )

            think_ms = 0
            next_user = _find_next_user(messages, msg_idx)
            if next_user is not None:
                raw_gap = (
                    next_user["timestamp_ms"] - msg["timestamp_ms"]
                )
                think_ms = min(max(0, raw_gap), max_think_ms)

            exchanges.append(
                Exchange(
                    user_messages=user_texts,
                    burst_gaps_ms=burst_gaps,
                    response_time_ms=rt_ms,
                    think_time_after_ms=think_ms,
                )
            )
            user_group = []
            leia_index += 1

    # Trailing user messages with no LEIA reply (incomplete sessions)
    if user_group:
        exchanges.append(
            Exchange(
                user_messages=[m["text"] for m in user_group],
                burst_gaps_ms=[
                    max(
                        0,
                        user_group[i]["timestamp_ms"]
                        - user_group[i - 1]["timestamp_ms"],
                    )
                    for i in range(1, len(user_group))
                ],
                response_time_ms=0,
                think_time_after_ms=0,
            )
        )

    return exchanges


def _parse_file(
    path: Path, max_think_ms: int
) -> Optional[SessionData]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _log.warning("Skipping %s: %s", path.name, exc)
        return None

    try:
        stem = path.stem  # e.g. "68b701009e8bc17dbed90610__prod"
        parts = stem.split("__")
        env = parts[1] if len(parts) > 1 else "unknown"

        classification = _classify(raw)
        exchanges = _build_exchanges(raw, max_think_ms * 1000)

        return SessionData(
            session_id=raw["session_id"],
            filename=path.name,
            environment=env,
            replication_name=raw.get("replication_name", "unknown"),
            exchange_count=raw.get("exchange_count", len(exchanges)),
            exchanges=exchanges,
            avg_response_time_ms=raw.get("avg_response_time_ms", 0.0),
            is_adversarial=(classification == "adversarial"),
            classification=classification,
        )
    except (KeyError, ValueError, TypeError) as exc:
        _log.warning(
            "Skipping %s: malformed session data — %s", path.name, exc
        )
        return None


def load_sessions(
    sessions_dir: Path,
    max_think_seconds: int = 120,
) -> tuple[list[SessionData], dict[str, list[SessionData]]]:
    all_sessions: list[SessionData] = []
    failed = 0
    for json_file in sorted(sessions_dir.glob("*.json")):
        sd = _parse_file(json_file, max_think_seconds)
        if sd is not None:
            all_sessions.append(sd)
        else:
            failed += 1

    if failed:
        _log.warning(
            "%d session file(s) failed to parse and were skipped",
            failed,
        )

    by_class: dict[str, list[SessionData]] = {
        "short": [],
        "medium": [],
        "long": [],
        "adversarial": [],
    }
    for sd in all_sessions:
        by_class[sd.classification].append(sd)

    return all_sessions, by_class


ALL_SESSIONS, BY_CLASS = load_sessions(
    config.SESSIONS_DIR,
    config.MAX_THINK_TIME_SECONDS,
)
