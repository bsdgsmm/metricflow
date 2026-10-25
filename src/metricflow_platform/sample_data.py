"""Deterministic generator for the synthetic e-commerce sample dataset.

The simulation is intentionally simple but produces the behaviours the analytics layer needs:
growth, seasonality, product lifecycles, price changes, discounts, returns and segment-dependent
repeat purchasing. A small, documented set of defective rows is appended so that ingestion
validation is exercised against the shipped data, not only against test fixtures.
"""

from __future__ import annotations

import csv
import logging
import math
import random
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from itertools import accumulate
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_SEED = 20230101
PERIOD_START = date(2023, 1, 1)
PERIOD_END = date(2025, 12, 31)
CUSTOMER_COUNT = 5000
NON_PURCHASER_SHARE = 0.15
CANCELLATION_RATE = 0.04


@dataclass(frozen=True)
class Category:
    name: str
    subcategories: tuple[str, ...]
    brands: tuple[str, ...]
    nouns: tuple[str, ...]
    price_range: tuple[float, float]
    cost_ratio: tuple[float, float]
    return_rate: float
    product_count: int


CATEGORIES = (
    Category(
        "Electronics",
        ("Audio", "Accessories", "Smart Home"),
        ("Voltix", "Auralis", "Nexon"),
        ("Headphones", "Speaker", "Charger", "Smart Plug", "Webcam", "Keyboard"),
        (25.0, 320.0),
        (0.68, 0.80),
        0.06,
        24,
    ),
    Category(
        "Home & Kitchen",
        ("Cookware", "Storage", "Decor"),
        ("Hearthly", "Casa Nova", "Oakline"),
        ("Pan", "Knife Set", "Storage Box", "Lamp", "Cutting Board", "Kettle"),
        (12.0, 140.0),
        (0.45, 0.60),
        0.03,
        22,
    ),
    Category(
        "Apparel",
        ("Tops", "Outerwear", "Footwear"),
        ("Northwind", "Loomwear", "Strada"),
        ("T-Shirt", "Hoodie", "Jacket", "Sneakers", "Jeans", "Scarf"),
        (15.0, 160.0),
        (0.35, 0.50),
        0.12,
        24,
    ),
    Category(
        "Beauty",
        ("Skincare", "Haircare", "Fragrance"),
        ("Lumea", "Purely", "Verdant"),
        ("Serum", "Moisturizer", "Shampoo", "Eau de Parfum", "Cleanser", "Hair Oil"),
        (8.0, 95.0),
        (0.30, 0.45),
        0.02,
        18,
    ),
    Category(
        "Sports & Outdoors",
        ("Fitness", "Camping", "Cycling"),
        ("Peakform", "Trailhead", "Velocity"),
        ("Yoga Mat", "Dumbbells", "Tent", "Water Bottle", "Bike Light", "Backpack"),
        (10.0, 260.0),
        (0.50, 0.65),
        0.04,
        18,
    ),
    Category(
        "Books",
        ("Fiction", "Business", "Cooking"),
        ("Inkwell Press", "Meridian Books", "Folio House"),
        ("Novel", "Handbook", "Cookbook", "Guide", "Anthology", "Workbook"),
        (9.0, 45.0),
        (0.50, 0.62),
        0.01,
        14,
    ),
)

ADJECTIVES = ("Classic", "Pro", "Essential", "Compact", "Premium", "Everyday", "Ultra", "Eco")

LOCATIONS = {
    "United States": ("New York", "Austin", "Seattle", "Chicago", "Denver"),
    "United Kingdom": ("London", "Manchester", "Bristol", "Leeds"),
    "Germany": ("Berlin", "Munich", "Hamburg", "Cologne"),
    "France": ("Paris", "Lyon", "Marseille"),
    "Netherlands": ("Amsterdam", "Rotterdam", "Utrecht"),
    "Canada": ("Toronto", "Vancouver", "Montreal"),
    "Australia": ("Sydney", "Melbourne", "Brisbane"),
}
COUNTRY_WEIGHTS = (34, 18, 14, 10, 8, 9, 7)


@dataclass(frozen=True)
class ChannelProfile:
    signup_weight: float
    repeat_probability: float
    mean_gap_days: float


ACQUISITION_CHANNELS = {
    "organic_search": ChannelProfile(0.30, 0.55, 75),
    "paid_search": ChannelProfile(0.22, 0.45, 90),
    "paid_social": ChannelProfile(0.20, 0.35, 110),
    "email": ChannelProfile(0.10, 0.65, 60),
    "referral": ChannelProfile(0.10, 0.70, 55),
    "affiliate": ChannelProfile(0.08, 0.40, 100),
}

