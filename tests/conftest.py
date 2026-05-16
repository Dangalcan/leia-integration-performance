"""
Root conftest: configure sys.path and env vars before any module import.
session_loader runs load_sessions() at module level, so SESSIONS_DIR must
point to a real (possibly empty) directory before it is imported.
"""
import os
import sys
import tempfile
from pathlib import Path

# Must happen before any locust/ module is imported
_tmp_sessions = tempfile.mkdtemp()
os.environ.setdefault("SESSIONS_DIR", _tmp_sessions)
os.environ.setdefault("RUNNER_KEY", "test-runner-key")
os.environ.setdefault("TARGET_HOST", "http://localhost:9999")
os.environ.setdefault("PERCENTILES", "50,90,99")
os.environ.setdefault("SHORT_MAX_EXCHANGES", "12")
os.environ.setdefault("LONG_MIN_EXCHANGES", "20")

# Add locust/ to sys.path so bare imports (config, core.*) resolve correctly
sys.path.insert(0, str(Path(__file__).parent.parent / "locust"))
