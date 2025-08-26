date = $(shell date)

migration:
	alembic revision --autogenerate -m "Revision ($(date))"

migrate:
	alembic upgrade head

run:
	uv run main.py

up:
	docker-compose up

down:
	docker-compose down

build:
	docker-compose build

.PHONY: migration migrate run up down build