MONTH_ACCEPTANCE = {
    1: 0.72,
    2: 0.68,
    3: 0.78,
    4: 0.78,
    5: 0.82,
    6: 0.80,
    7: 0.76,
    8: 0.80,
    9: 0.84,
    10: 0.88,
    11: 1.00,
    12: 0.97,
}
HOUR_WEIGHTS = (1, 1, 1, 1, 1, 2, 3, 4, 5, 6, 6, 7, 8, 7, 6, 6, 7, 8, 9, 10, 10, 8, 5, 2)
DISCOUNT_PROBABILITY = {11: 0.40, 12: 0.25}
BASE_DISCOUNT_PROBABILITY = 0.15
DISCOUNT_RATES = (0.05, 0.10, 0.15, 0.20, 0.25)
RETURN_REASONS = ("damaged", "wrong_size", "not_as_described", "changed_mind", "late_delivery")
TREND_SLOPES = {"stable": 0.0, "growing": 0.55, "declining": -0.85}

SCHEMAS = {
    "customers": (
        "customer_id",
        "signup_date",
        "country",
        "city",
        "acquisition_channel",
        "marketing_opt_in",
    ),
    "products": (
        "product_id",
        "product_name",
        "category",
        "subcategory",
        "brand",
        "launched_on",
        "discontinued_on",
    ),
    "product_price_history": ("product_id", "valid_from", "list_price", "unit_cost"),
    "orders": ("order_id", "customer_id", "order_timestamp", "status", "channel", "payment_method"),
    "order_items": (
        "order_item_id",
        "order_id",
        "product_id",
        "quantity",
        "unit_price",
        "discount_amount",
    ),
    "returns": ("return_id", "order_item_id", "return_date", "quantity", "refund_amount", "reason"),
}


@dataclass
class Product:
    product_id: str
    name: str
    category: Category
    subcategory: str
    brand: str
    launched_on: date
    discontinued_on: date | None
    popularity: float
    trend: str
    price_history: list[tuple[date, float, float]] = field(default_factory=list)

    def is_available(self, day: date) -> bool:
        return self.launched_on <= day and (
            self.discontinued_on is None or day < self.discontinued_on
        )

    def price_on(self, day: date) -> tuple[float, float]:
        starts = [valid_from for valid_from, _, _ in self.price_history]
        _, list_price, unit_cost = self.price_history[bisect_right(starts, day) - 1]
        return list_price, unit_cost


@dataclass
class Dataset:
    tables: dict[str, list[dict[str, object]]]

    def row_counts(self) -> dict[str, int]:
        return {name: len(rows) for name, rows in self.tables.items()}


