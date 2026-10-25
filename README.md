# MetricFlow

A production-style analytics engineering platform featuring dimensional modeling, dbt transformations, data quality testing, business metrics, and interactive BI dashboards.

MetricFlow turns raw order data from a fictional e-commerce business into trustworthy analytical models and consistent business metrics:

```
raw CSV files → validated ingestion → PostgreSQL raw schema → dbt staging → intermediate → star schema marts → metrics → Streamlit dashboard
```

## Technology stack

| Area | Tool |
| --- | --- |
| Language | Python 3.12 |
| Warehouse | PostgreSQL |
| Transformations | dbt Core with `dbt-postgres` |
| Data handling | pandas |
| Dashboard | Streamlit, Plotly |
| Testing | pytest, dbt tests |
| Code quality | Ruff, SQLFluff |

Exact pinned versions live in [`requirements.txt`](requirements.txt) and [`requirements-dev.txt`](requirements-dev.txt).

## Local development

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e . --no-deps
cp .env.example .env               # then edit the connection settings
```

Run the checks:

```bash
ruff check .
pytest
```

## License

Released under the [MIT License](LICENSE).
