# Handover

- Exact continuation point: M0-M8 are integrated on `main`; M9 OpenAI/Codex integration and judge-demo UI are delegated in separate worktrees; the held M9 submission assets remain intentionally unintegrated until their claims can be reconciled with final evidence
- Current architecture: Next.js incident room + shared strict contracts; FastAPI/Pydantic state machine; SQLAlchemy/Alembic persistence; deterministic evidence/investigation/planning; two approval boundaries; isolated patch and verification workspaces; immutable patch/verification artifacts; deterministic risk review
- M7 proof: an exact second approval binds current passing verification and patch artifacts; resolution drafting is idempotent; demo mode is always simulated; failures are redacted and recoverable; communications and one evidence-linked postmortem persist; a real local-API browser path reaches RESOLUTION_DRAFTED
- Latest validation: backend ruff pass, strict mypy 44 files, pytest 149; frontend lint/typecheck, contract Vitest 6, web Vitest 20, production build, and Playwright 20 pass on integrated `main`
- Known limitations: network denial for the demo verifier is enforced by the immutable allowlisted offline harness rather than an OS egress filter; optional GitHub behavior is mocked only; meaningful OpenAI-provider/Codex proof, Docker/PostgreSQL proof, secret scan, and five-run demo reliability remain unproven
- Run commands: `make setup`, `make dev-api`, `make dev-web`, `make lint`, `make typecheck`, `make test`; on this host use the equivalent `uv run` and `pnpm` commands because GNU Make is absent
- Next action: inspect the Fable and agy M9 diffs, reproduce their focused gates, integrate backend and UI separately, then run five complete golden demos and a secret scan
- Persistent routing: orchestrate external agents; Fable 5 first, Opus 4.8 after Fable exhaustion; agy for frontend/UX; Codex reviews, reproduces gates, and integrates
