# Incident Commander AI

AI incident commander for small engineering teams: evidence-grounded diagnosis, human-approved remediation, verified patches. Blueprint: `docs/AI_INCIDENT_COMMANDER_MASTER_BLUEPRINT_v1.md`.

**Status: M0 — foundation and contracts.** Deterministic demo mode only; no external credentials required or used.

## Layout

| Path | What |
|---|---|
| `services/api` | Python 3.12 FastAPI backend (Pydantic v2, strict mypy, ruff, pytest) |
| `apps/web` | Next.js 14 App Router frontend (strict TypeScript, vitest) |
| `packages/contracts` | Shared TypeScript contract types mirroring the backend Pydantic models |
| `docs/adr` | ADRs 001-007 |
| `docs/architecture` | System context, state machine, security model, demo architecture |

## Quick start

Docker (one command):

```bash
make docker-up        # or: docker compose up -d --build
# web: http://localhost:3000   api: http://localhost:8000/docs
```

Native:

```bash
make setup            # pnpm install + backend venv (Python 3.12) + dev deps
make dev-api          # FastAPI on :8000
make dev-web          # Next.js on :3000 (second terminal)
```

## Quality gates

```bash
make lint             # ruff + next lint + tsc
make typecheck        # mypy --strict + tsc --noEmit
make test             # pytest (35 tests) + vitest (contracts + web)
```

CI (`.github/workflows/ci.yml`) enforces all three plus the web build on every push/PR to `main`.

## Golden demo (no credentials)

```bash
curl -X POST localhost:8000/api/v1/incidents/inc-demo-0001/start
curl localhost:8000/api/v1/incidents/inc-demo-0001/approvals
curl -X POST localhost:8000/api/v1/approvals/<approval_id>/decision \
  -H 'Content-Type: application/json' \
  -d '{"decision": "approved", "reason": "Bounded patch approved"}'
curl localhost:8000/api/v1/incidents/inc-demo-0001   # state: REVIEW_READY
```

Reset: `curl -X POST localhost:8000/api/v1/incidents/reset-demo -H 'X-Demo-Admin-Key: demo-admin-key'`

See `docs/architecture/demo-architecture.md` for the full walkthrough.

## Principles (enforced from M0)

- Evidence passes a redaction boundary before persistence — raw payloads never do.
- Workflow state changes only through the deterministic state machine; model output is a typed proposal.
- External effects (patches, PRs) require recorded human approval.
- Simulated data is always labelled simulated.
