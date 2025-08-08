FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN --mount=type=cache,id=uv-cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . /app

RUN --mount=type=cache,id=uv-cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

RUN rm -f pyproject.toml uv.lock .python-version

FROM python:3.13-slim-bookworm

COPY --from=builder --chown=app:app /app /app

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "main.py"]
