"""Raw-layer DDL derived from the source table specifications."""

from __future__ import annotations

import logging

import psycopg
from psycopg import sql

from metricflow_platform.validation.schemas import SOURCE_TABLES, ColumnType, TableSpec

logger = logging.getLogger(__name__)

POSTGRES_TYPES = {
    ColumnType.TEXT: "text",
    ColumnType.INTEGER: "integer",
    ColumnType.DECIMAL: "numeric(12, 2)",
    ColumnType.DATE: "date",
    ColumnType.TIMESTAMP: "timestamptz",
    ColumnType.BOOLEAN: "boolean",
}

LINEAGE_COLUMNS = (
    ("_batch_id", "uuid not null"),
    ("_source_file", "text not null"),
    ("_source_row_number", "integer not null"),
    ("_loaded_at", "timestamptz not null default now()"),
)


def table_ddl(schema: str, spec: TableSpec) -> sql.Composed:
    columns = [
        sql.SQL("{} {}{}").format(
            sql.Identifier(column.name),
            sql.SQL(POSTGRES_TYPES[column.type]),
            sql.SQL(" not null" if column.required else ""),
        )
        for column in spec.columns
    ]
    columns += [
        sql.SQL("{} {}").format(sql.Identifier(name), sql.SQL(definition))
        for name, definition in LINEAGE_COLUMNS
    ]
    columns.append(
        sql.SQL("primary key ({})").format(
            sql.SQL(", ").join(map(sql.Identifier, spec.primary_key))
        )
    )
    return sql.SQL("create table if not exists {}.{} (\n    {}\n)").format(
        sql.Identifier(schema), sql.Identifier(spec.name), sql.SQL(",\n    ").join(columns)
    )


def metadata_ddl(schema: str) -> list[sql.Composed]:
    return [
        sql.SQL(
            """
            create table if not exists {}.ingestion_runs (
                run_id uuid primary key,
                batch_id uuid not null,
                table_name text not null,
                source_file text not null,
                file_sha256 text,
                status text not null check (status in ('succeeded', 'failed')),
                rows_read integer not null default 0,
                rows_inserted integer not null default 0,
                rows_updated integer not null default 0,
                rows_unchanged integer not null default 0,
                rows_rejected integer not null default 0,
                duplicates_removed integer not null default 0,
                error_message text,
                started_at timestamptz not null,
                finished_at timestamptz not null
            )
            """
        ).format(sql.Identifier(schema)),
        sql.SQL(
            """
            create table if not exists {}.rejected_records (
                table_name text not null,
                source_file text not null,
                source_row_number integer not null,
                reason text not null,
                detail text not null,
                payload jsonb not null,
                batch_id uuid not null,
                rejected_at timestamptz not null default now(),
                primary key (table_name, source_file, source_row_number)
            )
            """
        ).format(sql.Identifier(schema)),
    ]


def ensure_schema(conn: psycopg.Connection, schema: str) -> None:
    """Create the raw schema, source tables and ingestion metadata tables if they are missing."""
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(sql.SQL("create schema if not exists {}").format(sql.Identifier(schema)))
        for spec in SOURCE_TABLES:
            cur.execute(table_ddl(schema, spec))
        for statement in metadata_ddl(schema):
            cur.execute(statement)
    logger.info("schema_ready schema=%s tables=%s", schema, len(SOURCE_TABLES) + 2)
