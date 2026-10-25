from __future__ import annotations

EMPTY = "n/a"


def currency(value: float | None) -> str:
    return EMPTY if value is None else f"{value:,.0f}"


def currency_precise(value: float | None) -> str:
    return EMPTY if value is None else f"{value:,.2f}"


def percent(value: float | None, digits: int = 1) -> str:
    return EMPTY if value is None else f"{value:.{digits}%}"


def integer(value: int | None) -> str:
    return EMPTY if value is None else f"{value:,}"


def change(current: float | None, previous: float | None) -> str | None:
    """Relative change for st.metric deltas, or None when there is nothing to compare with."""
    if current is None or previous in (None, 0):
        return None
    return f"{current / previous - 1:+.1%}"


def point_change(current: float | None, previous: float | None) -> str | None:
    """Difference between two rates in percentage points."""
    if current is None or previous is None:
        return None
    return f"{(current - previous) * 100:+.1f} pp"
