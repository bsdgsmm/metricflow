from __future__ import annotations

import logging
import time

import psycopg

from metricflow.config import DatabaseSettings

logger = logging.getLogger(__name__)


class DatabaseUnavailableError(RuntimeError):
    """Raised when PostgreSQL cannot be reached within the allowed number of attempts."""


def connect(
    settings: DatabaseSettings, attempts: int = 1, retry_delay_seconds: float = 2.0
) -> psycopg.Connection:
    """Open a connection, retrying while the server is still starting up."""
    last_error: psycopg.OperationalError | None = None
    for attempt in range(1, attempts + 1):
        try:
            # Autocommit lets callers scope each unit of work with conn.transaction().
            return psycopg.connect(
                **settings.connection_kwargs(), connect_timeout=5, autocommit=True
            )
        except psycopg.OperationalError as exc:
            last_error = exc
            if attempt < attempts:
                logger.warning(
                    "database_not_ready host=%s port=%s attempt=%s/%s",
                    settings.host,
                    settings.port,
                    attempt,
                    attempts,
                )
                time.sleep(retry_delay_seconds)
    raise DatabaseUnavailableError(
        f"Could not connect to PostgreSQL at {settings.host}:{settings.port}/{settings.name}"
    ) from last_error
