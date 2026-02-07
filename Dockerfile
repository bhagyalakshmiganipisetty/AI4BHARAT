# Multi-stage build
FROM python:3.12-slim AS builder
WORKDIR /app
ARG INSTALL_DEV=false
ENV PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=off \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY pyproject.toml poetry.lock ./
RUN pip install --upgrade pip poetry && poetry config virtualenvs.create false && \
    if [ "$INSTALL_DEV" = "true" ]; then poetry install --no-root --with dev; else poetry install --no-root --only main; fi

FROM python:3.12-slim
WORKDIR /app
RUN useradd -u 10001 -m appuser
ENV PATH="/home/appuser/.local/bin:$PATH"
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD curl -f http://localhost:8000/health/live || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
