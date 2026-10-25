import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from metricflow_platform.config import PROJECT_ROOT
from metricflow_platform.database import connect

pytestmark = pytest.mark.integration

APP = str(PROJECT_ROOT / "dashboard" / "app.py")


@pytest.fixture(scope="module")
def marts_built(base_settings):
    with connect(base_settings.database) as conn:
        if conn.execute("select to_regclass('marts.fct_order_items')").fetchone()[0] is None:
            pytest.skip("dbt marts have not been built")


def test_dashboard_renders_all_tabs_without_errors(marts_built):
    app = AppTest.from_file(APP, default_timeout=120).run()

    assert not app.exception
    assert not app.error
    assert [tab.label for tab in app.tabs] == [
        "Overview",
        "Trends",
        "Products & categories",
        "Customers",
    ]
    labels = [metric.label for metric in app.metric]
    assert "Net revenue" in labels
    assert "Repeat-purchase rate" in labels


def test_category_filter_changes_kpis(marts_built):
    app = AppTest.from_file(APP, default_timeout=120).run()
    unfiltered = next(m.value for m in app.metric if m.label == "Net revenue")

    app.multiselect[0].select("Books").run()

    filtered = next(m.value for m in app.metric if m.label == "Net revenue")
    assert not app.exception
    assert float(filtered.replace(",", "")) < float(unfiltered.replace(",", ""))


def test_unreachable_database_shows_error(monkeypatch, marts_built):
    monkeypatch.setenv("METRICFLOW_DB_PORT", "1")
    st.cache_data.clear()

    app = AppTest.from_file(APP, default_timeout=120).run()

    assert not app.exception
    assert any("Cannot reach PostgreSQL" in element.value for element in app.error)
