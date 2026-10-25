from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


class ConfigurationError(ValueError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    name: str
    user: str
    password: str

    def connection_kwargs(self) -> dict[str, str | int]:
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.name,
            "user": self.user,
            "password": self.password,
        }

    def __repr__(self) -> str:
        return (
            f"DatabaseSettings(host={self.host!r}, port={self.port}, name={self.name!r}, "
            f"user={self.user!r}, password='***')"
        )


@dataclass(frozen=True)
class Settings:
    database: DatabaseSettings
    data_dir: Path
    log_level: str
    raw_schema: str = "raw"


def _require(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise ConfigurationError(f"Environment variable {key} is required but not set")
    return value


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build settings from environment variables, reading a local .env file if present."""
    if env is None:
        load_dotenv(PROJECT_ROOT / ".env")
        env = os.environ

    port_raw = env.get("METRICFLOW_DB_PORT", "5432").strip()
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ConfigurationError(
            f"METRICFLOW_DB_PORT must be an integer, got {port_raw!r}"
        ) from exc

    log_level = env.get("METRICFLOW_LOG_LEVEL", "INFO").strip().upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        raise ConfigurationError(f"Unsupported METRICFLOW_LOG_LEVEL {log_level!r}")

    data_dir = Path(env.get("METRICFLOW_DATA_DIR", "data/sample").strip())
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir

    raw_schema = env.get("METRICFLOW_RAW_SCHEMA", "raw").strip()
    if not _IDENTIFIER.match(raw_schema):
        raise ConfigurationError(f"METRICFLOW_RAW_SCHEMA {raw_schema!r} is not a valid identifier")

    return Settings(
        database=DatabaseSettings(
            host=env.get("METRICFLOW_DB_HOST", "localhost").strip(),
            port=port,
            name=_require(env, "METRICFLOW_DB_NAME"),
            user=_require(env, "METRICFLOW_DB_USER"),
            password=env.get("METRICFLOW_DB_PASSWORD", ""),
        ),
        data_dir=data_dir,
        log_level=log_level,
        raw_schema=raw_schema,
    )
