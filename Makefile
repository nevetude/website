.PHONY: dev backend frontend reset

# The whole project in one terminal: the database, then the API (:8000) and the site (:8080) side by side.
# Ctrl+C stops both. The migrations run first, so a fresh database is ready to use.
dev:
	docker compose up -d --wait db
	$(MAKE) --no-print-directory -j2 backend frontend

backend:
	cd backend && uv run alembic upgrade head && uv run fastapi dev

frontend:
	cd frontend && pnpm dev

# A clean database: the volume of the compose database is deleted (nothing else can be touched, so no question and
# no check of the host), then the migrations build the tables again. Stop the backend first.
reset:
	docker compose down -v
	docker compose up -d --wait db
	cd backend && uv run alembic upgrade head
