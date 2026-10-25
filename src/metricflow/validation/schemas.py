from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any


class ColumnType(StrEnum):
    TEXT = "text"
    INTEGER = "integer"
    DECIMAL = "decimal"
    DATE = "date"
    TIMESTAMP = "timestamp"
    BOOLEAN = "boolean"


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    type: ColumnType
    required: bool = True
    min_value: Decimal | int | None = None
    allowed_values: frozenset[str] | None = None


@dataclass(frozen=True)
class ForeignKey:
    column: str
    references_table: str
    references_column: str


@dataclass(frozen=True)
class RowRule:
    name: str
    check: Callable[[Mapping[str, Any]], bool]


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[ColumnSpec, ...]
    primary_key: tuple[str, ...]
    foreign_keys: tuple[ForeignKey, ...] = ()
    row_rules: tuple[RowRule, ...] = field(default_factory=tuple)

    @property
    def file_name(self) -> str:
        return f"{self.name}.csv"

    @property
    def column_names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)


def _text(name: str, required: bool = True, allowed: set[str] | None = None) -> ColumnSpec:
    return ColumnSpec(
        name, ColumnType.TEXT, required, allowed_values=frozenset(allowed) if allowed else None
    )


def _money(name: str) -> ColumnSpec:
    return ColumnSpec(name, ColumnType.DECIMAL, min_value=Decimal("0"))


def _discount_within_line_amount(row: Mapping[str, Any]) -> bool:
    return row["discount_amount"] <= row["quantity"] * row["unit_price"]


CUSTOMERS = TableSpec(
    name="customers",
    columns=(
        _text("customer_id"),
        ColumnSpec("signup_date", ColumnType.DATE),
        _text("country"),
        _text("city"),
        _text("acquisition_channel"),
        ColumnSpec("marketing_opt_in", ColumnType.BOOLEAN),
    ),
    primary_key=("customer_id",),
)

PRODUCTS = TableSpec(
    name="products",
    columns=(
        _text("product_id"),
        _text("product_name"),
        _text("category"),
        _text("subcategory"),
        _text("brand"),
        ColumnSpec("launched_on", ColumnType.DATE),
        ColumnSpec("discontinued_on", ColumnType.DATE, required=False),
    ),
    primary_key=("product_id",),
)

PRODUCT_PRICE_HISTORY = TableSpec(
    name="product_price_history",
    columns=(
        _text("product_id"),
        ColumnSpec("valid_from", ColumnType.DATE),
        _money("list_price"),
        _money("unit_cost"),
    ),
    primary_key=("product_id", "valid_from"),
    foreign_keys=(ForeignKey("product_id", "products", "product_id"),),
)

ORDERS = TableSpec(
    name="orders",
    columns=(
        _text("order_id"),
        _text("customer_id"),
        ColumnSpec("order_timestamp", ColumnType.TIMESTAMP),
        _text("status", allowed={"completed", "cancelled"}),
        _text("channel", allowed={"web", "mobile_app"}),
        _text("payment_method", allowed={"card", "paypal", "gift_card"}),
    ),
    primary_key=("order_id",),
    foreign_keys=(ForeignKey("customer_id", "customers", "customer_id"),),
)

ORDER_ITEMS = TableSpec(
    name="order_items",
    columns=(
        _text("order_item_id"),
        _text("order_id"),
        _text("product_id"),
        ColumnSpec("quantity", ColumnType.INTEGER, min_value=1),
        _money("unit_price"),
        _money("discount_amount"),
    ),
    primary_key=("order_item_id",),
    foreign_keys=(
        ForeignKey("order_id", "orders", "order_id"),
        ForeignKey("product_id", "products", "product_id"),
    ),
    row_rules=(RowRule("discount_exceeds_line_amount", _discount_within_line_amount),),
)

RETURNS = TableSpec(
    name="returns",
    columns=(
        _text("return_id"),
        _text("order_item_id"),
        ColumnSpec("return_date", ColumnType.DATE),
        ColumnSpec("quantity", ColumnType.INTEGER, min_value=1),
        _money("refund_amount"),
        _text("reason"),
    ),
    primary_key=("return_id",),
    foreign_keys=(ForeignKey("order_item_id", "order_items", "order_item_id"),),
)

# Ordered so that every table is loaded after the tables its foreign keys reference.
SOURCE_TABLES: tuple[TableSpec, ...] = (
    CUSTOMERS,
    PRODUCTS,
    PRODUCT_PRICE_HISTORY,
    ORDERS,
    ORDER_ITEMS,
    RETURNS,
)
