PYTHON ?= python
CLI = $(PYTHON) -m metricflow_platform

.PHONY: help install sample-data init-db ingest dbt-build dbt-test pipeline dashboard \
	lint format test test-unit screenshots docker-up docker-down docker-reset

help:
	@echo "install      Install runtime and development dependencies"
	@echo "sample-data  Regenerate the synthetic dataset in data/sample"
	@echo "init-db      Create the raw schema and metadata tables"
	@echo "ingest       Validate and load the source CSV files"
	@echo "dbt-build    Build and test all dbt models"
	@echo "pipeline     ingest + dbt-build"
	@echo "dashboard    Start the Streamlit dashboard"
	@echo "lint         Run Ruff and SQLFluff"
	@echo "test         Run all pytest suites (integration tests need PostgreSQL)"
	@echo "test-unit    Run tests that do not need a database"
	@echo "docker-up    Start PostgreSQL, run the pipeline and serve the dashboard"
	@echo "docker-down  Stop the containers"
	@echo "docker-reset Stop the containers and delete the database volume"

install:
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PYTHON) -m pip install --no-deps -e .

sample-data:
	$(CLI) generate-sample-data

init-db:
	$(CLI) init-db

ingest:
	$(CLI) ingest

dbt-build:
	$(CLI) dbt build

dbt-test:
	$(CLI) dbt test

pipeline: ingest dbt-build

dashboard:
	$(PYTHON) -m streamlit run dashboard/app.py

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m sqlfluff lint dbt sql

format:
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

test:
	$(PYTHON) -m pytest

test-unit:
	$(PYTHON) -m pytest -m "not integration"

screenshots:
	$(PYTHON) scripts/capture_screenshots.py

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-reset:
	docker compose down --volumes
