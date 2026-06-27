.PHONY: up down build logs test shell-backend

up:
	docker compose up --build -d

down:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f

test:
	docker compose run --rm backend pytest -v --tb=short

shell-backend:
	docker compose exec backend bash

.DEFAULT_GOAL := up
