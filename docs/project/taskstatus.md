# Task Status

- Active milestone: M7 — approved draft PR, communications, and postmortem
- Completed work: M0-M6, including typed investigation, immutable bounded remediation plans, artifact-bound approval, isolated candidate patching, byte-exact deterministic verification, bounded repair/failure classification, risk-based PR blocking, SQL persistence, and real-browser REVIEW_READY proof
- Current task: implement the simulated-first idempotent draft-PR adapter, second approval transition, technical/stakeholder updates, and evidence-based postmortem; the agy UI branch is partial and remains unintegrated after an out-of-scope test edit was stopped
- Next three tasks: complete and verify M7 backend/UI; integrate the already verified M8 product-polish branch; complete M9 five-run reliability, secret scan, and submission package
- Blocked items: none; live Codex/GitHub credentials remain optional and must not block deterministic demo mode
- Quality gates: backend ruff/strict mypy/134 tests pass; frontend lint/typecheck/20 tests pass; production build passes; all 11 Chromium scenarios pass; a real local-API browser flow proves approval → patch → six passing verification/risk checks → REVIEW_READY
- Environment note: GNU Make is not installed on this Windows host, so its underlying documented commands were reproduced directly
- Latest successful commands: `uv run --project services/api ruff check services/api`, `uv run --project services/api mypy --strict services/api/app`, `uv run --project services/api pytest -q services/api/tests`, frontend typecheck/lint/Vitest/build, and `pnpm --dir apps/web test:e2e`
