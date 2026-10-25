import dataclasses
import shutil
import uuid

import pytest
from psycopg import sql

from metricflow.config import PROJECT_ROOT, ConfigurationError, load_settings
from metricflow.database import DatabaseUnavailableError, connect


@pytest.fixture(scope="session")
def base_settings():
    try:
        settings = load_settings()
        connect(settings.database).close()
    except (ConfigurationError, DatabaseUnavailableError) as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")
    return settings


@pytest.fixture
def settings(base_settings):
    """Settings pointing at a throwaway raw schema that is dropped after the test."""
    schema = f"test_raw_{uuid.uuid4().hex[:12]}"
    yield dataclasses.replace(base_settings, raw_schema=schema)
    with connect(base_settings.database) as conn:
        conn.execute(sql.SQL("drop schema if exists {} cascade").format(sql.Identifier(schema)))


@pytest.fixture
def conn(base_settings):
    with connect(base_settings.database) as connection:
        yield connection


@pytest.fixture
def data_dir(tmp_path):
    """A private copy of the sample data that tests may modify."""
    target = tmp_path / "data"
    shutil.copytree(PROJECT_ROOT / "data" / "sample", target)
    return target
