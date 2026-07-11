# Handover

- Exact continuation point: M1 after independently verified M0 integration; repair Windows Next.js build teardown before expanding UI
- Current architecture: Next.js web app + shared TypeScript contracts; FastAPI/Pydantic API with explicit state machine, simulated providers, redaction, in-memory store, and deterministic demo pipeline
- Run commands: `make setup`, `make dev-api`, `make dev-web`, `make lint`, `make typecheck`, `make test`, `make docker-up`
- Latest validation: ruff pass; strict mypy pass (32 files); pytest 35 passed; frontend lint/typecheck pass; vitest 13 passed; Next build compiles/pages generate then exits 1 with Windows `kill EPERM`
- Known limitations: in-memory persistence; no webhook/SSE/detail screen; Docker not independently validated; production build exit remains failing on Windows
- External credentials: OpenAI and GitHub optional for live mode; deterministic demo must run without them
- Next action: diagnose/fix the frontend build exit, then implement M1 persistence and incident intake
- Persistent delegation policy: use `orchestrate-external-coding-agents`; Claude Fable 5 first, then Opus 4.8 after Fable exhaustion; agy for UI/UX/frontend integration; Hermes as authenticated fallback; Codex integrates and verifies.
