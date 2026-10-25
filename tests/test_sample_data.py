from datetime import date

import pytest

from metricflow_platform.config import PROJECT_ROOT
from metricflow_platform.sample_data import (
    PERIOD_END,
    SCHEMAS,
    generate_dataset,
    write_dataset,
)

DEFECT_IDS = {"O999001", "O999002", "O999003", "O999004", "C99001", "C99002"}


@pytest.fixture(scope="module")
def dataset():
    return generate_dataset()


def _clean(rows, key):
    seen, clean = set(), []
    for row in rows:
        if row[key] in seen or str(row[key]).startswith(("O999", "C990", "OI999", "R999")):
            continue
        seen.add(row[key])
        clean.append(row)
    return clean


def test_generation_is_deterministic():
    assert generate_dataset(seed=7).tables == generate_dataset(seed=7).tables


def test_different_seeds_produce_different_data():
    assert generate_dataset(seed=1).tables["orders"] != generate_dataset(seed=2).tables["orders"]


def test_committed_sample_matches_generator(tmp_path, dataset):
    paths = write_dataset(dataset, tmp_path)

    for name, path in paths.items():
        committed = PROJECT_ROOT / "data" / "sample" / f"{name}.csv"
        assert path.read_bytes() == committed.read_bytes(), f"{name}.csv is out of date"


def test_rows_follow_declared_schemas(dataset):
    for name, columns in SCHEMAS.items():
        assert all(tuple(row) == columns for row in dataset.tables[name]), name


def test_documented_defects_are_present(dataset):
    ids = {row["order_id"] for row in dataset.tables["orders"]} | {
        row["customer_id"] for row in dataset.tables["customers"]
    }
    assert ids >= DEFECT_IDS


def test_unit_price_matches_price_history_at_order_date(dataset):
    history = {}
    for row in dataset.tables["product_price_history"]:
        history.setdefault(row["product_id"], []).append(
            (date.fromisoformat(row["valid_from"]), row["list_price"])
        )
    order_dates = {
        row["order_id"]: date.fromisoformat(row["order_timestamp"][:10])
        for row in _clean(dataset.tables["orders"], "order_id")
    }

    for item in _clean(dataset.tables["order_items"], "order_item_id")[:2000]:
        order_day = order_dates[item["order_id"]]
        expected = [price for start, price in history[item["product_id"]] if start <= order_day][-1]
        assert item["unit_price"] == expected


def test_returns_are_consistent_with_order_lines(dataset):
    items = {row["order_item_id"]: row for row in dataset.tables["order_items"]}
    order_dates = {
        row["order_id"]: date.fromisoformat(row["order_timestamp"][:10])
        for row in _clean(dataset.tables["orders"], "order_id")
    }

    for ret in _clean(dataset.tables["returns"], "return_id"):
        item = items[ret["order_item_id"]]
        line_net = int(item["quantity"]) * float(item["unit_price"]) - float(
            item["discount_amount"]
        )
        return_day = date.fromisoformat(ret["return_date"])
        assert 1 <= ret["quantity"] <= int(item["quantity"])
        assert float(ret["refund_amount"]) <= line_net + 0.01
        assert order_dates[item["order_id"]] < return_day <= PERIOD_END


def test_price_history_keeps_cost_below_price(dataset):
    for row in dataset.tables["product_price_history"]:
        assert 0 < float(row["unit_cost"]) < float(row["list_price"])


def test_cli_writes_all_tables(tmp_path):
    from metricflow_platform.cli import main

    assert main(["generate-sample-data", "--seed", "3", "--output-dir", str(tmp_path)]) == 0
    assert sorted(p.stem for p in tmp_path.glob("*.csv")) == sorted(SCHEMAS)
