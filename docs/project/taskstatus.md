# Task Status

- Active milestone: M8 — product polish and operator usability
- Completed work: M0-M7, including typed investigation, immutable bounded remediation plans, two artifact-bound approval boundaries, isolated candidate patching, byte-exact deterministic verification, bounded repair/failure classification, risk-based PR blocking, idempotent simulated-first resolution drafting, communications, evidence-linked postmortem, SQL persistence, and real-browser RESOLUTION_DRAFTED proof
- Current task: integrate the already verified M8 product-polish branch while preserving all M7 resolution controls and evidence views
- Next three tasks: integrate and reverify M8; implement and prove meaningful OpenAI-provider/Codex usage; complete M9 five-run reliability, secret scan, and submission package
- Blocked items: none; live Codex/GitHub credentials remain optional and must not block deterministic demo mode
- Quality gates: backend ruff/strict mypy/149 tests pass; frontend lint/typecheck/20 tests pass; production build passes; all 16 Chromium scenarios pass; a real local-API browser flow proves patch approval → six passing verification/risk checks → separate PR approval → RESOLUTION_DRAFTED
- Environment note: GNU Make is not installed on this Windows host, so its underlying documented commands were reproduced directly
- Latest successful commands: `uv run --project services/api ruff check services/api`, `uv run --project services/api mypy --strict services/api/app`, `uv run --project services/api pytest -q services/api/tests`, frontend typecheck/lint/Vitest/build, and `pnpm --dir apps/web test:e2e`
