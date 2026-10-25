import pytest

from metricflow.config import PROJECT_ROOT, ConfigurationError, load_settings

BASE_ENV = {
    "METRICFLOW_DB_HOST": "db.internal",
    "METRICFLOW_DB_PORT": "6543",
    "METRICFLOW_DB_NAME": "analytics",
    "METRICFLOW_DB_USER": "loader",
    "METRICFLOW_DB_PASSWORD": "s3cret",
}


def test_load_settings_reads_values():
    settings = load_settings(BASE_ENV)

    assert settings.database.host == "db.internal"
    assert settings.database.port == 6543
    assert settings.database.name == "analytics"
    assert settings.log_level == "INFO"
    assert settings.data_dir == PROJECT_ROOT / "data" / "sample"


def test_password_is_masked_in_repr():
    settings = load_settings(BASE_ENV)

    assert "s3cret" not in repr(settings.database)
    assert settings.database.connection_kwargs()["password"] == "s3cret"


def test_missing_required_variable_raises():
    env = {k: v for k, v in BASE_ENV.items() if k != "METRICFLOW_DB_NAME"}

    with pytest.raises(ConfigurationError, match="METRICFLOW_DB_NAME"):
        load_settings(env)


def test_invalid_port_raises():
    with pytest.raises(ConfigurationError, match="integer"):
        load_settings({**BASE_ENV, "METRICFLOW_DB_PORT": "abc"})


def test_invalid_log_level_raises():
    with pytest.raises(ConfigurationError, match="LOG_LEVEL"):
        load_settings({**BASE_ENV, "METRICFLOW_LOG_LEVEL": "verbose"})


def test_absolute_data_dir_is_kept(tmp_path):
    settings = load_settings({**BASE_ENV, "METRICFLOW_DATA_DIR": str(tmp_path)})

    assert settings.data_dir == tmp_path
