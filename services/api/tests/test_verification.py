"""M6 deterministic verification and review.

Covers the M6 gate end to end and at the seams:

- the strict argv ``CommandRunner`` (allowlist rejection, per-command timeout,
  bounded output),
- the deterministic risk reviewer's PR-blocking decision,
- the ``DeterministicVerifier`` pass path with byte-exact diff reconstruction
  and proven workspace destruction, plus failure classification into an
  environment issue (unauthorized command) and a patch issue (a check that
  fails on the patched tree but passes on the pristine base),
- the bounded repair loop (a relevant patch-caused failure re-enters PATCHING
  at most until the budget and the MAX_REPAIR_ATTEMPTS cap are exhausted, then
  lands in PATCH_FAILED),
- PR blocking: a failed verification or a high-risk pass never reaches
  REVIEW_READY,
- persistence and exposure through the existing incident verification API.
"""

import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.contracts import ApprovalRequest, Incident
from app.domain.enums import (
    ApprovalStatus,
    ApprovalType,
    Environment,
    ProviderMode,
    RiskLevel,
    Severity,
    WorkflowState,
)
from app.domain.remediation import ApprovalBinding, build_plan_artifact
from app.domain.sandbox import FileChange, PatchExecutionArtifact, PatchExecutionStatus
from app.domain.verification import (
    TEST_CATEGORIES,
    CheckCategory,
    RiskReview,
    VerificationCommandResult,
    VerificationFailureKind,
    VerificationRunArtifact,
    build_verification_artifact,
)
from app.main import create_app
from app.providers.code_agent import (
    _TEST_ANCHOR,
    _TEST_INSERTION,
    FixtureCodexGateway,
)
from app.sandbox.command_runner import CommandPolicyError, CommandRunner
from app.sandbox.executor import ApprovalRequiredError, SandboxPatchExecutor
from app.sandbox.verifier import DeterministicVerifier
from app.sandbox.workspace import SandboxWorkspace
from app.store.memory import InMemoryStore
from app.workflow.policy import PROHIBITED_PATH_PATTERNS
from app.workflow.risk import review_patch

NOW = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
NODE = shutil.which("node")


# --- Shared fixture-repo setup ------------------------------------------------


def _incident() -> Incident:
    return Incident(
        id="inc-test-0001",
        title="Checkout API elevated 500 errors",
        service="checkout-api",
        environment=Environment.PRODUCTION,
        severity=Severity.SEV2,
        summary="HTTP 500 rate exceeded 12% after deployment.",
        state=WorkflowState.PATCHING,
        provider_mode=ProviderMode.SIMULATED,
        created_at=NOW,
        updated_at=NOW,
    )


def _plan(incident_id: str, **overrides: Any) -> Any:
    fields: dict[str, Any] = {
        "id": "rplan-0001",
        "incident_id": incident_id,
        "investigation_report_id": "inv-0001",
        "hypothesis_id": "hyp-0001",
        "version": 1,
        "summary": "Restore optional discount handling and add a regression test",
        "files_expected": ["src/checkout.test.ts", "src/checkout.ts"],
        "steps": ["Add a no-discount regression test", "Restore the optional guard"],
        "verification_commands": ["npm test"],
        "allowed_commands": ["npm test"],
        "prohibited_paths": list(PROHIBITED_PATH_PATTERNS),
        "risk_level": RiskLevel.LOW,
        "max_files_changed": 2,
        "max_lines_changed": 40,
        "max_attempts": 2,
        "timeout_seconds": 300,
        "network_allowed": False,
        "rollback": "Revert the candidate patch commit",
        "rationale": "Smallest safe fix grounded in the investigation code mapping",
        "created_at": NOW,
    }
    fields.update(overrides)
    return build_plan_artifact(**fields)


def _bind_approval(store: InMemoryStore, incident: Incident, plan: Any) -> ApprovalRequest:
    approval = ApprovalRequest(
        id=store.next_id("apr"),
        incident_id=incident.id,
        approval_type=ApprovalType.APPLY_PATCH,
        risk_level=plan.risk_level,
        status=ApprovalStatus.APPROVED,
        reason=plan.summary,
        artifact_version=plan.version,
        requested_at=NOW,
        expires_at=NOW + timedelta(hours=4),
        decided_at=NOW,
    )
    store.add_approval(approval)
    store.add_approval_binding(
        ApprovalBinding(
            approval_id=approval.id,
            incident_id=incident.id,
            plan_id=plan.id,
            plan_version=plan.version,
            plan_hash=plan.artifact_hash,
            action=ApprovalType.APPLY_PATCH,
            risk_level=plan.risk_level,
            approver_role="incident_commander",
            expires_at=approval.expires_at,
            created_at=NOW,
        )
    )
    return approval


