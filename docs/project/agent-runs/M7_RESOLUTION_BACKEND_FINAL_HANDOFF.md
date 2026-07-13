# M7 Resolution Backend Handoff

## Result

Status: backend implementation verified and ready for frontend-contract integration.

## Done

- Passing low/medium-risk verification creates one exact, expiring `CREATE_DRAFT_PR` approval and advances `REVIEW_READY -> WAITING_PR_APPROVAL`.
- The second approval validates state, binding, role, latest patch, passing verification hash, risk decision, and expiry before any action.
- Rejection returns to `REVIEW_READY` without an external action.
- The simulated default records one explicit offline draft-PR artifact.
- Stable idempotency is derived from action type, incident, patch, and verification artifact hash; it excludes the approval ID.
- Provider failure persists a redacted receipt, audits failure, renews one approval, and retries the same external-action row/key.
- Completed receipts are reused without another provider call.
- Draft-PR, communications, and postmortem API projections match the frontend contract.
- Communications and one evidence-linked postmortem are persisted and deterministically upserted.
- Three portable M7 tables are migrated: `external_actions`, `postmortems`, and `communications`.
- Demo mode always binds the simulated provider, even if ambient GitHub credentials exist.
- Optional GitHub behavior is fail-closed and mock-tested. It can create only a draft PR between explicitly configured, pre-existing head/base refs; it never pushes or merges and never includes the diff in the request body.

## Verification

- `uv run --project services/api ruff check services/api`: passed.
- `uv run --project services/api mypy --strict services/api/app`: passed, 44 source files.
- `uv run --project services/api pytest services/api/tests`: 149 passed; one upstream Starlette/httpx deprecation warning.
- Focused M7 tests: 15 passed.
- Real empty SQLite `alembic upgrade head`: revisions M0 through M7 applied successfully.
- Migration regression test inspects the three M7 tables and required unique indexes.
- `git diff --check`: passed.

## Blocked

- No M7 backend blocker.

## Risk

- Live GitHub was mock-tested only. It requires an externally prepared head ref and explicit live configuration; no credentialed network action was performed.
- Resolution artifacts describe a verified candidate and draft-PR artifact, not deployment, mitigation, merge, or incident closure.

## Next

1. Integrate this backend into main.
2. Rebase the verified M7 UI checkpoint onto the final API shapes and run the complete browser suite against the real local API.
3. Integrate the already verified M8 product-polish branch only after M7 passes.
