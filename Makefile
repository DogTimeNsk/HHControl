.PHONY: up down logs admin_add test

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

admin_add:
	docker compose run --rm api sh -c "alembic upgrade head && python -m app.cli"

test:
	docker compose run --rm api sh -c "uv pip install --system '.[dev]' && pytest"
