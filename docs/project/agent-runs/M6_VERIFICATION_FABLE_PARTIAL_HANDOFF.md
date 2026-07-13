# M6 Verification Fable Partial Handoff

## Result
Status: partial

## Files Changed
- `services/api/app/domain/verification.py`: verification evidence contracts.
- `services/api/app/sandbox/command_runner.py`: bounded allowlisted command execution.
- `services/api/app/sandbox/verifier.py`: deterministic verification orchestration.
- `services/api/app/workflow/risk.py`: risk classification.
- `services/api/app/workflow/pipeline.py`: patch, verify, repair, and review-ready flow.
- `services/api/app/store/`: verification persistence protocol and memory store.
- `services/api/fixtures/checkout-api/`: deterministic verification manifest and checks.

## Verification
- `uv run --project services/api pytest -q services/api/tests`: failed, 114 passed and 6 failed.
- Common failure: `SimulatedVerificationRunner.verify()` still accepts the legacy two-argument contract while the pipeline now supplies incident, execution, patch id, and attempt.
- `git diff --check`: passed.

## Remaining Work
- Migrate every verifier implementation and test double to one typed protocol.
- Add focused M6 tests for allowlist rejection, timeout/output bounds, pass/fail classification, bounded repair, persistence/API exposure, and failed-verification PR blocking.
- Run ruff, strict mypy, full pytest, and fresh migration verification.

## Risks
- This checkpoint is not integration-ready and must not be cherry-picked to `main`.
- Security behavior and exact patch reconstruction have not yet received integrator review.

## Notes For Integrator
- Fable stopped on a session-limit marker before producing its own handoff.
- Continue from this preserved diff with Opus 4.8; do not restart or discard coherent work.
