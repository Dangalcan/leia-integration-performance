from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent.parent / ".env")

TARGET_HOST: str = os.getenv("TARGET_HOST", "http://localhost:9000")
RUNNER_KEY: str = os.getenv("RUNNER_KEY", "")
DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "alma")
MAX_THINK_TIME_SECONDS: int = int(os.getenv("MAX_THINK_TIME_SECONDS", "120"))

_sessions_raw = os.getenv("SESSIONS_DIR", "./sessions")
SESSIONS_DIR: Path = (Path(__file__).parent.parent / _sessions_raw).resolve()
