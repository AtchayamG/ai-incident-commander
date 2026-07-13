# Handover

- Exact continuation point: M0-M6 are integrated on `main`; M7 backend is next; `agent/m7-resolution-ui` is a partial UI checkpoint requiring Codex repair/reverification; `agent/m8-product-polish` is independently verified and intentionally held until M7 to preserve milestone order
- Current architecture: Next.js incident room + shared strict contracts; FastAPI/Pydantic state machine; SQLAlchemy/Alembic persistence; deterministic evidence/investigation/planning; two approval boundaries; isolated patch and verification workspaces; immutable patch/verification artifacts; deterministic risk review
- M6 proof: exact diff reconstruction in a fresh workspace, triple-authorized fixed argv checks, secret-free environment, bounded output/time, regression requirement, base-state failure classification, at most two repairs, risk PR blocking, SQL persistence/API projection, and cleanup proof
- Latest validation: backend ruff pass, strict mypy 43 files, pytest 134; frontend lint/typecheck, Vitest 20, production build, and Playwright 11 pass on integrated `main`
- Known limitations: network denial for the demo verifier is enforced by the immutable allowlisted offline harness rather than an OS egress filter; M7 external-action/communications/postmortem remain; Docker/PostgreSQL and five-run demo reliability remain unproven
- Run commands: `make setup`, `make dev-api`, `make dev-web`, `make lint`, `make typecheck`, `make test`; on this host use the equivalent `uv run` and `pnpm` commands because GNU Make is absent
- Next action: delegate and verify M7 backend, repair/rebase the M7 UI onto the resulting contracts, then integrate the verified M8 branch
- Persistent routing: orchestrate external agents; Fable 5 first, Opus 4.8 after Fable exhaustion; agy for frontend/UX; Codex reviews, reproduces gates, and integrates
