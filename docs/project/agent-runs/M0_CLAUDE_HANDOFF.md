# Agent Handoff — M0 Foundation (architecture/backend)

Date: 2026-07-12 · Branch: `agent/m0-claude` · Worktree: `.agent-worktrees/incident-m0-claude`

## What was delivered

M0 repository foundation per the blueprint (`docs/AI_INCIDENT_COMMANDER_MASTER_BLUEPRINT_v1.md`) and execution index, plus the earliest P0 golden-path slice running end-to-end in deterministic demo mode.

### Backend (`services/api`, Python 3.12 / FastAPI / Pydantic v2)

- `app/domain/` — enums + strict contracts (`extra="forbid"`) for incidents, evidence, timeline, hypotheses, plans, patches, verification, approvals, workflow events. Single source of truth; TS mirror in `packages/contracts`.
- `app/workflow/state_machine.py` — full blueprint section 11 transition map, terminal/recoverable sets, approval-gated pairs (`WAITING_PATCH_APPROVAL→PATCHING`, `WAITING_PR_APPROVAL→CREATING_PR`). Only this module authorizes state changes.
- `app/workflow/pipeline.py` — deterministic golden-path orchestration: start → evidence (redacted) → hypothesis → plan → approval gate; approve → patch (change-budget enforced) → verify → `REVIEW_READY`; reject → `CANCELLED`. Appends a workflow event per transition.
- `app/providers/` — `runtime_checkable` Protocols (telemetry, investigation, code agent, verification, PR) + deterministic simulated implementations. Fixture log plants a secret to prove redaction. All output labelled `[SIMULATED]`.
- `app/security/redaction.py` — redaction boundary (private keys, sk-/AKIA/gh tokens, bearer, URL creds, assigned secrets, emails); applied to every provider payload before persistence.
- `app/store/memory.py` — in-memory repository shaped like the future SQLAlchemy repo (M1 swap without route changes).
- `app/api/routes/` — health (`/health/live|ready|dependencies`), incidents (`/api/v1/incidents` CRUD-lite, start, cancel, reset-demo, evidence/timeline/hypotheses/plans/patches/verifications/approvals/events), approvals decision endpoint with pending/expiry/artifact-version checks.
- `app/main.py` — app factory; `DEMO_MODE=false` raises `NotImplementedError` (live providers are M4-M7); golden incident `inc-demo-0001` seeded at startup.

### Frontend (`apps/web` + `packages/contracts`)

- `packages/contracts` — TS mirror of all contracts incl. `TRANSITIONS` map, type guards, parity tests.
- `apps/web` — Next.js 14.2, strict tsconfig (`noUncheckedIndexedAccess` etc.), typed non-throwing API client (`lib/api.ts`, `ApiResult<T>`), dynamic server-component dashboard listing incidents with graceful API-down state, vitest tests.

### Infra / governance

- `Makefile` (setup/dev-api/dev-web/lint/typecheck/test/docker-up/down), `docker-compose.yml` (api healthchecked, web depends_on healthy; postgres+redis behind `persistence` profile for M1), Dockerfiles, `.env.example` (credential-free defaults), `.gitignore`, `README.md`.
- CI `.github/workflows/ci.yml`: backend ruff + mypy strict + pytest (py3.12); frontend pnpm lint + typecheck + test + web build (Node 22). No soft-fails (the previous `mypy || true` is gone).
- ADRs 001-007 updated with implemented decisions and recorded deviations; `docs/architecture/` (system-context, workflow-state-machine, security-model, demo-architecture).

## Gate results (executed in this worktree, 2026-07-12)

| Gate | Command | Result |
|---|---|---|
| Backend lint | `.venv/Scripts/python -m ruff check .` | PASS ("All checks passed!") |
| Backend typecheck | `.venv/Scripts/python -m mypy` (strict) | PASS ("no issues found in 32 source files") |
| Backend tests | `.venv/Scripts/python -m pytest` | PASS (35 passed) |
| Frontend lint | `pnpm -r run lint` | PASS (tsc + next lint clean) |
| Frontend typecheck | `pnpm -r run typecheck` | PASS |
| Frontend tests | `pnpm -r run test` | PASS (contracts 6, web 7) |
| Web build | `pnpm --filter @incident-commander/web build` | Compiled + 4/4 pages generated; process exits 1 on Windows from a known Next jest-worker `kill EPERM` teardown bug (artifacts verified: `.next/BUILD_ID` present). CI on ubuntu gates the clean exit. |
| Local startup smoke | uvicorn on :8123 → `/health/live`, `/health/dependencies`, seed listed, `start` → `WAITING_PATCH_APPROVAL`, pending `APPLY_PATCH` approval | PASS (server stopped afterwards) |

Not executed: `docker compose up` (image builds not run in this session), GitHub Actions (no push). Do not claim those pass until run.

## Known deviations from blueprint (recorded in ADRs)

1. Layout is `apps/ packages/ services/` not `frontend/ backend/` (pre-existing worktree convention; ADR 001).
2. `reset-demo` is store-global (`POST /api/v1/incidents/reset-demo`), not per-incident — single demo tenant in M0 (ADR 005).
3. M0 store is in-memory; Postgres/Redis provisioned in compose behind the `persistence` profile but unused until M1 (ADR 002/004).

## Environment notes for the next agent

- Backend venv: `services/api/.venv` (Python 3.12.10 via `py -3.12`). System default python is 3.11/3.14 — do not use for this package (`requires-python >=3.12`).
- Vitest must run with `pool: "threads"` (pinned in both `vitest.config.ts`); the default forks pool crashes tinypool on this Windows path (contains spaces).
- Governance files (`taskstatus.md`, `BUILD_STATUS.json`, `handover.md`, `AGENTS.md`) were NOT modified — outside this task's allowed file list; orchestrator should update them from the gate table above.

## Exact continuation point (M1 — incident intake and dashboard)

1. Add SQLAlchemy 2 + Alembic; implement a Postgres-backed store with the same surface as `InMemoryStore`; drop the compose `persistence` profile gate.
2. Generic webhook intake (`POST /webhooks/{provider}`) with signature verification hook.
3. Incident creation form + incident detail page in `apps/web`; wire TanStack Query.
4. SSE endpoint (`GET /incidents/{id}/events` streaming) — event contract already defined in `WorkflowEvent`.
5. E2E test: incident created through UI persists and appears on dashboard (M1 gate).
