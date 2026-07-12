# M5 Codex Sandbox Final Handoff

## Result

Status: complete. Bounded isolated-workspace patch execution runs end to end:
an approved, single-use APPLY_PATCH approval materializes an ephemeral fixture
workspace, the code-agent gateway produces the minimal regression-test patch
inside it, the executor captures an immutable diff/metrics/provenance artifact,
and the workspace is destroyed on every path with the source fixture proven
unmutated.

Provider provenance: the deterministic demo run uses `FixtureCodexGateway`,
labeled `simulated=True` / `ProviderMode.SIMULATED`. It is never presented as a
live Codex call. The real `CodexCliGateway` drives the locally installed
`codex exec` (0.139.0) contract, is configuration-gated, and fails closed when
the binary, model, or credentials are absent — no live run was performed or
claimed in this handoff.

Continuation context: this milestone was resumed from the Fable quota-exhaust
checkpoint (commit `538019e`). The checkpoint's implementation was inspected and
retained; it was already correct and complete. This session added the single
missing reachable proof (timeout budget) and verified migration/store/agreement
and the full quality gates. No working code was rewritten.

## Files Touched

Retained from the checkpoint (inspected, correct, unchanged):

- `services/api/app/sandbox/workspace.py`: ephemeral policy-bounded workspace — immutable-base verification, read-only-until-approval writes, path confinement, prohibited-path and allowed-path enforcement, file/line budgets checked at write time and diff capture, reset-between-attempts, and proven idempotent destruction.
- `services/api/app/sandbox/executor.py`: deterministic patch lifecycle — approval authorization (missing/rejected/stale/reused), single-use consumption, manifest fail-closed, attempt/timeout budgets, regression-test requirement, diff capture, source-immutability check, destruction on every failure path, immutable hashed artifact, timeline audit with provenance.
- `services/api/app/sandbox/__init__.py`: package marker.
- `services/api/app/domain/sandbox.py`: `PatchExecutionArtifact` and lifecycle types; content hash covers every field; succeeded-run invariants (non-empty diff, destroyed workspace, intact source, no failure reasons).
- `services/api/app/providers/base.py`: `CodeAgentGateway` protocol and `PatchTaskContext`; removed the legacy M0 `PatchProposal` shape.
- `services/api/app/providers/code_agent.py`: `FixtureCodexGateway` (simulated) and `CodexCliGateway` (live, fail-closed, env-allowlisted, network-disabled) + `build_code_agent_gateway` selector.
- `services/api/app/providers/simulated.py`: removed the obsolete `SimulatedCodeAgentGateway`/`_FIXTURE_DIFF`; the sandbox now owns patch production.
- `services/api/app/workflow/pipeline.py`: `apply_patch_approval` runs the executor, records PATCHING/VERIFYING/REVIEW_READY vs PATCH_FAILED, and keeps the M4 authorization gate as defense in depth.
- `services/api/app/config.py`: `CODE_AGENT_ENGINE` / `CODEX_MODEL` / `CODEX_BINARY` / `CODEX_HOME` settings.
- `services/api/app/main.py`: wires `SandboxPatchExecutor` with the configured gateway.
- `services/api/app/api/routes/incidents.py`: read-only `GET /{incident_id}/patch-executions`.
- `services/api/app/store/protocol.py`, `store/memory.py`, `store/models.py`, `store/sql.py`: `add_patch_execution` / `list_patch_executions` across the in-memory and SQL stores; JSON-document row with scalar safety columns.
- `services/api/alembic/versions/a9c1e6f3b208_patch_execution_artifacts.py`: `patch_execution_artifacts` table + indexes.
- `services/api/fixtures/checkout-api/base_manifest.json`: pinned immutable base (per-file sha256, CRLF-normalized) for the checkout-api repo checkout.
- `evals/fixtures/checkout-api/golden_patch.diff`, `README.md`: byte-exact golden diff the fixture gateway reproduces.
- `services/api/tests/test_sandbox_workspace.py`, `tests/test_providers.py`, `tests/test_demo_determinism.py`, `tests/test_investigation.py`, `tests/test_remediation.py`: sandbox/provider coverage and M0-shape cleanups.
- `services/api/uv.lock`: dependency lock.

Changed this session:

