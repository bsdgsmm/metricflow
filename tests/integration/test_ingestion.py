import csv

import pytest
from psycopg import sql

from metricflow.ingestion import IngestionError, run_ingestion

pytestmark = pytest.mark.integration

EXPECTED_ROWS = {
    "customers": 5000,
    "products": 120,
    "product_price_history": 474,
    "orders": 7840,
    "order_items": 15370,
    "returns": 696,
}


def count(conn, schema, table):
    query = sql.SQL("select count(*) from {}.{}").format(
        sql.Identifier(schema), sql.Identifier(table)
    )
    return conn.execute(query).fetchone()[0]


def rewrite_csv(path, transform):
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    rows = transform(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerows(rows)


def test_sample_data_loads_with_documented_rejections(settings, conn, data_dir):
    reports = {report.table: report for report in run_ingestion(settings, data_dir)}

    assert {table: count(conn, settings.raw_schema, table) for table in EXPECTED_ROWS} == (
        EXPECTED_ROWS
    )
    assert reports["order_items"].rejection_reasons == {
        "conflicting_duplicate_key": 2,
        "invalid_integer": 1,
        "below_minimum": 1,
        "malformed_row": 1,
        "orphaned_foreign_key": 2,
    }
    assert count(conn, settings.raw_schema, "rejected_records") == 14


def test_rerunning_ingestion_is_idempotent(settings, conn, data_dir):
    run_ingestion(settings, data_dir)
    second = run_ingestion(settings, data_dir)

    assert all(r.inserted == 0 and r.updated == 0 for r in second)
    assert sum(r.unchanged for r in second) == sum(EXPECTED_ROWS.values())
    assert {table: count(conn, settings.raw_schema, table) for table in EXPECTED_ROWS} == (
        EXPECTED_ROWS
    )
    assert count(conn, settings.raw_schema, "rejected_records") == 14
    assert count(conn, settings.raw_schema, "ingestion_runs") == 12


def test_changed_source_row_is_updated_in_place(settings, conn, data_dir):
    run_ingestion(settings, data_dir)

    def change_first_price(rows):
        rows[1][2] = "999.99"
        return rows

    rewrite_csv(data_dir / "product_price_history.csv", change_first_price)
    reports = {report.table: report for report in run_ingestion(settings, data_dir)}

    assert reports["product_price_history"].updated == 1
    assert reports["product_price_history"].inserted == 0
    price = conn.execute(
        sql.SQL(
            "select list_price from {}.product_price_history where product_id = 'P0001' "
            "order by valid_from limit 1"
        ).format(sql.Identifier(settings.raw_schema))
    ).fetchone()[0]
    assert str(price) == "999.99"


def test_new_rows_are_appended_on_rerun(settings, conn, data_dir):
    run_ingestion(settings, data_dir)

    def add_customer(rows):
        return [*rows, ["C77777", "2025-06-01", "Germany", "Berlin", "referral", "true"]]

    rewrite_csv(data_dir / "customers.csv", add_customer)
    reports = {report.table: report for report in run_ingestion(settings, data_dir)}

    assert reports["customers"].inserted == 1
    assert count(conn, settings.raw_schema, "customers") == EXPECTED_ROWS["customers"] + 1


def test_schema_error_fails_run_and_is_recorded(settings, conn, data_dir):
    rewrite_csv(data_dir / "orders.csv", lambda rows: [row[:3] for row in rows])

    with pytest.raises(IngestionError, match="missing required columns"):
        run_ingestion(settings, data_dir)

    statuses = conn.execute(
        sql.SQL("select table_name, status from {}.ingestion_runs order by started_at").format(
            sql.Identifier(settings.raw_schema)
        )
    ).fetchall()
    assert statuses[-1] == ("orders", "failed")
    assert count(conn, settings.raw_schema, "orders") == 0
    assert count(conn, settings.raw_schema, "order_items") == 0


def test_missing_source_file_fails_without_partial_load(settings, conn, data_dir):
    (data_dir / "returns.csv").unlink()

    with pytest.raises(IngestionError, match="does not exist"):
        run_ingestion(settings, data_dir)

    assert count(conn, settings.raw_schema, "order_items") == EXPECTED_ROWS["order_items"]
    assert count(conn, settings.raw_schema, "returns") == 0


def test_rejections_reflect_latest_run(settings, conn, data_dir):
    run_ingestion(settings, data_dir)
    rewrite_csv(
        data_dir / "returns.csv",
        lambda rows: [row for row in rows if row[0] != "R999001"],
    )
    run_ingestion(settings, data_dir)

    rejected_returns = conn.execute(
        sql.SQL("select count(*) from {}.rejected_records where table_name = 'returns'").format(
            sql.Identifier(settings.raw_schema)
        )
    ).fetchone()[0]
    assert rejected_returns == 0
