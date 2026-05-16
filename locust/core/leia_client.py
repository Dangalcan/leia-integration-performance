"""
Reusable helpers that wrap leia-runner API calls with auth and error handling.
All functions take a Locust HttpUser client instance.
"""
from __future__ import annotations

import json
import logging
import time as _time
from pathlib import Path

import config

_log = logging.getLogger("leia-perf.leia_client")


def _load_leia_spec() -> dict:
    """Load LEIA spec from LEIA_SPEC_FILE, or fall back to built-in spec."""
    if config.LEIA_SPEC_FILE:
        spec_path = Path(config.LEIA_SPEC_FILE)
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            _log.info("Loaded LEIA spec from %s", spec_path)
            return spec
        except (OSError, json.JSONDecodeError) as exc:
            _log.warning(
                "Failed to load LEIA_SPEC_FILE '%s': %s — using built-in spec",
                config.LEIA_SPEC_FILE,
                exc,
            )
    return {
        "leia_id": config.LEIA_INSTANCE_ID,
        "description": (
            "{replication_name} — requirements engineering tutor "
            "for an online theater ticket platform"
        ),
        "solution": (
            "student provides complete software requirements "
            "for a theater ticket platform"
        ),
        "solution_format": "text",
        "evaluation_prompt": (
            "evaluate if the student correctly gathered the "
            "platform requirements"
        ),
    }


_SPEC = _load_leia_spec()


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {config.RUNNER_KEY}"}


def _error_category(status_code: int) -> str:
    if status_code in (401, 403):
        return "auth_error"
    if status_code >= 500:
        return "server_error"
    if status_code == 0:
        return "timeout"
    if 400 <= status_code < 500:
        return "client_error"
    return "unknown"


def create_leia_session(
    client,
    session_id: str,
    replication_name: str,
    provider: str,
    request_name: str = "POST /api/v1/leias",
) -> bool:
    """
    Creates a LEIA instance.
    Returns True on success or 409 (already exists). False on error.
    """
    description = _SPEC["description"].format(
        replication_name=replication_name
    )
    body = {
        "sessionId": session_id,
        "leia": {
            "id": _SPEC.get("leia_id", config.LEIA_INSTANCE_ID),
            "spec": {
                "behaviour": {
                    "spec": {"description": description}
                },
                "problem": {
                    "spec": {
                        "solution": _SPEC["solution"],
                        "solutionFormat": _SPEC["solution_format"],
                        "evaluationPrompt": _SPEC["evaluation_prompt"],
                    }
                },
            },
        },
        "runnerConfiguration": {"provider": provider},
    }

    with client.post(
        "/api/v1/leias",
        json=body,
        headers=_headers(),
        name=request_name,
        catch_response=True,
        timeout=config.REQUEST_TIMEOUT_SECONDS,
    ) as resp:
        if resp.status_code in (200, 201):
            resp.success()
            return True
        if resp.status_code == 409:
            resp.success()
            return True
        cat = _error_category(resp.status_code)
        resp.failure(
            f"create_leia_session failed: {resp.status_code}"
            f" [{cat}] {resp.text[:120]}"
        )
        return False


def send_message(
    client,
    session_id: str,
    message_text: str,
    exchange_index: int,
    request_name: str = "POST /api/v1/leias/{sessionId}/messages",
) -> tuple[bool, float]:
    """
    Sends one user message to an existing LEIA instance.
    Retries up to RETRY_MAX times on 5xx or network errors.
    Returns (success, response_length_chars).
    """
    for attempt in range(config.RETRY_MAX + 1):
        should_retry = False

        with client.post(
            f"/api/v1/leias/{session_id}/messages",
            json={"message": message_text},
            headers=_headers(),
            name=request_name,
            catch_response=True,
            timeout=config.REQUEST_TIMEOUT_SECONDS,
        ) as resp:
            if resp.status_code == 200:
                try:
                    data = resp.json() if resp.text else {}
                except json.JSONDecodeError:
                    resp.failure("parse_error: invalid JSON response")
                    return False, 0.0
                resp.success()
                return True, len(data.get("message", ""))

            retryable = resp.status_code >= 500 or resp.status_code == 0
            if retryable and attempt < config.RETRY_MAX:
                resp.failure(
                    f"retry {attempt + 1}/{config.RETRY_MAX}:"
                    f" status={resp.status_code}"
                )
                should_retry = True
            else:
                cat = _error_category(resp.status_code)
                resp.failure(
                    f"send_message [{exchange_index}] failed:"
                    f" {resp.status_code} [{cat}] {resp.text[:120]}"
                )
                return False, 0.0

        if should_retry:
            _time.sleep(0.5 * (2 ** attempt))

    return False, 0.0


def get_models(
    client, request_name: str = "GET /api/v1/models"
) -> bool:
    with client.get(
        "/api/v1/models",
        headers=_headers(),
        name=request_name,
        catch_response=True,
        timeout=config.REQUEST_TIMEOUT_SECONDS,
    ) as resp:
        if resp.status_code == 200:
            resp.success()
            return True
        resp.failure(f"get_models failed: {resp.status_code}")
        return False


def get_cache_stats(
    client, request_name: str = "GET /api/v1/cache/stats"
) -> bool:
    with client.get(
        "/api/v1/cache/stats",
        headers=_headers(),
        name=request_name,
        catch_response=True,
        timeout=config.REQUEST_TIMEOUT_SECONDS,
    ) as resp:
        if resp.status_code == 200:
            resp.success()
            return True
        resp.failure(f"get_cache_stats failed: {resp.status_code}")
        return False
