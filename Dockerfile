FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY pyproject.toml README.md ./
COPY src ./src
# Editable install keeps the package anchored to /app, where it finds dbt/, data/ and .streamlit/.
RUN pip install --no-deps -e .

COPY data ./data
COPY dbt ./dbt
COPY dashboard ./dashboard
COPY .streamlit ./.streamlit

RUN useradd --create-home --uid 1000 metricflow \
    && chown -R metricflow:metricflow /app
USER metricflow

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