def _setup(store: InMemoryStore, **plan_overrides: Any) -> tuple[Incident, Any]:
    incident = _incident()
    store.add_incident(incident)
    plan = _plan(incident.id, **plan_overrides)
    store.add_plan_artifact(plan)
    _bind_approval(store, incident, plan)
    return incident, plan


def _verifier(store: InMemoryStore) -> DeterministicVerifier:
    return DeterministicVerifier(
        store=store, environ=dict(os.environ), fixtures_root=FIXTURES_ROOT
    )


class _TestOnlyGateway:
    """Adds the regression test but never fixes the source, so the new test
    exercises the still-present defect: ``npm test`` fails on the patched tree
    yet passes on the pristine base — a patch-caused failure."""

    engine_id = "fixture-test-only"
    simulated = True

    def apply_patch_turn(self, workspace: SandboxWorkspace, task: Any) -> None:
        tests = workspace.read_file("src/checkout.test.ts")
        workspace.write_file(
            "src/checkout.test.ts", tests.replace(_TEST_ANCHOR, _TEST_INSERTION, 1)
        )


# --- CommandRunner: allowlist, timeout, output bound --------------------------


def test_command_runner_refuses_shell_metacharacters_and_relative_exe() -> None:
    runner = CommandRunner(environ=dict(os.environ))
    cwd = Path(__file__).parent
    with pytest.raises(CommandPolicyError):
        runner.run((), cwd, 5.0)
    with pytest.raises(CommandPolicyError, match="shell metacharacters"):
        runner.run(("/bin/echo", "a;b"), cwd, 5.0)
    with pytest.raises(CommandPolicyError, match="pinned absolute path"):
        runner.run(("node", "--version"), cwd, 5.0)


@pytest.mark.skipif(NODE is None, reason="node toolchain required")
def test_command_runner_enforces_timeout() -> None:
    assert NODE is not None
    runner = CommandRunner(environ=dict(os.environ))
    result = runner.run((NODE, "-e", "while(true){}"), Path.cwd(), 0.5)
    assert result.timed_out is True
    assert result.exit_code is None


@pytest.mark.skipif(NODE is None, reason="node toolchain required")
def test_command_runner_bounds_output() -> None:
    assert NODE is not None
    runner = CommandRunner(environ=dict(os.environ), output_limit_bytes=1024)
    result = runner.run(
        (NODE, "-e", "process.stdout.write('x'.repeat(50000))"), Path.cwd(), 30.0
    )
    assert result.exit_code == 0
    assert result.stdout_truncated is True
    assert len(result.stdout.encode("utf-8")) <= 1024


# --- Risk reviewer: PR blocking ----------------------------------------------


def test_review_patch_high_risk_path_blocks_pr() -> None:
    review = review_patch(
        [FileChange(path="src/auth/session.ts", additions=3, deletions=1)], ""
    )
    assert review.risk_level is RiskLevel.HIGH
    assert review.blocks_pr is True


def test_review_patch_small_low_risk_change_allows_pr() -> None:
    review = review_patch(
        [FileChange(path="src/checkout.ts", additions=2, deletions=1)], ""
    )
    assert review.risk_level is RiskLevel.LOW
    assert review.blocks_pr is False


# --- Verifier: pass, environment issue, patch issue ---------------------------


@pytest.mark.skipif(NODE is None, reason="node toolchain required")
def test_verifier_passes_and_persists_the_artifact() -> None:
    store = InMemoryStore()
    incident, _ = _setup(store)
    execution = SandboxPatchExecutor(
        store=store, gateway=FixtureCodexGateway(), fixtures_root=FIXTURES_ROOT
    ).execute(incident)
    assert execution.status is PatchExecutionStatus.SUCCEEDED

    artifact = _verifier(store).verify(incident, execution, "patch-0001", 1)

    assert artifact.passed is True
    assert artifact.failure_kind is None
    assert artifact.diff_reconstructed is True
    assert artifact.workspace_destroyed is True
    assert artifact.risk.blocks_pr is False
    non_baseline = [c for c in artifact.commands if not c.baseline]
    assert non_baseline and all(c.passed for c in non_baseline)
    assert any(c.category in TEST_CATEGORIES for c in non_baseline)
    # Persisted and retrievable through the store protocol.
    assert store.get_verification_artifact_for_patch("patch-0001") == artifact
    assert store.list_verification_artifacts(incident.id) == [artifact]


