# Handover

- Exact continuation point: M0-M5 are integrated on `main`; Claude Fable is implementing the M6 real verifier in `agent/m6-verification`; agy is implementing M8 frontend polish in `agent/m8-product-polish`
- Current architecture: Next.js incident room + shared strict contracts; FastAPI/Pydantic state machine; SQLAlchemy/Alembic persistence; deterministic evidence/investigation/planning; one-time artifact-bound approvals; isolated workspace executor; fixture and fail-closed live Codex gateways; immutable patch execution artifacts
- M5 proof: source fixture manifest verification, read-only-until-approval workspace, allowed paths/change budgets/network denial/secret-free subprocess environment, candidate regression patch, unified diff capture, cleanup on every path, and explicit simulated/live provenance
- Latest validation: backend ruff pass, strict mypy 39 files, pytest 120; frontend lint/typecheck, Vitest 20, production build, and Playwright 10 pass on integrated `main`
- Known limitations: verification runner is still simulated until M6 integration; real PR/communications/postmortem are M7; Docker/PostgreSQL and five-run demo reliability remain unproven
- Run commands: `make setup`, `make dev-api`, `make dev-web`, `make lint`, `make typecheck`, `make test`; on this host use the equivalent `uv run` and `pnpm` commands because GNU Make is absent
- Next action: verify/integrate M6, add a real local-API approval→patch→verification→review browser scenario, then start M7
- Persistent routing: orchestrate external agents; Fable 5 first, Opus 4.8 after Fable exhaustion; agy for frontend/UX; Codex reviews, reproduces gates, and integrates
