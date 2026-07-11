# ADR 002: Backend Framework

## Status
Accepted (updated for M0 implementation)

## Context
We need a performant, typed, and modern backend for orchestrating agent workflows and APIs.

## Decision
Python 3.12, FastAPI, and Pydantic v2. Concrete M0 shape:

- App factory (`app.main.create_app`) wires settings, store, providers, and the workflow pipeline; nothing binds at import time except the default app for uvicorn.
- All request/response bodies are Pydantic models in `app/domain/contracts.py` with `extra="forbid"` so contract drift returns 422 instead of passing silently.
- Workflow state changes go exclusively through `app/workflow/state_machine.py`; provider/agent output is a typed proposal that deterministic code evaluates (blueprint section 11.3).
- M0 persistence is an in-memory store (`app/store/memory.py`) whose method surface anticipates the SQLAlchemy repository arriving in M1, so routes and pipeline code do not change when Postgres lands.
- Quality gates: `ruff check`, `mypy --strict`, `pytest` — all enforced in CI with no soft-fail.

## Consequences
- Strong typing and automatic OpenAPI generation.
- In-memory state means restarts lose data in M0; acceptable because demo reset re-seeds deterministically.
- OpenAI Agents SDK / Codex SDK integration (M3-M5) plugs in behind the provider protocols without touching domain or route code.
