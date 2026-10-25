from collections import Counter
from decimal import Decimal

import pytest

from metricflow.config import PROJECT_ROOT
from metricflow.validation import SOURCE_TABLES, read_source_file, validate_source
from metricflow.validation.csv_reader import MalformedRow, RawRow, SourceFile
from metricflow.validation.schemas import ORDER_ITEMS, ORDERS

ORDER = {
    "order_id": "O1",
    "customer_id": "C1",
    "order_timestamp": "2024-05-01T10:00:00Z",
    "status": "completed",
    "channel": "web",
    "payment_method": "card",
}
ITEM = {
    "order_item_id": "OI1",
    "order_id": "O1",
    "product_id": "P1",
    "quantity": "2",
    "unit_price": "10.00",
    "discount_amount": "1.50",
}


def source(*rows, malformed=()):
    return SourceFile(
        path=PROJECT_ROOT / "unused.csv",
        rows=[RawRow(number, values) for number, values in enumerate(rows, start=2)],
        malformed=list(malformed),
    )


def test_valid_row_is_parsed_to_typed_values():
    result = validate_source(source(ITEM), ORDER_ITEMS)

    assert result.rejections == []
    assert [row.row_number for row in result.rows] == [2]
    assert [row.values for row in result.rows] == [
        {
            "order_item_id": "OI1",
            "order_id": "O1",
            "product_id": "P1",
            "quantity": 2,
            "unit_price": Decimal("10.00"),
            "discount_amount": Decimal("1.50"),
        }
    ]


def test_values_are_trimmed_before_validation():
    result = validate_source(source({**ITEM, "quantity": " 3 ", "order_id": " O1 "}), ORDER_ITEMS)

    assert result.rows[0].values["quantity"] == 3
    assert result.rows[0].values["order_id"] == "O1"


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"order_id": ""}, "missing_required"),
        ({"quantity": "   "}, "missing_required"),
        ({"quantity": "two"}, "invalid_integer"),
        ({"quantity": "0"}, "below_minimum"),
        ({"unit_price": "-0.01"}, "below_minimum"),
        ({"discount_amount": "25.00"}, "discount_exceeds_line_amount"),
    ],
)
def test_invalid_order_items_are_rejected(overrides, reason):
    result = validate_source(source({**ITEM, **overrides}), ORDER_ITEMS)

    assert result.rows == []
    assert [r.reason for r in result.rejections] == [reason]
    assert result.rejections[0].row_number == 2


def test_disallowed_enum_value_is_rejected():
    result = validate_source(source({**ORDER, "status": "pending_review"}), ORDERS)

    assert result.rejections[0].reason == "value_not_allowed"
    assert "status" in result.rejections[0].detail


def test_exact_duplicates_are_collapsed():
    result = validate_source(source(ITEM, dict(ITEM), dict(ITEM)), ORDER_ITEMS)

    assert len(result.rows) == 1
    assert result.duplicates_removed == 2
    assert result.rejections == []
    assert result.rows_read == 3


def test_duplicates_differing_only_in_formatting_are_exact_duplicates():
    result = validate_source(source(ITEM, {**ITEM, "unit_price": "10.0"}), ORDER_ITEMS)

    assert len(result.rows) == 1
    assert result.duplicates_removed == 1


def test_conflicting_duplicates_reject_every_occurrence():
    other = {"order_item_id": "OI2", **{k: v for k, v in ITEM.items() if k != "order_item_id"}}
    result = validate_source(source(ITEM, other, {**ITEM, "quantity": "5"}), ORDER_ITEMS)

    assert [row.values["order_item_id"] for row in result.rows] == ["OI2"]
    assert [(r.row_number, r.reason) for r in result.rejections] == [
        (2, "conflicting_duplicate_key"),
        (4, "conflicting_duplicate_key"),
    ]


def test_malformed_rows_become_rejections():
    malformed = MalformedRow(9, ["OI9", "O1"], "expected 6 fields, found 2")
    result = validate_source(source(ITEM, malformed=[malformed]), ORDER_ITEMS)

    assert result.rejections[0].reason == "malformed_row"
    assert result.rejections[0].payload == {"0": "OI9", "1": "O1"}
    assert result.rows_read == 2


def test_shipped_sample_data_matches_documented_defects():
    data_dir = PROJECT_ROOT / "data" / "sample"
    results = {
        spec.name: validate_source(read_source_file(data_dir / spec.file_name, spec), spec)
        for spec in SOURCE_TABLES
    }

    reasons = {name: Counter(r.reason for r in res.rejections) for name, res in results.items()}
    assert reasons["customers"] == {"missing_required": 1, "invalid_date": 1}
    assert reasons["orders"] == {
        "invalid_timestamp": 2,
        "missing_required": 1,
        "value_not_allowed": 1,
    }
    assert reasons["order_items"] == {
        "invalid_integer": 1,
        "below_minimum": 1,
        "conflicting_duplicate_key": 2,
        "malformed_row": 1,
    }
    assert reasons["returns"] == {"missing_required": 1}
    assert reasons["products"] == {}
    assert reasons["product_price_history"] == {}
    assert {name: res.duplicates_removed for name, res in results.items()} == {
        "customers": 3,
        "products": 0,
        "product_price_history": 0,
        "orders": 5,
        "order_items": 3,
        "returns": 0,
    }
