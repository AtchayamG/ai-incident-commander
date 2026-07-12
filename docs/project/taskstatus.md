# Task Status

- Active milestone: M6 — deterministic sandbox verification and review
- Completed work: M0-M5, including typed investigation, immutable bounded remediation plans, artifact-bound approval, accessible approval UX, isolated fixture workspaces, deterministic candidate patching, real Codex CLI adapter behind a fail-closed gateway, diff capture, persistence, and cleanup proof
- Current task: replace simulated verification with an allowlisted network-denied runner, bounded repair loop, structured failure classification, deterministic risk review, and real REVIEW_READY/PATCH_FAILED evidence
- Next three tasks: integrate M6 backend and real browser proof; implement M7 simulated draft PR/communications/postmortem; complete M8-M9 reliability and submission package
- Blocked items: none; live Codex/GitHub credentials remain optional and must not block deterministic demo mode
- Quality gates: backend ruff/strict mypy/120 tests pass; frontend lint/typecheck/20 tests pass; production build passes; all 10 Chromium scenarios pass; M5 approval-to-isolated-patch flow is integrated
- Environment note: GNU Make is not installed on this Windows host, so its underlying documented commands were reproduced directly
- Latest successful commands: `uv run ruff check .`, `uv run mypy --strict app`, `uv run pytest -q`, frontend typecheck/lint/Vitest/build, and `pnpm --dir apps/web run test:e2e`