@pytest.mark.skipif(NODE is None, reason="node toolchain required")
def test_verifier_refuses_unauthorized_command_as_environment_issue() -> None:
    store = InMemoryStore()
    incident, _ = _setup(
        store,
        verification_commands=["npm run coverage"],
        allowed_commands=["npm run coverage"],
    )
    execution = SandboxPatchExecutor(
        store=store, gateway=FixtureCodexGateway(), fixtures_root=FIXTURES_ROOT
    ).execute(incident)

    artifact = _verifier(store).verify(incident, execution, "patch-0001", 1)

    assert artifact.passed is False
    assert artifact.failure_kind is VerificationFailureKind.ENVIRONMENT_ISSUE
    assert any("safe policy baseline" in e for e in artifact.failure_evidence)
    # Failing closed before authorization means no workspace was ever built.
    assert artifact.workspace_destroyed is True


@pytest.mark.skipif(NODE is None, reason="node toolchain required")
def test_verifier_classifies_patch_caused_check_failure() -> None:
    store = InMemoryStore()
    incident, _ = _setup(store)
    execution = SandboxPatchExecutor(
        store=store, gateway=_TestOnlyGateway(), fixtures_root=FIXTURES_ROOT
    ).execute(incident)
    assert execution.status is PatchExecutionStatus.SUCCEEDED

    artifact = _verifier(store).verify(incident, execution, "patch-0001", 1)

    assert artifact.passed is False
    assert artifact.failure_kind is VerificationFailureKind.PATCH_ISSUE
    # Classification is proven with base-state evidence: the same command ran
    # against the pristine base and passed there.
    baseline = [c for c in artifact.commands if c.baseline]
    assert baseline and all(c.passed for c in baseline)


# --- Bounded repair loop cap (executor) ---------------------------------------


def test_repair_loop_is_capped_at_two_attempts() -> None:
    store = InMemoryStore()
    incident, _ = _setup(store, max_attempts=5)
    executor = SandboxPatchExecutor(
        store=store, gateway=FixtureCodexGateway(), fixtures_root=FIXTURES_ROOT
    )

    execution = executor.execute(incident)
    assert executor.repair_budget_remaining(incident, execution) == 4

    execution = executor.repair(incident, execution, "verification failed")
    assert executor.repair_budget_remaining(incident, execution) == 3

    execution = executor.repair(incident, execution, "verification failed")
    # Two repairs done: the MAX_REPAIR_ATTEMPTS cap now closes the budget even
    # though the plan's own attempt budget (5) has not been spent.
    assert executor.repair_budget_remaining(incident, execution) == 0
    with pytest.raises(ApprovalRequiredError, match="no repair attempt budget"):
        executor.repair(incident, execution, "verification failed")


# --- Pipeline PR blocking and bounded repair (stub verifier) ------------------


