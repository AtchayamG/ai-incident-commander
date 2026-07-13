# Task Status

- Active milestone: M9 — OpenAI/Codex proof, reliability, and submission package
- Completed work: M0-M8, including the full safe incident workflow plus truthful onboarding, derived workflow metrics, explicit health states, accessible empty states, and responsive product polish
- Current task: finish the externally gated M9 submission steps; OpenAI Responses contract tests, five-run demo, full-history secret scan, complete local Docker browser proof, screenshots, and draft submission copy are complete, while credentialed OpenAI/Codex live smoke evidence is still not claimed
- Next three tasks: review official rules/categories when Devpost publishes them; record and upload the final demo video; add authorized repository/demo URLs and submit
- Blocked items: Devpost rules, categories, and submission form are not yet published/open; credentialed OpenAI/Codex smoke evidence requires authorized credentials and spend; video upload and final submission require the account holder
- Quality gates: backend ruff/strict mypy/156 tests pass (46 files); frontend lint/typecheck/20 tests and 6 contract tests pass; production build and 20 Chromium scenarios pass; five complete golden demos pass; Gitleaks reports no leaks across the full Git history
- Environment note: GNU Make is not installed on this Windows host, so its underlying documented commands were reproduced directly
- Latest successful commands: `uv run --project services/api ruff check services/api`, `uv run --project services/api mypy --strict services/api/app`, `uv run --project services/api pytest -q services/api/tests`, frontend typecheck/lint/Vitest/build, `pnpm --dir apps/web test:e2e`, `make demo-assert`, `gitleaks detect`, and the full Docker Compose browser workflow
