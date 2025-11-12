### ───────────────────────────────────────────────
### Builder stage
### ───────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

RUN rm -f pyproject.toml uv.lock .python-version


### ───────────────────────────────────────────────
### Runtime stage
### ───────────────────────────────────────────────
FROM python:3.13-slim-bookworm AS runtime

WORKDIR /app

COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"

RUN chmod +x ./docker/* \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man

CMD ["sh", "./docker/docker-entrypoint.sh"]
