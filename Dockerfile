### ───────────────────────────────────────────────
### Builder stage
### ───────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN apk add --no-cache git bash

RUN apk add --no-cache gcc python3-dev musl-dev linux-headers


RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

RUN rm -f pyproject.toml uv.lock .python-version \
    && rm -rf /app/.cache

### ───────────────────────────────────────────────
### Runtime stage
### ───────────────────────────────────────────────
FROM python:3.13-alpine AS runtime

WORKDIR /app

COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"

RUN rm -rf /app/.venv/share/man \
    /app/.venv/lib/python*/test \
    /app/.venv/lib/python*/ensurepip \
    /app/.venv/lib/python*/distutils/tests \
    /app/.venv/lib/python*/tkinter \
    && chmod +x ./docker/*

EXPOSE 8000

CMD ["sh", "./docker/docker-entrypoint.sh"]
