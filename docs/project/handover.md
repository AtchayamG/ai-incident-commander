# Handover

- Exact continuation point: start M2 evidence/timeline implementation after complete M1 browser verification
- Current architecture: Next.js web app + shared TypeScript contracts; FastAPI/Pydantic API with explicit state machine, SQLAlchemy SQLite demo persistence, Alembic, webhook intake, SSE events, simulated providers, redaction, and deterministic demo pipeline
- Run commands: `make setup`, `make dev-api`, `make dev-web`, `make lint`, `make typecheck`, `make test`, `make docker-up`
- Latest validation: ruff pass; strict mypy pass (36 files); pytest 39 passed; frontend lint/typecheck pass; vitest 15 passed; Next build passes on Windows with supported worker-thread configuration
- Known limitations: Docker startup and PostgreSQL mode not yet exercised; M2 evidence bundle is still partial; live integrations remain intentionally disabled
- External credentials: OpenAI and GitHub optional for live mode; deterministic demo must run without them
- Next action: implement M2 deterministic evidence providers, provenance, Git/deployment correlation, timeline, and tests
- Persistent delegation policy: use `orchestrate-external-coding-agents`; Claude Fable 5 first, then Opus 4.8 after Fable exhaustion; agy for UI/UX/frontend integration; Hermes as authenticated fallback; Codex integrates and verifies.
