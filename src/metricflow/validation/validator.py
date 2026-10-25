from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from metricflow.validation.csv_reader import SourceFile
from metricflow.validation.parsers import ParseError, parse_value
from metricflow.validation.schemas import TableSpec


@dataclass(frozen=True)
class Rejection:
    row_number: int
    reason: str
    detail: str
    payload: dict[str, str]


@dataclass(frozen=True)
class ValidRow:
    row_number: int
    values: dict[str, Any]


@dataclass
class ValidationResult:
    table: str
    rows: list[ValidRow] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)
    duplicates_removed: int = 0

    @property
    def rows_read(self) -> int:
        return len(self.rows) + len(self.rejections) + self.duplicates_removed


def _validate_row(values: dict[str, str], spec: TableSpec) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for column in spec.columns:
        raw = values[column.name].strip()
        if not raw:
            if column.required:
                raise ParseError("missing_required", f"{column.name} is required")
            parsed[column.name] = None
            continue
        try:
            value = parse_value(raw, column.type)
        except ParseError as exc:
            raise ParseError(exc.reason, f"{column.name}: {exc.detail}") from None
        if column.min_value is not None and value < column.min_value:
            raise ParseError(
                "below_minimum", f"{column.name}={raw} is below minimum {column.min_value}"
            )
        if column.allowed_values is not None and value not in column.allowed_values:
            raise ParseError("value_not_allowed", f"{column.name}={raw!r} is not an allowed value")
        parsed[column.name] = value

    for rule in spec.row_rules:
        if not rule.check(parsed):
            raise ParseError(rule.name, f"row violates rule {rule.name}")
    return parsed


def validate_source(source: SourceFile, spec: TableSpec) -> ValidationResult:
    """Validate parsed CSV rows against a table specification.

    Exact duplicate rows are collapsed into one. When the same primary key appears with
    different content there is no reliable way to pick the correct version, so every
    occurrence is rejected and left for investigation.
    """
    result = ValidationResult(table=spec.name)
    for malformed in source.malformed:
        result.rejections.append(
            Rejection(
                malformed.row_number,
                "malformed_row",
                malformed.detail,
                {str(i): value for i, value in enumerate(malformed.raw)},
            )
        )

    candidates: dict[tuple[Any, ...], list[tuple[int, dict[str, Any], dict[str, str]]]] = (
        defaultdict(list)
    )
    for raw_row in source.rows:
        try:
            parsed = _validate_row(raw_row.values, spec)
        except ParseError as exc:
            result.rejections.append(
                Rejection(raw_row.row_number, exc.reason, exc.detail, raw_row.values)
            )
            continue
        key = tuple(parsed[column] for column in spec.primary_key)
        candidates[key].append((raw_row.row_number, parsed, raw_row.values))

    for key, occurrences in candidates.items():
        distinct = {tuple(parsed.values()) for _, parsed, _ in occurrences}
        if len(distinct) == 1:
            row_number, parsed, _ = occurrences[0]
            result.rows.append(ValidRow(row_number, parsed))
            result.duplicates_removed += len(occurrences) - 1
            continue
        for row_number, _, raw_values in occurrences:
            result.rejections.append(
                Rejection(
                    row_number,
                    "conflicting_duplicate_key",
                    f"primary key {key} appears {len(occurrences)} times with different values",
                    raw_values,
                )
            )

    result.rejections.sort(key=lambda rejection: rejection.row_number)
    return result
