# ADR 004: Docker Contract

## Status
Accepted (updated for M0 implementation)

## Context
We need a consistent development and execution environment.

## Decision
`docker compose up -d --build` (or `make docker-up`) is the one-command startup contract:

- `api` — FastAPI on :8000, `DEMO_MODE=true`, healthcheck on `/health/live`.
- `web` — Next.js on :3000, built from the repo root so the workspace contracts package resolves; waits for the API healthcheck.
- `postgres` / `redis` — declared under the `persistence` compose profile. They are NOT consumed by the M0 API (in-memory store) and only start with `--profile persistence`; M1 binds them without changing the local contract.

Native (non-Docker) development remains supported via `make setup`, `make dev-api`, `make dev-web`.

## Consequences
- Reviewers get the golden demo with Docker alone, no credentials.
- The compose file is the forward contract for M1 persistence; only the profile gate is removed when the API starts using Postgres/Redis.
