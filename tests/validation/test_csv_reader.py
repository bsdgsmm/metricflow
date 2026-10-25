import logging

import pytest

from metricflow.validation.csv_reader import SourceSchemaError, read_source_file
from metricflow.validation.schemas import RETURNS


def write(path, text):
    path.write_text(text, encoding="utf-8", newline="")
    return path


HEADER = "return_id,order_item_id,return_date,quantity,refund_amount,reason\n"


def test_reads_rows_with_physical_line_numbers(tmp_path):
    path = write(
        tmp_path / "returns.csv",
        HEADER + "R1,OI1,2024-01-02,1,9.99,damaged\n\nR2,OI2,2024-01-03,1,5.00,changed_mind\n",
    )

    source = read_source_file(path, RETURNS)

    assert [row.row_number for row in source.rows] == [2, 4]
    assert source.rows[0].values["refund_amount"] == "9.99"
    assert source.malformed == []


def test_rows_with_wrong_field_count_are_malformed(tmp_path):
    path = write(
        tmp_path / "returns.csv",
        HEADER + "R1,OI1,2024-01-02\nR2,OI2,2024-01-03,1,5.00,changed_mind,extra\n",
    )

    source = read_source_file(path, RETURNS)

    assert source.rows == []
    assert [(m.row_number, m.detail) for m in source.malformed] == [
        (2, "expected 6 fields, found 3"),
        (3, "expected 6 fields, found 7"),
    ]


def test_quoted_commas_are_not_malformed(tmp_path):
    path = write(tmp_path / "returns.csv", HEADER + 'R1,OI1,2024-01-02,1,9.99,"late, damaged"\n')

    source = read_source_file(path, RETURNS)

    assert source.rows[0].values["reason"] == "late, damaged"


def test_column_order_and_extra_columns_are_tolerated(tmp_path, caplog):
    path = write(
        tmp_path / "returns.csv",
        "reason,refund_amount,quantity,return_date,order_item_id,return_id,note\n"
        "damaged,9.99,1,2024-01-02,OI1,R1,ignored\n",
    )

    with caplog.at_level(logging.WARNING):
        source = read_source_file(path, RETURNS)

    assert source.rows[0].values == {
        "return_id": "R1",
        "order_item_id": "OI1",
        "return_date": "2024-01-02",
        "quantity": "1",
        "refund_amount": "9.99",
        "reason": "damaged",
    }
    assert "unexpected_columns_ignored" in caplog.text


def test_missing_required_column_raises(tmp_path):
    path = write(tmp_path / "returns.csv", "return_id,order_item_id\nR1,OI1\n")

    with pytest.raises(SourceSchemaError, match="missing required columns"):
        read_source_file(path, RETURNS)


def test_empty_and_missing_files_raise(tmp_path):
    with pytest.raises(SourceSchemaError, match="empty"):
        read_source_file(write(tmp_path / "returns.csv", ""), RETURNS)
    with pytest.raises(SourceSchemaError, match="does not exist"):
        read_source_file(tmp_path / "absent.csv", RETURNS)


def test_byte_order_mark_is_ignored(tmp_path):
    path = tmp_path / "returns.csv"
    path.write_bytes(("﻿" + HEADER + "R1,OI1,2024-01-02,1,9.99,damaged\n").encode("utf-8"))

    assert read_source_file(path, RETURNS).rows[0].values["return_id"] == "R1"
