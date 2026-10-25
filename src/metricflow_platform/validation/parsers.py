from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from metricflow_platform.validation.schemas import ColumnType

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TRUE = {"true", "t", "1", "yes", "y"}
_FALSE = {"false", "f", "0", "no", "n"}


class ParseError(ValueError):
    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def parse_value(raw: str, column_type: ColumnType) -> object:
    """Convert a non-empty, stripped CSV value into its Python representation."""
    match column_type:
        case ColumnType.TEXT:
            return raw
        case ColumnType.INTEGER:
            return _parse_integer(raw)
        case ColumnType.DECIMAL:
            return _parse_decimal(raw)
        case ColumnType.DATE:
            return _parse_date(raw)
        case ColumnType.TIMESTAMP:
            return _parse_timestamp(raw)
        case ColumnType.BOOLEAN:
            return _parse_boolean(raw)
    raise ValueError(f"Unsupported column type {column_type}")


def _parse_integer(raw: str) -> int:
    try:
        return int(raw)
    except ValueError:
        raise ParseError("invalid_integer", f"{raw!r} is not an integer") from None


def _parse_decimal(raw: str) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise ParseError("invalid_decimal", f"{raw!r} is not a decimal number") from None
    if not value.is_finite():
        raise ParseError("invalid_decimal", f"{raw!r} is not a finite number")
    return value


def _parse_date(raw: str) -> date:
    if not _DATE_PATTERN.match(raw):
        raise ParseError("invalid_date", f"{raw!r} is not an ISO date (YYYY-MM-DD)")
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ParseError("invalid_date", f"{raw!r} is not a valid calendar date") from None


def _parse_timestamp(raw: str) -> datetime:
    try:
        value = datetime.fromisoformat(raw)
    except ValueError:
        raise ParseError("invalid_timestamp", f"{raw!r} is not an ISO 8601 timestamp") from None
    if value.tzinfo is None:
        # Local times are ambiguous across daylight-saving changes, so sources must send offsets.
        raise ParseError("invalid_timestamp", f"{raw!r} has no UTC offset")
    return value


def _parse_boolean(raw: str) -> bool:
    lowered = raw.lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise ParseError("invalid_boolean", f"{raw!r} is not a boolean")
