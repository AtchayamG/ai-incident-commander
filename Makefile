# Developer contract. Every target must stay runnable on a fresh clone.
# Backend commands assume the venv created by `make setup` (services/api/.venv).

PY := services/api/.venv/Scripts/python
ifeq ($(OS),Windows_NT)
PY := services/api/.venv/Scripts/python
else
PY := services/api/.venv/bin/python
endif

.PHONY: bootstrap setup dev dev-api dev-web lint typecheck test eval secret-scan demo-reset demo-run demo-assert openai-smoke docker-up docker-down

bootstrap: setup

setup:
	pnpm install
	python -m venv services/api/.venv || py -3.12 -m venv services/api/.venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e "services/api[dev]"

dev-api:
	cd services/api && ./.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000 || \
		./.venv/bin/python -m uvicorn app.main:app --reload --port 8000

dev-web:
	pnpm --filter @incident-commander/web dev

dev:
	docker compose up --build

lint:
	cd services/api && $(abspath $(PY)) -m ruff check .
	pnpm -r run lint

typecheck:
	cd services/api && $(abspath $(PY)) -m mypy
	pnpm -r run typecheck

test:
	cd services/api && $(abspath $(PY)) -m pytest
	pnpm -r run test

eval:
	cd services/api && $(abspath $(PY)) -m app.evals.runner

secret-scan:
	gitleaks detect --source . --redact --no-banner --exit-code 1

demo-reset:
	cd services/api && $(abspath $(PY)) -m app.demo.runner --reset-only

demo-run:
	cd services/api && $(abspath $(PY)) -m app.demo.runner --runs 1

demo-assert:
	cd services/api && $(abspath $(PY)) -m app.demo.runner --runs 5

openai-smoke:
	cd services/api && $(abspath $(PY)) -m app.demo.openai_smoke --model gpt-5.6

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down