- `services/api/tests/test_sandbox_executor.py`: added `test_timeout_budget_is_enforced_before_the_gateway_runs` — the one reachable budget proof the checkpoint lacked (the gateway never runs, the execution fails with the timeout reason, and the workspace is still destroyed).

## Verification (exact commands, from `services/api`)

- `uv run ruff check .` → `All checks passed!`
- `uv run mypy --strict app` → `Success: no issues found in 39 source files`
- `uv run pytest` → `120 passed, 1 warning`
- `uv run pytest tests/test_sandbox_executor.py tests/test_sandbox_workspace.py` → `31 passed`
- Alembic chain on a fresh SQLite DB (via the alembic API with an overridden `sqlalchemy.url`, since `alembic.ini` pins a placeholder URL): `upgrade head` creates `patch_execution_artifacts` with columns `{id, incident_id, approval_id, status, engine_id, simulated, artifact_hash, document, created_at}` and both indexes; `downgrade base` leaves only `alembic_version`. Columns match `PatchExecutionArtifactModel` exactly.

## Security Invariants Proven

- **Approval required and single-use.** No plan / no approved APPLY_PATCH / stale binding hash / already-consumed approval each refuse before any workspace exists or is reused (`test_execute_without_plan_refuses`, `test_execute_without_approved_approval_refuses[PENDING|REJECTED|EXPIRED]`, `test_execute_with_stale_binding_refuses`, `test_approval_is_single_use`, `test_api_rejected_approval_never_touches_a_workspace`).
- **Source-fixture immutability.** Drift from the pinned manifest fails closed pre-workspace; the source hashes are re-verified after every run (`test_drifted_source_fails_closed`, `test_missing_manifest_fails_closed_before_any_workspace`, `test_create_refuses_drifted_source`, golden run asserts `source_fixture_intact`).
- **Path and budget bounds.** Read-only-until-approval, path escape, prohibited paths, unapproved files, file-count and line budgets, attempt budget, and timeout budget are all enforced and each destroys the workspace on violation.
- **Network denied.** A plan cannot enable network access (`RemediationPlanArtifact` rejects `network_allowed=True`; planner refuses such drafts), and the live `codex exec` command sets `sandbox_workspace_write.network_access=false`.
- **No secret leakage.** The Codex subprocess environment is an explicit allowlist (`PATH`, `SYSTEMROOT`, `TEMP`, `TMP`, plus an explicit `CODEX_HOME`); parent API keys/tokens never cross the boundary (`test_codex_cli_env_never_leaks_parent_secrets`).
- **Cleanup on every path.** Success, policy violation, budget breach, exhausted attempts, timeout, and crash all end with a destroyed workspace (`workspace_destroyed` proven, path re-checked absent).
- **Honest provenance.** The fixture adapter is always `simulated`; the live adapter fails closed and is never silently substituted in demo mode (`test_code_agent_gateways_declare_explicit_provenance`, `test_codex_cli_fails_closed_without_binary_or_credentials`, `test_gateway_builder_selects_and_refuses_explicitly`).

## Remaining Limitations

- The executor's `if plan.network_allowed:` guard is redundant defense in depth: `RemediationPlanArtifact` already rejects `network_allowed=True` at construction, so the guard is unreachable through the normal type. Left in place as fail-closed belt-and-suspenders; not separately unit-tested because no such plan can be built.
- `alembic.ini` ships the stock `driver://user:pass@localhost/dbname` placeholder, which shadows `DATABASE_URL` in `env.py:get_url()`. Migrations were verified by overriding `sqlalchemy.url` via the alembic API. Pre-existing; out of M5 scope.
- The live `CodexCliGateway` was not exercised against real Codex in this run (no credentials, and STOP-IF forbids live-credential use). It is covered structurally: command construction, env allowlist, and fail-closed availability checks.
- Verification is still simulated (`SimulatedVerificationRunner`). The real test/lint/typecheck runner against the patched workspace is M6 and was intentionally not implemented.

## Handoff to Integrator / M6

- Reproduce the gates on `main`; nothing here touches `apps/web/**` or `packages/contracts/**`.
- M6 owns the verification runner that executes tests inside a (read-only, network-denied) checkout of the captured diff and the judge-facing execution UX.
