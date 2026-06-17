FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY resolveops_core ./resolveops_core
COPY services ./services
COPY scripts ./scripts
COPY tests ./tests

RUN pip install --no-cache-dir -e ".[dev]"

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
