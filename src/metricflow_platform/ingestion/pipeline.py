from __future__ import annotations

import hashlib
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from psycopg import sql

from metricflow_platform.config import Settings
from metricflow_platform.database import connect, ensure_schema
from metricflow_platform.ingestion.loader import existing_keys, replace_rejections, upsert_rows
from metricflow_platform.validation import (
    SOURCE_TABLES,
    Rejection,
    TableSpec,
    ValidationResult,
    read_source_file,
    validate_source,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TableLoadReport:
    table: str
    rows_read: int
    inserted: int
    updated: int
    unchanged: int
    rejected: int
    duplicates_removed: int
    rejection_reasons: dict[str, int]


class IngestionError(RuntimeError):
    """Raised when a source table cannot be loaded; earlier tables remain committed."""


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reject_orphans(
    conn: psycopg.Connection, schema: str, spec: TableSpec, result: ValidationResult
) -> None:
    """Move rows whose foreign keys do not exist in the already-loaded parent tables."""
    for foreign_key in spec.foreign_keys:
        known = existing_keys(
            conn, schema, foreign_key.references_table, foreign_key.references_column
        )
        kept = []
        for row in result.rows:
            value = row.values[foreign_key.column]
            if value in known:
                kept.append(row)
                continue
            result.rejections.append(
                Rejection(
                    row.row_number,
                    "orphaned_foreign_key",
                    f"{foreign_key.column}={value!r} not found in "
                    f"{foreign_key.references_table}.{foreign_key.references_column}",
                    {name: str(v) if v is not None else "" for name, v in row.values.items()},
                )
            )
        result.rows = kept


def _record_run(
    conn: psycopg.Connection,
    schema: str,
    *,
    batch_id: UUID,
    spec: TableSpec,
    source_file: str,
    file_sha256: str | None,
    started_at: datetime,
    report: TableLoadReport | None,
    error: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL(
                """
                insert into {}.ingestion_runs (
                    run_id, batch_id, table_name, source_file, file_sha256, status,
                    rows_read, rows_inserted, rows_updated, rows_unchanged, rows_rejected,
                    duplicates_removed, error_message, started_at, finished_at
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
            ).format(sql.Identifier(schema)),
            (
                uuid4(),
                batch_id,
                spec.name,
                source_file,
                file_sha256,
                "failed" if report is None else "succeeded",
                report.rows_read if report else 0,
                report.inserted if report else 0,
                report.updated if report else 0,
                report.unchanged if report else 0,
                report.rejected if report else 0,
                report.duplicates_removed if report else 0,
                error,
                started_at,
                datetime.now(UTC),
            ),
        )


def load_table(
    conn: psycopg.Connection, schema: str, spec: TableSpec, data_dir: Path, batch_id: UUID
) -> TableLoadReport:
    path = data_dir / spec.file_name
    started_at = datetime.now(UTC)
    file_sha256 = _file_sha256(path) if path.exists() else None
    try:
        with conn.transaction():
            result = validate_source(read_source_file(path, spec), spec)
            _reject_orphans(conn, schema, spec, result)
            counts = upsert_rows(conn, schema, spec, result.rows, batch_id, spec.file_name)
            replace_rejections(conn, schema, spec.name, spec.file_name, result.rejections, batch_id)
            report = TableLoadReport(
                table=spec.name,
                rows_read=result.rows_read,
                inserted=counts.inserted,
                updated=counts.updated,
                unchanged=counts.unchanged,
                rejected=len(result.rejections),
                duplicates_removed=result.duplicates_removed,
                rejection_reasons=dict(Counter(r.reason for r in result.rejections)),
            )
            _record_run(
                conn,
                schema,
                batch_id=batch_id,
                spec=spec,
                source_file=spec.file_name,
                file_sha256=file_sha256,
                started_at=started_at,
                report=report,
            )
    except Exception as exc:
        with conn.transaction():
            _record_run(
                conn,
                schema,
                batch_id=batch_id,
                spec=spec,
                source_file=spec.file_name,
                file_sha256=file_sha256,
                started_at=started_at,
                report=None,
                error=str(exc),
            )
        raise IngestionError(f"Loading {spec.name} failed: {exc}") from exc

    logger.info(
        "table_loaded table=%s rows_read=%s inserted=%s updated=%s unchanged=%s "
        "rejected=%s duplicates_removed=%s",
        report.table,
        report.rows_read,
        report.inserted,
        report.updated,
        report.unchanged,
        report.rejected,
        report.duplicates_removed,
    )
    if report.rejection_reasons:
        logger.warning("rows_rejected table=%s reasons=%s", report.table, report.rejection_reasons)
    return report


def run_ingestion(settings: Settings, data_dir: Path | None = None) -> list[TableLoadReport]:
    """Validate and load every source table in dependency order.

    Each table is committed in its own transaction. If a table fails, the run stops so that
    child tables are never validated against a parent table that did not load.
    """
    source_dir = data_dir or settings.data_dir
    batch_id = uuid4()
    logger.info("ingestion_started batch_id=%s data_dir=%s", batch_id, source_dir)
    with connect(settings.database, attempts=10) as conn:
        ensure_schema(conn, settings.raw_schema)
        reports = [
            load_table(conn, settings.raw_schema, spec, source_dir, batch_id)
            for spec in SOURCE_TABLES
        ]
    logger.info(
        "ingestion_finished batch_id=%s inserted=%s updated=%s rejected=%s",
        batch_id,
        sum(r.inserted for r in reports),
        sum(r.updated for r in reports),
        sum(r.rejected for r in reports),
    )
    return reports
