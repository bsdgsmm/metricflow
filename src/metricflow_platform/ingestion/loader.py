from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import psycopg
from psycopg import sql

from metricflow_platform.database.schema import POSTGRES_TYPES
from metricflow_platform.validation import Rejection, TableSpec, ValidRow


@dataclass(frozen=True)
class UpsertCounts:
    inserted: int
    updated: int
    unchanged: int


def existing_keys(conn: psycopg.Connection, schema: str, table: str, column: str) -> set[Any]:
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("select distinct {} from {}.{}").format(
                sql.Identifier(column), sql.Identifier(schema), sql.Identifier(table)
            )
        )
        return {row[0] for row in cur.fetchall()}


def upsert_rows(
    conn: psycopg.Connection,
    schema: str,
    spec: TableSpec,
    rows: list[ValidRow],
    batch_id: UUID,
    source_file: str,
) -> UpsertCounts:
    """Insert new rows and update changed rows, leaving identical rows untouched.

    Rows are bulk-loaded into a temporary table with COPY and merged with a single
    INSERT ... ON CONFLICT statement. The WHERE clause on the update keeps reruns of an
    unchanged file from rewriting rows, which keeps the load idempotent and lineage
    columns meaningful.
    """
    staging = sql.Identifier(f"_stage_{spec.name}")
    target = sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(spec.name))
    names = [*spec.column_names, "_source_row_number"]
    columns = sql.SQL(", ").join(map(sql.Identifier, names))
    value_columns = [name for name in spec.column_names if name not in spec.primary_key]

    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("create temporary table {} ({}) on commit drop").format(
                staging,
                sql.SQL(", ").join(
                    [
                        sql.SQL("{} {}").format(
                            sql.Identifier(column.name), sql.SQL(POSTGRES_TYPES[column.type])
                        )
                        for column in spec.columns
                    ]
                    + [sql.SQL("_source_row_number integer")]
                ),
            )
        )
        with cur.copy(sql.SQL("copy {} ({}) from stdin").format(staging, columns)) as copy:
            for row in rows:
                copy.write_row([row.values[name] for name in spec.column_names] + [row.row_number])

        updates = [
            sql.SQL("{0} = excluded.{0}").format(sql.Identifier(name))
            for name in [*value_columns, "_batch_id", "_source_file", "_source_row_number"]
        ]
        updates.append(sql.SQL("_loaded_at = now()"))
        changed = sql.SQL("({}) is distinct from ({})").format(
            sql.SQL(", ").join(
                sql.SQL("t.{}").format(sql.Identifier(name)) for name in value_columns
            ),
            sql.SQL(", ").join(
                sql.SQL("excluded.{}").format(sql.Identifier(name)) for name in value_columns
            ),
        )
        cur.execute(
            sql.SQL(
                """
                insert into {target} as t ({columns}, _batch_id, _source_file)
                select {columns}, %(batch_id)s, %(source_file)s from {staging}
                on conflict ({key}) do update set {updates}
                where {changed}
                returning (xmax = 0) as inserted
                """
            ).format(
                target=target,
                columns=columns,
                staging=staging,
                key=sql.SQL(", ").join(map(sql.Identifier, spec.primary_key)),
                updates=sql.SQL(", ").join(updates),
                changed=changed,
            ),
            {"batch_id": batch_id, "source_file": source_file},
        )
        results = [inserted for (inserted,) in cur.fetchall()]

    inserted = sum(results)
    updated = len(results) - inserted
    return UpsertCounts(inserted, updated, len(rows) - inserted - updated)


def replace_rejections(
    conn: psycopg.Connection,
    schema: str,
    table: str,
    source_file: str,
    rejections: list[Rejection],
    batch_id: UUID,
) -> None:
    """Make rejected_records reflect the latest run for this file only."""
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL(
                "delete from {}.rejected_records where table_name = %s and source_file = %s"
            ).format(sql.Identifier(schema)),
            (table, source_file),
        )
        cur.executemany(
            sql.SQL(
                """
                insert into {}.rejected_records
                    (table_name, source_file, source_row_number, reason, detail, payload, batch_id)
                values (%s, %s, %s, %s, %s, %s, %s)
                """
            ).format(sql.Identifier(schema)),
            [
                (
                    table,
                    source_file,
                    rejection.row_number,
                    rejection.reason,
                    rejection.detail,
                    json.dumps(rejection.payload),
                    batch_id,
                )
                for rejection in rejections
            ],
        )
