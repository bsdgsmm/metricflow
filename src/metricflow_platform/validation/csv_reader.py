from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

from metricflow_platform.validation.schemas import TableSpec

logger = logging.getLogger(__name__)


class SourceSchemaError(ValueError):
    """Raised when a source file cannot be processed at all, e.g. required columns are missing."""


@dataclass(frozen=True)
class RawRow:
    row_number: int
    values: dict[str, str]


@dataclass(frozen=True)
class MalformedRow:
    row_number: int
    raw: list[str]
    detail: str


@dataclass(frozen=True)
class SourceFile:
    path: Path
    rows: list[RawRow]
    malformed: list[MalformedRow]


def read_source_file(path: Path, spec: TableSpec) -> SourceFile:
    """Read a CSV file as strings, checking the header against the table specification.

    Row numbers refer to physical file lines, with the header on line 1, so that rejected
    records can be traced back to the source file.
    """
    if not path.exists():
        raise SourceSchemaError(f"Source file {path} does not exist")

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            header = [column.strip() for column in next(reader)]
        except StopIteration:
            raise SourceSchemaError(f"Source file {path} is empty") from None

        missing = [name for name in spec.column_names if name not in header]
        if missing:
            raise SourceSchemaError(f"{path.name} is missing required columns: {missing}")
        if len(set(header)) != len(header):
            raise SourceSchemaError(f"{path.name} has duplicate column names: {header}")
        unexpected = [name for name in header if name not in spec.column_names]
        if unexpected:
            logger.warning("unexpected_columns_ignored file=%s columns=%s", path.name, unexpected)

        rows: list[RawRow] = []
        malformed: list[MalformedRow] = []
        for row_number, record in enumerate(reader, start=2):
            if not record or all(not value.strip() for value in record):
                continue
            if len(record) != len(header):
                malformed.append(
                    MalformedRow(
                        row_number,
                        record,
                        f"expected {len(header)} fields, found {len(record)}",
                    )
                )
                continue
            values = dict(zip(header, record, strict=True))
            rows.append(RawRow(row_number, {name: values[name] for name in spec.column_names}))

    return SourceFile(path=path, rows=rows, malformed=malformed)
