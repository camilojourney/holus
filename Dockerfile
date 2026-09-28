# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    HOLUS_PERSONAL_DELIVERY_GRANT=0 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Pin uv so dependency installation is reproducible alongside uv.lock.
RUN pip install --no-cache-dir uv==0.12.19

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY config ./config
COPY agentic ./agentic

RUN uv sync --frozen --no-dev \
    && mkdir -p data/content-queue data/lineage logs \
    && useradd --create-home --uid 10001 holus \
    && chown -R holus:holus /app /opt/venv

USER holus

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)" || exit 1

ENTRYPOINT ["uvicorn"]
CMD ["holus.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
