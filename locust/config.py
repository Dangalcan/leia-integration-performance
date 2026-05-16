from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
import logging
import os

load_dotenv(Path(__file__).parent.parent / ".env")

TARGET_HOST: str = os.getenv("TARGET_HOST", "http://localhost:9000")
RUNNER_KEY: str = os.getenv("RUNNER_KEY", "")
DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "alma")
MAX_THINK_TIME_SECONDS: int = int(os.getenv("MAX_THINK_TIME_SECONDS", "120"))

_sessions_raw = os.getenv("SESSIONS_DIR", "./sessions")
SESSIONS_DIR: Path = (Path(__file__).parent.parent / _sessions_raw).resolve()

# v2 additions
LEIA_SPEC_FILE: str = os.getenv("LEIA_SPEC_FILE", "")
LEIA_INSTANCE_ID: str = os.getenv("LEIA_INSTANCE_ID", "leia-perf-test")
BURST_GAP_CAP_MS: int = int(os.getenv("BURST_GAP_CAP_MS", "5000"))
REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "60"))
RETRY_MAX: int = int(os.getenv("RETRY_MAX", "2"))
PERCENTILES: str = os.getenv("PERCENTILES", "50,90,99")
SHORT_MAX_EXCHANGES: int = int(os.getenv("SHORT_MAX_EXCHANGES", "12"))
LONG_MIN_EXCHANGES: int = int(os.getenv("LONG_MIN_EXCHANGES", "20"))
CONTINUE_ON_MESSAGE_FAILURE: bool = (
    os.getenv("CONTINUE_ON_MESSAGE_FAILURE", "false").lower() == "true"
)
PREFLIGHT_CHECK: bool = (
    os.getenv("PREFLIGHT_CHECK", "false").lower() == "true"
)
FAILURE_BACKOFF_SECONDS: float = float(
    os.getenv("FAILURE_BACKOFF_SECONDS", "2.0")
)


def validate_config() -> None:
    """Validate critical config values at startup. Raises SystemExit on errors."""
    logger = logging.getLogger("leia-perf.config")
    errors: list[str] = []

    if not RUNNER_KEY:
        errors.append(
            "RUNNER_KEY is empty — all requests will fail authentication"
        )

    if not SESSIONS_DIR.is_dir():
        errors.append(
            f"SESSIONS_DIR '{SESSIONS_DIR}' does not exist or is not a directory"
        )

    if errors:
        for msg in errors:
            logger.error("CONFIG ERROR: %s", msg)
        raise SystemExit(
            "[leia-perf] Fatal config errors — fix .env and restart:\n"
            + "\n".join(f"  • {e}" for e in errors)
        )

    if MAX_THINK_TIME_SECONDS <= 0:
        logger.warning(
            "MAX_THINK_TIME_SECONDS=%d <= 0 — think time effectively disabled",
            MAX_THINK_TIME_SECONDS,
        )

    try:
        parsed = urlparse(TARGET_HOST)
        if not parsed.scheme or not parsed.netloc:
            logger.warning(
                "TARGET_HOST='%s' does not look like a valid URL", TARGET_HOST
            )
    except Exception:
        logger.warning("Could not parse TARGET_HOST='%s'", TARGET_HOST)
