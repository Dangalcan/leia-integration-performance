"""Unit tests for config.py — validate_config() behaviour."""
from __future__ import annotations

import importlib
import logging
import sys
import tempfile
from pathlib import Path

import pytest


def _reload_config(**overrides):
    """Reload config module with patched os.environ values."""
    import os
    saved = {}
    for k, v in overrides.items():
        saved[k] = os.environ.get(k)
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

    if "config" in sys.modules:
        del sys.modules["config"]
    import config as cfg

    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

    return cfg


class TestValidateConfig:
    def test_empty_runner_key_raises(self, tmp_path):
        cfg = _reload_config(
            RUNNER_KEY="", SESSIONS_DIR=str(tmp_path)
        )
        with pytest.raises(SystemExit, match="RUNNER_KEY"):
            cfg.validate_config()

    def test_missing_sessions_dir_raises(self, tmp_path):
        missing = tmp_path / "does_not_exist"
        cfg = _reload_config(
            RUNNER_KEY="valid-key",
            SESSIONS_DIR=str(missing),
        )
        with pytest.raises(SystemExit, match="SESSIONS_DIR"):
            cfg.validate_config()

    def test_valid_config_passes(self, tmp_path):
        cfg = _reload_config(
            RUNNER_KEY="valid-key",
            SESSIONS_DIR=str(tmp_path),
        )
        cfg.validate_config()  # must not raise

    def test_negative_think_time_warns(self, tmp_path, caplog):
        cfg = _reload_config(
            RUNNER_KEY="key",
            SESSIONS_DIR=str(tmp_path),
            MAX_THINK_TIME_SECONDS="-1",
        )
        with caplog.at_level(logging.WARNING):
            cfg.validate_config()
        assert any("think time" in r.message.lower() for r in caplog.records)

    def test_invalid_url_warns(self, tmp_path, caplog):
        cfg = _reload_config(
            RUNNER_KEY="key",
            SESSIONS_DIR=str(tmp_path),
            TARGET_HOST="not_a_url",
        )
        with caplog.at_level(logging.WARNING):
            cfg.validate_config()
        assert any("valid URL" in r.message for r in caplog.records)


class TestEnvVarDefaults:
    def test_burst_gap_cap_default(self):
        import config
        assert config.BURST_GAP_CAP_MS == 5000

    def test_retry_max_default(self):
        import config
        assert config.RETRY_MAX == 2

    def test_leia_instance_id_default(self):
        import config
        assert config.LEIA_INSTANCE_ID == "leia-perf-test"

    def test_continue_on_failure_default_false(self):
        import config
        assert config.CONTINUE_ON_MESSAGE_FAILURE is False
