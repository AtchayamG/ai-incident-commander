# M4 Remediation Final Handoff

## Result

Status: complete after Fable usage exhaustion; Codex reproduced every backend gate.

## Files Changed

- `services/api/app/domain/remediation.py`: immutable bounded plan artifact, deterministic hash, refusal decision, and approval binding contracts.
- `services/api/app/workflow/remediation_planner.py`: evidence/code-map grounded planning and policy enforcement.
- `services/api/app/workflow/policy.py`: prohibited paths, command allowlist, budgets, no-network, and risk classification.
- `services/api/app/providers/simulated_remediation.py`: deterministic golden remediation draft.
- `services/api/app/workflow/pipeline.py`: PLAN_READY/NO_SAFE_REMEDIATION transitions and artifact-bound APPLY_PATCH approval creation.
- `services/api/app/api/routes/approvals.py`: stale/hash/version/expiry/role/single-use enforcement.
- `services/api/alembic/versions/e8a4f7c2d901_remediation_plan_artifacts.py`: persisted plan artifact and approval binding schema.
- `services/api/tests/test_remediation.py`: golden, refusal, budget, stale, role, expiry, reuse, and audit coverage.

## Verification

- `py -3.12 -m ruff check .`: pass.
- `py -3.12 -m mypy`: pass, 49 source files.
- `py -3.12 -m pytest -q`: pass, 89 tests.

## Security Invariants

- No plan or approval is created for insufficient evidence or policy refusal.
- Approval binds one exact incident/plan ID/version/hash/action/role/expiry tuple and is single-use.
- Golden plan is limited to `src/checkout.ts` and `src/checkout.test.ts`, two files, 40 lines, no network, allowlisted commands, and explicit rollback.
- This slice performs no repository mutation; M5 owns isolated patch execution.

## Remaining Work

- Integrator must reproduce gates on `main`, add the judge-facing M4 approval UX, and begin M5 isolated workspace execution.
