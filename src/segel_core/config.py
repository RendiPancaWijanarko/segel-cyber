# SPDX-License-Identifier: MIT
"""SEGEL Environment Configuration & Operational Settings.

Loads, validates, and provides access to runtime configuration per PRD v2.0 §16.
Supports 'demo', 'pilot', and 'production' operational modes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

VALID_MODES = frozenset({"demo", "pilot", "production"})
VALID_LOG_LEVELS = frozenset({"debug", "info", "warning", "error", "critical"})
VALID_ROLES = frozenset({"canary", "general"})


@dataclass(frozen=True)
class SegelConfig:
    """Runtime configuration container for SEGEL services."""

    mode: str
    log_level: str
    host: str
    port: int
    data_dir: Path
    state_dir: Path
    keys_dir: Path
    deploy_root: Path
    unit_id: str
    unit_role: str
    ollama_host: str
    ollama_model: str

    def is_demo(self) -> bool:
        return self.mode == "demo"

    def is_pilot(self) -> bool:
        return self.mode == "pilot"

    def is_production(self) -> bool:
        return self.mode == "production"

    def validate_directories(self) -> None:
        """Ensure designated directory paths can be created or accessed."""
        if not self.is_demo():
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self.deploy_root.mkdir(parents=True, exist_ok=True)


def load_dotenv(env_file: Path | str | None = None) -> dict[str, str]:
    """Parse a .env file and populate os.environ for keys that are not already set.

    Args:
        env_file: Optional explicit path to .env file. Defaults to .env in cwd.

    Returns:
        Dictionary of loaded key-value pairs.
    """
    path = Path(env_file) if env_file else Path.cwd() / ".env"
    loaded: dict[str, str] = {}
    if not path.is_file():
        return loaded
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k:
                loaded[k] = v
                if k not in os.environ:
                    os.environ[k] = v
    return loaded


def load_config(env_file: Path | str | None = None, auto_load_dotenv: bool = False) -> SegelConfig:
    """Load configuration from environment variables with safe defaults.

    Args:
        env_file: Optional explicit path to .env file.
        auto_load_dotenv: If True, automatically loads from .env if present.

    Returns:
        SegelConfig initialized from os.environ.

    Raises:
        ValueError: If any environment variable has an invalid value.
    """
    if auto_load_dotenv or env_file:
        load_dotenv(env_file)
    mode = os.getenv("SEGEL_MODE", "demo").lower().strip()
    if mode not in VALID_MODES:
        raise ValueError(
            f"Invalid SEGEL_MODE '{mode}'. Must be one of: {sorted(VALID_MODES)}"
        )

    log_level = os.getenv("SEGEL_LOG_LEVEL", "info").lower().strip()
    if log_level not in VALID_LOG_LEVELS:
        raise ValueError(
            f"Invalid SEGEL_LOG_LEVEL '{log_level}'. Must be one of: {sorted(VALID_LOG_LEVELS)}"
        )

    host = os.getenv("SEGEL_HOST", "0.0.0.0").strip()  # noqa: S104 # nosec B104

    port_raw = os.getenv("SEGEL_PORT", "8000").strip()
    try:
        port = int(port_raw)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        msg = f"Invalid SEGEL_PORT '{port_raw}'. Must be an integer between 1 and 65535."
        raise ValueError(msg) from None

    data_dir = Path(os.getenv("SEGEL_DATA_DIR", "/var/lib/segel"))
    state_dir = Path(os.getenv("SEGEL_STATE_DIR", str(data_dir / "state")))
    keys_dir = Path(os.getenv("SEGEL_KEYS_DIR", "/etc/segel/keys"))
    deploy_root = Path(os.getenv("SEGEL_DEPLOY_ROOT", "/opt/app/config"))

    unit_id = os.getenv("SEGEL_UNIT_ID", "unit-local").strip()
    unit_role = os.getenv("SEGEL_UNIT_ROLE", "general").lower().strip()
    if unit_role not in VALID_ROLES:
        raise ValueError(
            f"Invalid SEGEL_UNIT_ROLE '{unit_role}'. Must be one of: {sorted(VALID_ROLES)}"
        )

    ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").strip()
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3:8b").strip()

    return SegelConfig(
        mode=mode,
        log_level=log_level,
        host=host,
        port=port,
        data_dir=data_dir,
        state_dir=state_dir,
        keys_dir=keys_dir,
        deploy_root=deploy_root,
        unit_id=unit_id,
        unit_role=unit_role,
        ollama_host=ollama_host,
        ollama_model=ollama_model,
    )
