date = $(shell date)

migration:
	uv run alembic revision --autogenerate -m "Revision ($(date))"

migrate:
	uv run alembic upgrade head

erd:
	uv run python scripts/generate_erd.py

lint:
	uv run ruff check --config=pyproject.toml .

format:
	uv run ruff format --config=pyproject.toml .

.PHONY: migration migrate