# syntax = docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml .
COPY uv.lock .

RUN --mount=type=cache,id=s/fc583318-4860-4485-9d22-4802980b51bf,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY . /app

RUN --mount=type=cache,id=s/fc583318-4860-4485-9d22-4802980b51bf,target=/root/.cache/uv \
    uv sync --locked --no-dev

RUN rm -f pyproject.toml uv.lock .python-version

FROM python:3.13-slim-bookworm

# У базовому образі python:3.13-slim немає користувача "app" — це не критично для кешу,
# але може зламати COPY --chown. Можна прибрати chown або створити користувача.
COPY --from=builder /app /app

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

RUN chmod +x ./docker/*

CMD ["sh", "./docker/docker-entrypoint.sh"]