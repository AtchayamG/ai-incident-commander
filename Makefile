.PHONY: setup dev test lint build docker-up docker-down

setup:
	pnpm install
	cd services/api && pip install -r requirements.txt
	cd services/api && pip install pytest flake8 mypy httpx

dev:
	# Starts backend and frontend
	cd services/api && uvicorn main:app --reload --port 8000 &
	cd apps/web && pnpm dev &

test:
	cd services/api && pytest
	cd apps/web && pnpm test

lint:
	cd services/api && flake8 . && mypy .
	cd apps/web && pnpm lint

docker-up:
	docker-compose up -d --build

docker-down:
	docker-compose down
