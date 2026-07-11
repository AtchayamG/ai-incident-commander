# ADR 001: Monorepo Structure

## Status
Accepted (updated for M0 implementation)

## Context
We need a scalable repository structure that can house the backend, frontend, and shared packages for Incident Commander AI.

## Decision
We use a pnpm workspace monorepo with three top-level code roots:

- `apps/web` — Next.js frontend (`@incident-commander/web`)
- `packages/contracts` — shared TypeScript contract types (`@incident-commander/contracts`), a hand-maintained mirror of the backend Pydantic contracts
- `services/api` — Python FastAPI backend with its own venv and `pyproject.toml`

This deviates from the blueprint section 27 sketch (`frontend/`, `backend/`): the `apps/packages/services` layout is the established convention in this worktree and generalizes better when the worker and sandbox-runner services land (M4+). Contract mirroring is enforced socially plus by parity tests on both sides (`services/api/tests/test_state_machine.py`, `packages/contracts/src/state-machine.test.ts`).

## Consequences
- Single source of truth per language; TS types and Pydantic models must change in the same commit.
- `Makefile` bridges Python and JS task runners (`make lint|typecheck|test`).
- Code generation of TS types from OpenAPI can replace the hand-maintained mirror later without changing consumers.
