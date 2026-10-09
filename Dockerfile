# Этап 1: сборка
FROM python:3.12-slim AS builder

WORKDIR /app

# Отдельное окружение для Poetry
RUN python -m venv /opt/poetry-venv \
    && /opt/poetry-venv/bin/pip install --no-cache-dir poetry==2.5.1

# Отдельное окружение для приложения
RUN python -m venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml poetry.lock ./

RUN /opt/poetry-venv/bin/poetry config virtualenvs.create false \
    && /opt/poetry-venv/bin/poetry install --only main --no-root --no-interaction


# Этап 2: runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY --from=builder /opt/venv /opt/venv

COPY src ./src
COPY products.txt .

CMD ["python", "src/price_parser/parser.py"]