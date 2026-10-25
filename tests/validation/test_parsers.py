from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from metricflow_platform.validation.parsers import ParseError, parse_value
from metricflow_platform.validation.schemas import ColumnType


@pytest.mark.parametrize(
    ("raw", "column_type", "expected"),
    [
        ("42", ColumnType.INTEGER, 42),
        ("-3", ColumnType.INTEGER, -3),
        ("19.99", ColumnType.DECIMAL, Decimal("19.99")),
        ("2024-02-29", ColumnType.DATE, date(2024, 2, 29)),
        ("true", ColumnType.BOOLEAN, True),
        ("No", ColumnType.BOOLEAN, False),
        ("Berlin", ColumnType.TEXT, "Berlin"),
    ],
)
def test_parse_valid_values(raw, column_type, expected):
    assert parse_value(raw, column_type) == expected


@pytest.mark.parametrize(
    ("raw", "column_type", "reason"),
    [
        ("two", ColumnType.INTEGER, "invalid_integer"),
        ("1.5", ColumnType.INTEGER, "invalid_integer"),
        ("abc", ColumnType.DECIMAL, "invalid_decimal"),
        ("NaN", ColumnType.DECIMAL, "invalid_decimal"),
        ("Infinity", ColumnType.DECIMAL, "invalid_decimal"),
        ("2024-02-30", ColumnType.DATE, "invalid_date"),
        ("2023-02-29", ColumnType.DATE, "invalid_date"),
        ("24-01-05", ColumnType.DATE, "invalid_date"),
        ("2024-01-05T10:00:00Z", ColumnType.DATE, "invalid_date"),
        ("2024-13-45T10:00:00Z", ColumnType.TIMESTAMP, "invalid_timestamp"),
        ("yesterday", ColumnType.TIMESTAMP, "invalid_timestamp"),
        ("maybe", ColumnType.BOOLEAN, "invalid_boolean"),
    ],
)
def test_parse_invalid_values(raw, column_type, reason):
    with pytest.raises(ParseError) as excinfo:
        parse_value(raw, column_type)

    assert excinfo.value.reason == reason


def test_timestamp_with_z_suffix_is_utc():
    assert parse_value("2024-03-31T01:30:00Z", ColumnType.TIMESTAMP) == datetime(
        2024, 3, 31, 1, 30, tzinfo=UTC
    )


def test_timestamp_offsets_are_preserved_as_the_same_instant():
    parsed = parse_value("2024-03-31T03:30:00+02:00", ColumnType.TIMESTAMP)

    assert parsed.utcoffset() == timedelta(hours=2)
    assert parsed == datetime(2024, 3, 31, 1, 30, tzinfo=UTC)
    assert parsed.astimezone(UTC).date() == date(2024, 3, 31)


def test_naive_timestamp_is_rejected():
    with pytest.raises(ParseError, match="no UTC offset"):
        parse_value("2024-03-31T01:30:00", ColumnType.TIMESTAMP)