class _StubVerifier:
    """Conforms to the ``Verifier`` protocol and returns a fixed deterministic
    outcome, so the pipeline's REVIEW_READY / PATCH_FAILED / repair branches
    can be driven without a real toolchain."""

    def __init__(
        self,
        store: Any,
        *,
        passed: bool,
        blocks_pr: bool = False,
        failure_kind: VerificationFailureKind | None = None,
    ) -> None:
        self._store = store
        self._passed = passed
        self._blocks_pr = blocks_pr
        self._failure_kind = failure_kind
        self.calls = 0

    def verify(
        self,
        incident: Incident,
        execution: PatchExecutionArtifact,
        patch_id: str,
        attempt: int,
    ) -> VerificationRunArtifact:
        self.calls += 1
        risk = RiskReview(
            risk_level=RiskLevel.HIGH if self._blocks_pr else RiskLevel.LOW,
            findings=[],
            files_changed=len(execution.changed_files),
            lines_changed=execution.total_additions + execution.total_deletions,
            blocks_pr=self._blocks_pr,
        )
        commands = [
            VerificationCommandResult(
                command="npm test",
                category=CheckCategory.TEST,
                argv=["x"],
                exit_code=0 if self._passed else 1,
                duration_ms=1,
                stdout="",
                stderr="",
                stdout_truncated=False,
                stderr_truncated=False,
                timed_out=False,
            )
        ]
        artifact = build_verification_artifact(
            id=self._store.next_id("vrun"),
            incident_id=incident.id,
            patch_id=patch_id,
            patch_execution_id=execution.id,
            plan_id=execution.plan_id,
            plan_hash=execution.plan_hash,
            attempt=attempt,
            base_ref=execution.base_ref,
            base_checksum=execution.base_checksum,
            diff_hash=execution.diff_hash,
            diff_reconstructed=True,
            workspace_id="stub",
            runner_id="stub-runner",
            target_simulated=True,
            commands=commands,
            relevant_regression_test=self._passed,
            passed=self._passed,
            failure_kind=None if self._passed else self._failure_kind,
            failure_evidence=[] if self._passed else ["stub failure"],
            risk=risk,
            workspace_destroyed=True,
            total_duration_ms=1,
            budget_seconds=300,
            created_at=NOW,
        )
        self._store.add_verification_artifact(artifact)
        return artifact


def _demo_client_with_verifier(verifier_factory: Any) -> TestClient:
    settings = Settings(demo_mode=True, demo_admin_key="test", database_url="sqlite:///:memory:")
    app = create_app(settings)
    app.state.pipeline._verifier = verifier_factory(app.state.store)
    return TestClient(app)


def _drive_to_decision(client: TestClient) -> str:
    client.post("/api/v1/incidents/inc-demo-0001/start")
    approval = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()[0]
    client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        json={"decision": "approved", "reason": "test"},
    )
    return str(client.get("/api/v1/incidents/inc-demo-0001").json()["state"])


def test_high_risk_pass_blocks_pr_and_never_reaches_review_ready() -> None:
    with _demo_client_with_verifier(
        lambda store: _StubVerifier(store, passed=True, blocks_pr=True)
    ) as client:
        state = _drive_to_decision(client)
        assert state == WorkflowState.PATCH_FAILED.value
        verifs = client.get("/api/v1/incidents/inc-demo-0001/verifications").json()
        assert verifs and verifs[-1]["passed"] is False


def test_failed_verification_blocks_pr() -> None:
    with _demo_client_with_verifier(
        lambda store: _StubVerifier(
            store, passed=False, failure_kind=VerificationFailureKind.ENVIRONMENT_ISSUE
        )
    ) as client:
        state = _drive_to_decision(client)
        assert state == WorkflowState.PATCH_FAILED.value


def test_repairable_failure_is_bounded_then_fails() -> None:
    factory = lambda store: _StubVerifier(  # noqa: E731
        store, passed=False, failure_kind=VerificationFailureKind.PATCH_ISSUE
    )
    with _demo_client_with_verifier(factory) as client:
        state = _drive_to_decision(client)
        assert state == WorkflowState.PATCH_FAILED.value
        # Initial attempt + at most the plan's bounded repairs, never a loop.
        patches = client.get("/api/v1/incidents/inc-demo-0001/patches").json()
        assert 2 <= len(patches) <= 3


@pytest.mark.skipif(NODE is None, reason="node toolchain required")
def test_golden_verification_persisted_and_exposed_via_api() -> None:
    """Real deterministic verification drives REVIEW_READY; the projected run
    is exposed through the existing endpoint and the rich artifact persists in
    SQL, retrievable by patch."""
    settings = Settings(demo_mode=True, demo_admin_key="test", database_url="sqlite:///:memory:")
    app = create_app(settings)
    with TestClient(app) as client:
        state = _drive_to_decision(client)
        assert state == WorkflowState.WAITING_PR_APPROVAL.value

        verifs = client.get("/api/v1/incidents/inc-demo-0001/verifications").json()
        assert verifs and verifs[-1]["passed"] is True
        assert any(c["passed"] for c in verifs[-1]["checks"])

        patch = client.get("/api/v1/incidents/inc-demo-0001/patches").json()[0]
        artifact = app.state.store.get_verification_artifact_for_patch(patch["id"])
        assert artifact is not None
        assert artifact.passed is True
        assert artifact.diff_reconstructed is True
