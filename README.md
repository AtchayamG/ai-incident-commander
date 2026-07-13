# Incident Commander AI

AI incident commander for small engineering teams: evidence-grounded diagnosis, human-approved remediation, verified patches. Blueprint: `docs/AI_INCIDENT_COMMANDER_MASTER_BLUEPRINT_v1.md`.

**Status: M9 — submission hardening.** M0–M8 are integrated. The deterministic demo completes the two-approval workflow through an explicitly simulated draft-PR package, communications, and an evidence-linked postmortem. No external credentials are required.

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
make test             # backend, shared-contract, and web tests
make secret-scan      # Gitleaks over current tree and Git history
make demo-assert      # five complete deterministic demo runs
```

CI (`.github/workflows/ci.yml`) enforces all three plus the web build on every push/PR to `main`.

## Golden demo (no credentials)

```bash
make demo-reset       # verify protected reset and RECEIVED seed state
make demo-run         # one full run through RESOLUTION_DRAFTED
make demo-assert      # five consecutive asserted runs
```

On Windows hosts without GNU Make, run the underlying command directly:

```powershell
uv run --project services/api python -m app.demo.runner --runs 5
```

Every run uses an ephemeral SQLite database, fixture investigation, and the fixture code-agent. It exercises both public approval endpoints and asserts `RESOLUTION_DRAFTED`, simulated provider provenance, communications, and the evidence-linked postmortem. It never contacts OpenAI or GitHub.

See `docs/architecture/demo-architecture.md` for the full walkthrough.

## Verified baseline

- Backend: Ruff and strict mypy pass across 46 source files; 156 tests pass.
- Frontend: lint, strict typecheck, 20 web tests, 6 shared-contract tests, and production build pass.
- Browser: 20 Chromium scenarios pass, including a real local-API flow through both approvals.
- Optional live integrations fail closed and never replace deterministic demo mode. Live credentialed proof is documented separately and is not implied by fixture artifacts.

See [task status](docs/project/taskstatus.md), [evidence checklist](docs/submission/evidence-checklist.md), and [demo script](docs/submission/demo-script.md) for current proof and remaining limitations.

## Principles

- Evidence passes a redaction boundary before persistence — raw payloads never do.
- Workflow state changes only through the deterministic state machine; model output is a typed proposal.
- External effects (patches, PRs) require recorded human approval.
- Simulated data is always labelled simulated.
