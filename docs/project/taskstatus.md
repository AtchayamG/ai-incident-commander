# Task Status

- Active milestone: M9 — OpenAI/Codex proof, reliability, and submission package
- Completed work: M0-M8, including the full safe incident workflow plus truthful onboarding, derived workflow metrics, explicit health states, accessible empty states, and responsive product polish
- Current task: implement and prove meaningful optional OpenAI reasoning and live Codex repository-work seams while preserving unconditional deterministic demo mode; improve the judge-facing demo UX in a non-overlapping worktree
- Next three tasks: integrate and verify the M9 provider/demo-UI work; prove five consecutive full golden runs and run the secret scan; finalize the submission package and reproducibility evidence
- Blocked items: none; live Codex/GitHub credentials remain optional and must not block deterministic demo mode
- Quality gates: backend ruff/strict mypy/149 tests pass; frontend lint/typecheck/20 tests pass; production build passes; all 20 Chromium scenarios pass; a real local-API browser flow proves patch approval → six passing verification/risk checks → separate PR approval → RESOLUTION_DRAFTED
- Environment note: GNU Make is not installed on this Windows host, so its underlying documented commands were reproduced directly
- Latest successful commands: `uv run --project services/api ruff check services/api`, `uv run --project services/api mypy --strict services/api/app`, `uv run --project services/api pytest -q services/api/tests`, frontend typecheck/lint/Vitest/build, and `pnpm --dir apps/web test:e2e`
