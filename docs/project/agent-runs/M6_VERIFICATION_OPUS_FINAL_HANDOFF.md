# M6 Verification — Opus Final Handoff

Continues the Fable checkpoint (commit `496a3b4`) without restarting it. All
Fable-authored M6 modules were kept; the gaps that left six failing tests and
an unwired verifier were closed.

## DONE

### Single strict typed verifier protocol (fixes the six failures)
- Added `Verifier` protocol (`app/sandbox/verifier.py`): the one contract the
  pipeline depends on — `verify(incident, execution, patch_id, attempt) ->
  VerificationRunArtifact`. `DeterministicVerifier` is the sole production
  implementation.
- `WorkflowPipeline` now types its `verifier` parameter as `Verifier` (was the
  concrete class).
- Deleted the legacy `SimulatedVerificationRunner`, the old
  `VerificationRunner` protocol, and its `VerificationCheckResult` type
  (`app/providers/simulated.py`, `app/providers/base.py`). The stale
  two-argument `verify(incident, diff)` contract is gone; nothing references
  it anymore.
- Wired the real verifier in `app/main.py`:
  `DeterministicVerifier(store=store, environ=dict(os.environ))`. The
  environment is copied once so the runner's own allowlist — not the parent
  process — decides what check subprocesses see.
- Migrated every test double: `test_remediation.py`, `test_investigation.py`,
  and `test_providers.py` now use `DeterministicVerifier` / assert against the
  `Verifier` protocol.

### Real, deterministic verification (already present from Fable, now exercised)
- The captured candidate diff is reconstructed byte-exact in a fresh ephemeral
  workspace from the immutable fixture base; if reconstruction is not
  byte-identical, nothing runs.
- Checks run through the strict `CommandRunner`: no shell, fixed absolute argv,
  environment allowlist, cwd confinement, per-command timeout, and bounded
  redacted stdout/stderr, under a total budget. Commands are triple-authorized
  (policy baseline, plan allowlist, repository manifest) before any process
  exists.
- Failures are classified with immutable base-state evidence: patch issue vs
  pre-existing failure vs environment issue. Only a `PATCH_ISSUE` may re-enter
  the bounded repair loop (`MAX_REPAIR_ATTEMPTS = 2`, additionally capped by
  the plan attempt budget). Any failed/incomplete verification or a risk block
  ends `PATCH_FAILED`; only all-pass plus acceptable risk reaches
  `REVIEW_READY`. Confirmed end to end on the golden fixture (node v22.9.0
  offline harness).

### Persistence + API (no parallel API invented)
- Implemented the three missing store methods on `SqlAlchemyStore`:
  `add_verification_artifact`, `list_verification_artifacts`,
  `get_verification_artifact_for_patch`.
- Added `VerificationRunArtifactModel` and a new Alembic migration
  `d4b8f1e6c530_verification_run_artifacts` (down_revision `a9c1e6f3b208`).
  Schema matches the model (8 columns, `incident_id`/`patch_id` indexed).
- Exposure reuses the existing contract: the pipeline projects the rich
  artifact onto the unchanged `VerificationRun` shape and persists it, served
  by the existing `GET /api/v1/incidents/{incident_id}/verifications`
  endpoint the M6 review UI already consumes. No new verification endpoint was
  added.

### Focused tests (`services/api/tests/test_verification.py`, 13 tests)
Pass; allowlist rejection (shell metachars, relative exe, empty argv); timeout;
output bound; environment-issue classification (unauthorized command);
patch-issue classification (base-state evidence); bounded-repair cap; PR
blocking on high-risk pass and on failed verification; persistence + API
exposure to `REVIEW_READY`.

### Determinism preserved
`test_demo_determinism` now masks the M6 `verification_lifecycle` events'
volatile tokens (real subprocess durations, ephemeral uuid workspace IDs) —
the same treatment already applied to M5 `sandbox_lifecycle` — so the
deterministic sequence is still asserted without pinning provenance noise.

## Exact command results

- `uv run --project services/api ruff check services/api/app services/api/tests`
  → **All checks passed!**
- `uv run --project services/api mypy --strict services/api/app`
  → **Success: no issues found in 43 source files**
- `uv run --project services/api pytest -q services/api/tests`
  → **133 passed, 1 warning in 23.23s** (was 114 passed / 6 failed)
- Fresh Alembic upgrade on an empty temp DB (`alembic upgrade head`, no
  `create_all` shortcut) → chain runs `... a9c1e6f3b208 -> d4b8f1e6c530`,
  `alembic_version = d4b8f1e6c530`, `verification_run_artifacts` table present
  with columns `[artifact_hash, created_at, document, failure_kind, id,
  incident_id, passed, patch_id]`. Also exercised by
  `test_persistence.py::test_fresh_migration` (part of the 133).

## RISK

- Real verification requires the `node` toolchain on the host; the four
  `node`-dependent tests `skipif(node is None)`. On a host without node the
  verifier fails **closed** (`VerificationSetupError` → `PATCH_FAILED`), never
  a false pass. The one warning is the pre-existing Starlette/httpx
  deprecation, unrelated to M6.
- Network denial is enforced by layering (argv only ever maps to the pinned
  offline harness + environment allowlist), not an OS egress filter — as
  documented in the runner and ADR 009. No change from Fable's design.

## NEXT

- M7 draft-PR adapter must gate on `REVIEW_READY` + a second `CREATE_DRAFT_PR`
  approval and must not fire on any `PATCH_FAILED`/risk-blocked incident.
- If a live (non-fixture) repository target is added, wire its own
  verification manifest; the verifier already resolves the manifest per
  service and fails closed when missing.

## BLOCKED

None. Branch is fully verified and integration-ready. No commits made (per
task constraints).

## Integrator review (2026-07-13)

- Reproduced full backend gates: ruff passed, strict mypy passed over 43 source files, and the complete backend suite passed (133 tests; one pre-existing deprecation warning).
- Reproduced the 13 focused M6 tests and the fresh-migration test independently.
- Corrected the migration's JSON column from SQLite-specific `sqlite.JSON()` to portable `sa.JSON()` so the schema remains compatible with the PostgreSQL target; full ruff and focused verification/migration tests pass after the correction.
- Confirmed the demo harness imports only Node filesystem/path/process/URL built-ins and runs through the immutable pinned manifest. Network denial is therefore an allowlisted-fixture guarantee, not OS-level egress isolation; live repository command execution remains unsupported and fails closed.