def _random_date(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def _money(value: float) -> float:
    return round(value + 1e-9, 2)


def _generate_products(rng: random.Random) -> list[Product]:
    products: list[Product] = []
    for category in CATEGORIES:
        for _ in range(category.product_count):
            launched_before_period = rng.random() < 0.75
            if launched_before_period:
                launched_on = _random_date(rng, date(2021, 1, 1), date(2022, 12, 31))
            else:
                launched_on = _random_date(rng, PERIOD_START, date(2025, 6, 30))
            trend = rng.choices(("stable", "growing", "declining"), weights=(60, 22, 18))[0]
            discontinued_on = None
            earliest_discontinuation = max(launched_on + timedelta(days=365), date(2024, 6, 1))
            last_discontinuation = date(2025, 11, 30)
            if (
                trend == "declining"
                and earliest_discontinuation < last_discontinuation
                and rng.random() < 0.35
            ):
                discontinued_on = _random_date(rng, earliest_discontinuation, last_discontinuation)
            brand = rng.choice(category.brands)
            product = Product(
                product_id=f"P{len(products) + 1:04d}",
                name=f"{brand} {rng.choice(ADJECTIVES)} {rng.choice(category.nouns)}",
                category=category,
                subcategory=rng.choice(category.subcategories),
                brand=brand,
                launched_on=launched_on,
                discontinued_on=discontinued_on,
                popularity=rng.lognormvariate(0, 0.6),
                trend=trend,
            )
            product.price_history = _generate_price_history(rng, category, launched_on)
            products.append(product)
    return products


def _generate_price_history(
    rng: random.Random, category: Category, launched_on: date
) -> list[tuple[date, float, float]]:
    low, high = category.price_range
    list_price = _money(math.exp(rng.uniform(math.log(low), math.log(high)))) - 0.01
    unit_cost = _money(list_price * rng.uniform(*category.cost_ratio))
    history = [(launched_on, _money(list_price), unit_cost)]
    valid_from = launched_on
    while True:
        valid_from += timedelta(days=rng.randint(240, 480))
        if valid_from > PERIOD_END:
            return history
        list_price = _money(list_price * rng.uniform(0.92, 1.12))
        unit_cost = _money(min(unit_cost * rng.uniform(0.96, 1.08), list_price * 0.9))
        history.append((valid_from, list_price, unit_cost))


def _product_weights_by_month(products: list[Product]) -> dict[tuple[int, int], list[float]]:
    weights: dict[tuple[int, int], list[float]] = {}
    year, month = PERIOD_START.year, PERIOD_START.month
    while date(year, month, 1) <= PERIOD_END:
        day = date(year, month, 15)
        years_elapsed = (day - PERIOD_START).days / 365.25
        monthly = [
            product.popularity * math.exp(TREND_SLOPES[product.trend] * years_elapsed)
            if product.is_available(day)
            else 0.0
            for product in products
        ]
        weights[(year, month)] = list(accumulate(monthly))
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return weights


def _signup_date(rng: random.Random) -> date:
    # Inverse CDF of a linearly increasing density on [0, 1] produces steady customer growth.
    slope = 1.5
    u = rng.random()
    t = (-1 + math.sqrt(1 + slope * (slope + 2) * u)) / slope
    return PERIOD_START + timedelta(days=int(t * (PERIOD_END - PERIOD_START).days))


def _order_timestamp(rng: random.Random, day: date) -> datetime:
    hour = rng.choices(range(24), weights=HOUR_WEIGHTS)[0]
    return datetime(
        day.year, day.month, day.day, hour, rng.randint(0, 59), rng.randint(0, 59), tzinfo=UTC
    )


def _customer_order_dates(rng: random.Random, signup: date, profile: ChannelProfile) -> list[date]:
    if rng.random() < NON_PURCHASER_SHARE:
        return []
    first = signup + timedelta(days=int(rng.expovariate(1 / 6)))
    if first > PERIOD_END:
        return []
    dates = [first]
    current = first
    while rng.random() < profile.repeat_probability:
        while True:
            current += timedelta(days=max(1, int(rng.expovariate(1 / profile.mean_gap_days))))
            if current > PERIOD_END or rng.random() < MONTH_ACCEPTANCE[current.month]:
                break
        if current > PERIOD_END:
            break
        dates.append(current)
    return dates


def generate_dataset(seed: int = DEFAULT_SEED) -> Dataset:
    """Generate the full sample dataset, including documented defective rows."""
    rng = random.Random(seed)
    products = _generate_products(rng)
    product_weights = _product_weights_by_month(products)
    channel_names = tuple(ACQUISITION_CHANNELS)
    channel_weights = tuple(p.signup_weight for p in ACQUISITION_CHANNELS.values())
    countries = tuple(LOCATIONS)

    customers: list[dict[str, object]] = []
    orders: list[dict[str, object]] = []
    order_items: list[dict[str, object]] = []
    returns: list[dict[str, object]] = []

    for index in range(1, CUSTOMER_COUNT + 1):
        country = rng.choices(countries, weights=COUNTRY_WEIGHTS)[0]
        channel = rng.choices(channel_names, weights=channel_weights)[0]
        signup = _signup_date(rng)
        customer_id = f"C{index:05d}"
        customers.append(
            {
                "customer_id": customer_id,
                "signup_date": signup.isoformat(),
                "country": country,
                "city": rng.choice(LOCATIONS[country]),
                "acquisition_channel": channel,
                "marketing_opt_in": "true" if rng.random() < 0.55 else "false",
            }
        )
        for order_day in _customer_order_dates(rng, signup, ACQUISITION_CHANNELS[channel]):
            orders.append(_build_order(rng, customer_id, order_day))

    orders.sort(key=lambda row: (row["order_timestamp"], row["customer_id"]))
    for position, order in enumerate(orders, start=1):
        order["order_id"] = f"O{position:06d}"
        _build_order_lines(rng, order, products, product_weights, order_items, returns)

    tables = {
        "customers": customers,
        "products": [_product_row(product) for product in products],
        "product_price_history": [
            {
                "product_id": product.product_id,
                "valid_from": valid_from.isoformat(),
                "list_price": f"{list_price:.2f}",
                "unit_cost": f"{unit_cost:.2f}",
            }
            for product in products
            for valid_from, list_price, unit_cost in product.price_history
        ],
        "orders": orders,
        "order_items": order_items,
        "returns": returns,
    }
    _inject_defects(tables)
    return Dataset(tables=tables)


def _build_order(rng: random.Random, customer_id: str, order_day: date) -> dict[str, object]:
    years_elapsed = (order_day - PERIOD_START).days / 365.25
    mobile_share = 0.30 + 0.08 * years_elapsed
    timestamp = _order_timestamp(rng, order_day)
    return {
        "order_id": "",
        "customer_id": customer_id,
        "order_timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "cancelled" if rng.random() < CANCELLATION_RATE else "completed",
        "channel": "mobile_app" if rng.random() < mobile_share else "web",
        "payment_method": rng.choices(("card", "paypal", "gift_card"), weights=(70, 24, 6))[0],
    }


def _build_order_lines(
    rng: random.Random,
    order: dict[str, object],
    products: list[Product],
    product_weights: dict[tuple[int, int], list[float]],
    order_items: list[dict[str, object]],
    returns: list[dict[str, object]],
) -> None:
    order_day = date.fromisoformat(str(order["order_timestamp"])[:10])
    cumulative = product_weights[(order_day.year, order_day.month)]
    line_count = rng.choices((1, 2, 3, 4, 5), weights=(45, 30, 14, 7, 4))[0]
    chosen: list[Product] = []
    while len(chosen) < line_count:
        product = rng.choices(products, cum_weights=cumulative)[0]
        if product not in chosen and product.is_available(order_day):
            chosen.append(product)

    discount_probability = DISCOUNT_PROBABILITY.get(order_day.month, BASE_DISCOUNT_PROBABILITY)
    for product in chosen:
        quantity = rng.choices((1, 2, 3), weights=(80, 15, 5))[0]
        unit_price, _ = product.price_on(order_day)
        discount = 0.0
        if rng.random() < discount_probability:
            discount = _money(quantity * unit_price * rng.choice(DISCOUNT_RATES))
        item_id = f"OI{len(order_items) + 1:07d}"
        order_items.append(
            {
                "order_item_id": item_id,
                "order_id": order["order_id"],
                "product_id": product.product_id,
                "quantity": quantity,
                "unit_price": f"{unit_price:.2f}",
                "discount_amount": f"{discount:.2f}",
            }
        )
        if order["status"] == "completed" and rng.random() < product.category.return_rate:
            return_day = order_day + timedelta(days=rng.randint(3, 30))
            if return_day > PERIOD_END:
                continue
            returned_quantity = rng.randint(1, quantity)
            net_unit_price = unit_price - discount / quantity
            returns.append(
                {
                    "return_id": f"R{len(returns) + 1:06d}",
                    "order_item_id": item_id,
                    "return_date": return_day.isoformat(),
                    "quantity": returned_quantity,
                    "refund_amount": f"{_money(returned_quantity * net_unit_price):.2f}",
                    "reason": rng.choice(RETURN_REASONS),
                }
            )


def _product_row(product: Product) -> dict[str, object]:
    return {
        "product_id": product.product_id,
        "product_name": product.name,
        "category": product.category.name,
        "subcategory": product.subcategory,
        "brand": product.brand,
        "launched_on": product.launched_on.isoformat(),
        "discontinued_on": product.discontinued_on.isoformat() if product.discontinued_on else "",
    }


def _inject_defects(tables: dict[str, list[dict[str, object]]]) -> None:
    """Append the defective rows documented in data/sample/README.md."""
    customers = tables["customers"]
    customers.extend(dict(customers[i]) for i in (10, 250, 4000))
    customers.append({**customers[0], "customer_id": "C99001", "country": ""})
    customers.append({**customers[1], "customer_id": "C99002", "signup_date": "2024-02-30"})

    orders = tables["orders"]
    orders.extend(dict(orders[i]) for i in (5, 500, 1500, 3000, 6000))
    orders.append({**orders[0], "order_id": "O999001", "order_timestamp": "2024-13-45T10:00:00Z"})
    orders.append({**orders[1], "order_id": "O999002", "order_timestamp": "yesterday"})
    orders.append({**orders[2], "order_id": "O999003", "customer_id": ""})
    orders.append({**orders[3], "order_id": "O999004", "status": "pending_review"})

    items = tables["order_items"]
    items.extend(dict(items[i]) for i in (7, 700, 7000))
    items.append({**items[0], "order_item_id": "OI9999001", "quantity": "two"})
    items.append({**items[1], "order_item_id": "OI9999002", "quantity": -1})
    items.append({**items[2], "order_item_id": "OI9999003", "order_id": "O000000"})
    items.append({**items[3], "order_item_id": "OI9999004", "product_id": "P9999"})
    conflicting = dict(items[20])
    conflicting["quantity"] = int(conflicting["quantity"]) + 4
    items.append(conflicting)

    tables["returns"].append({**tables["returns"][0], "return_id": "R999001", "refund_amount": ""})


def write_dataset(dataset: Dataset, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name, columns in SCHEMAS.items():
        path = output_dir / f"{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(dataset.tables[name])
        paths[name] = path
    _append_malformed_line(paths["order_items"])
    logger.info("sample_data_written output_dir=%s rows=%s", output_dir, dataset.row_counts())
    return paths


def _append_malformed_line(path: Path) -> None:
    with path.open("a", newline="", encoding="utf-8") as handle:
        handle.write("OI9999005,O000001,P0001\n")
