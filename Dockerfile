# syntax = docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml .
COPY uv.lock .

RUN --mount=type=cache,id=s/66c88aaf-75d1-47f9-bbd9-5902c3d7e3e2,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY . /app

RUN --mount=type=cache,id=s/66c88aaf-75d1-47f9-bbd9-5902c3d7e3e2,target=/root/.cache/uv \
    uv sync --locked --no-dev

RUN rm -f pyproject.toml uv.lock .python-version

FROM python:3.13-slim-bookworm

COPY --from=builder /app /app

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

RUN chmod +x ./docker/*

CMD ["sh", "./docker/docker-entrypoint.sh"]