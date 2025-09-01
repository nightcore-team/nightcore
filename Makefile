date = $(shell date)

migration:
	alembic revision --autogenerate -m "Revision ($(date))"

migrate:
	alembic upgrade head

.PHONY: migration migrate