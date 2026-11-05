# SPDX-License-Identifier: MIT
"""Unit tests for runtime environment configuration in segel_core.config."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from segel_core.config import SegelConfig, load_config, load_dotenv


def test_default_config_loading():
    """Verify default configuration values."""
    with patch.dict(os.environ, {}, clear=True):
        cfg = load_config()
        assert cfg.mode == "demo"
        assert cfg.is_demo()
        assert not cfg.is_pilot()
        assert not cfg.is_production()
        assert cfg.port == 8000
        assert cfg.host == "0.0.0.0"
        assert cfg.log_level == "info"
        assert cfg.unit_role == "general"


def test_custom_environment_loading():
    """Verify parsing of custom environment variables."""
    env = {
        "SEGEL_MODE": "pilot",
        "SEGEL_LOG_LEVEL": "debug",
        "SEGEL_HOST": "127.0.0.1",
        "SEGEL_PORT": "9000",
        "SEGEL_DATA_DIR": "/custom/data",
        "SEGEL_STATE_DIR": "/custom/state",
        "SEGEL_KEYS_DIR": "/custom/keys",
        "SEGEL_DEPLOY_ROOT": "/custom/deploy",
        "SEGEL_UNIT_ID": "canary-primary",
        "SEGEL_UNIT_ROLE": "canary",
        "OLLAMA_HOST": "http://ollama:11434",
        "OLLAMA_MODEL": "llama3:70b",
    }
    with patch.dict(os.environ, env, clear=True):
        cfg = load_config()
        assert cfg.mode == "pilot"
        assert cfg.is_pilot()
        assert cfg.port == 9000
        assert cfg.unit_id == "canary-primary"
        assert cfg.unit_role == "canary"
        assert str(cfg.data_dir).replace("\\", "/") == "/custom/data"


def test_invalid_mode_rejected():
    """Verify that unsupported SEGEL_MODE raises ValueError."""
    with patch.dict(os.environ, {"SEGEL_MODE": "invalid_mode"}, clear=True):
        with pytest.raises(ValueError, match="Invalid SEGEL_MODE"):
            load_config()


def test_invalid_port_rejected():
    """Verify that non-numeric or out-of-range port raises ValueError."""
    with patch.dict(os.environ, {"SEGEL_PORT": "not-a-port"}, clear=True):
        with pytest.raises(ValueError, match="Invalid SEGEL_PORT"):
            load_config()

    with patch.dict(os.environ, {"SEGEL_PORT": "999999"}, clear=True):
        with pytest.raises(ValueError, match="Invalid SEGEL_PORT"):
            load_config()


def test_invalid_unit_role_rejected():
    """Verify that unknown unit role raises ValueError."""
    with patch.dict(os.environ, {"SEGEL_UNIT_ROLE": "admin"}, clear=True):
        with pytest.raises(ValueError, match="Invalid SEGEL_UNIT_ROLE"):
            load_config()


def test_load_dotenv_custom_file(tmp_path):
    """Verify load_dotenv reads and populates environment safely."""
    env_file = tmp_path / ".env.test"
    env_file.write_text("SEGEL_MODE=pilot\nSEGEL_PORT=8888\n# comment\n", encoding="utf-8")
    with patch.dict(os.environ, {}, clear=True):
        loaded = load_dotenv(env_file)
        assert loaded["SEGEL_MODE"] == "pilot"
        assert loaded["SEGEL_PORT"] == "8888"
        cfg = load_config(env_file=env_file)
        assert cfg.mode == "pilot"
        assert cfg.port == 8888

