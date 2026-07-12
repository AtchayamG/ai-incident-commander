"""M5 bounded isolated-workspace patch execution.

Covers: approval missing/pending/rejected/stale refusal before any workspace
exists, single-use approval consumption, the golden fixture patch (byte-exact
against the evals golden diff) with full lifecycle audit and provenance,
source-fixture immutability, workspace destruction on success and on every
failure path (denied path, budget violation, exhausted attempt budget),
missing/drifted immutable-base manifest failing closed, and the end-to-end
API flow through the approval decision endpoint.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

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
from app.domain.sandbox import (
    PatchExecutionStatus,
    SandboxLifecycleStage,
    execution_artifact_hash,
)
from app.providers.base import PatchTaskContext
from app.providers.code_agent import FixtureCodexGateway, GatewayTurnError
from app.sandbox.executor import (
    ApprovalConsumedError,
    ApprovalRequiredError,
    SandboxPatchExecutor,
    SandboxSetupError,
)
from app.sandbox.workspace import SandboxWorkspace, content_sha256, normalize_text
from app.store.memory import InMemoryStore
from app.workflow.policy import PROHIBITED_PATH_PATTERNS

NOW = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
GOLDEN_DIFF = (
    Path(__file__).resolve().parents[3]
    / "evals"
    / "fixtures"
    / "checkout-api"
    / "golden_patch.diff"
)


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


def _bind_approval(
    store: InMemoryStore,
    incident: Incident,
    plan: Any,
    status: ApprovalStatus = ApprovalStatus.APPROVED,
    plan_hash: str | None = None,
) -> ApprovalRequest:
    approval = ApprovalRequest(
        id=store.next_id("apr"),
        incident_id=incident.id,
        approval_type=ApprovalType.APPLY_PATCH,
        risk_level=plan.risk_level,
        status=status,
        reason=plan.summary,
        artifact_version=plan.version,
        requested_at=NOW,
        expires_at=NOW + timedelta(hours=4),
        decided_at=NOW if status is not ApprovalStatus.PENDING else None,
    )
    store.add_approval(approval)
    store.add_approval_binding(
        ApprovalBinding(
            approval_id=approval.id,
            incident_id=incident.id,
            plan_id=plan.id,
            plan_version=plan.version,
            plan_hash=plan_hash or plan.artifact_hash,
            action=ApprovalType.APPLY_PATCH,
            risk_level=plan.risk_level,
            approver_role="incident_commander",
            expires_at=approval.expires_at,
            created_at=NOW,
        )
    )
    return approval


def _executor(
    store: InMemoryStore, gateway: Any | None = None, fixtures_root: Path | None = None
) -> SandboxPatchExecutor:
    return SandboxPatchExecutor(
        store=store,
        gateway=gateway or FixtureCodexGateway(),
        fixtures_root=fixtures_root or FIXTURES_ROOT,
    )


def _golden_setup(store: InMemoryStore) -> Incident:
    incident = _incident()
    store.add_incident(incident)
    plan = _plan(incident.id)
    store.add_plan_artifact(plan)
    _bind_approval(store, incident, plan)
    return incident


def _fixture_repo_hashes() -> dict[str, str]:
    repo = FIXTURES_ROOT / "checkout-api" / "repo"
    return {
        p.relative_to(repo).as_posix(): content_sha256(normalize_text(p.read_bytes()))
        for p in sorted(repo.rglob("*"))
        if p.is_file()
    }


class _RecordingGateway:
    """Test gateway that records the workspace it ran in so destruction can
    be asserted, then delegates to a callable."""

    engine_id = "fixture-test"
    simulated = True

    def __init__(self, turn: Any) -> None:
        self._turn = turn
        self.workspace: SandboxWorkspace | None = None
        self.calls = 0

    def apply_patch_turn(self, workspace: SandboxWorkspace, task: PatchTaskContext) -> None:
        self.workspace = workspace
        self.calls += 1
        self._turn(workspace, task)


# --- Authorization gates (no workspace before a valid approval) -----------------


def test_execute_without_plan_refuses() -> None:
    store = InMemoryStore()
    incident = _incident()
    store.add_incident(incident)
    with pytest.raises(ApprovalRequiredError, match="no bounded remediation plan"):
        _executor(store).execute(incident)
    assert store.list_patch_executions(incident.id) == []


@pytest.mark.parametrize(
    "status", [ApprovalStatus.PENDING, ApprovalStatus.REJECTED, ApprovalStatus.EXPIRED]
)
def test_execute_without_approved_approval_refuses(status: ApprovalStatus) -> None:
    store = InMemoryStore()
    incident = _incident()
    store.add_incident(incident)
    plan = _plan(incident.id)
    store.add_plan_artifact(plan)
    _bind_approval(store, incident, plan, status=status)
    with pytest.raises(ApprovalRequiredError, match="no approved APPLY_PATCH"):
        _executor(store).execute(incident)
    assert store.list_patch_executions(incident.id) == []


def test_execute_with_stale_binding_refuses() -> None:
    """An approval bound to an older artifact hash never authorizes the
    current plan."""
    store = InMemoryStore()
    incident = _incident()
    store.add_incident(incident)
    plan = _plan(incident.id)
    store.add_plan_artifact(plan)
    _bind_approval(store, incident, plan, plan_hash="sha256:stale-hash")
    with pytest.raises(ApprovalRequiredError):
        _executor(store).execute(incident)
    assert store.list_patch_executions(incident.id) == []


def test_approval_is_single_use() -> None:
    store = InMemoryStore()
    incident = _golden_setup(store)
    executor = _executor(store)
    first = executor.execute(incident)
    assert first.status is PatchExecutionStatus.SUCCEEDED
    with pytest.raises(ApprovalConsumedError, match="already consumed"):
        executor.execute(incident)
    assert len(store.list_patch_executions(incident.id)) == 1


# --- Golden execution -------------------------------------------------------------


def test_golden_execution_captures_diff_and_proves_cleanup() -> None:
    store = InMemoryStore()
    incident = _golden_setup(store)
    before = _fixture_repo_hashes()

    artifact = _executor(store).execute(incident)

    assert artifact.status is PatchExecutionStatus.SUCCEEDED
    assert artifact.simulated is True
    assert artifact.provider_mode is ProviderMode.SIMULATED
    assert artifact.engine_id == "fixture-codex"
    assert artifact.approval_id == store.list_approvals(incident.id)[0].id
    assert [c.path for c in artifact.changed_files] == [
        "src/checkout.test.ts",
        "src/checkout.ts",
    ]
    assert artifact.total_additions == 6
    assert artifact.total_deletions == 1
    assert artifact.attempts_used == 1
    assert artifact.failure_reasons == []

    # Golden diff: byte-exact against the evals fixture, and it both repairs
    # the defect and adds the regression test.
    assert artifact.unified_diff == GOLDEN_DIFF.read_text(encoding="utf-8")
    assert "+  const code = session.discount?.code ?? null;" in artifact.unified_diff
    assert "-  const code = session.discount.code;" in artifact.unified_diff
    assert (
        '+  it("returns the cart total for a session without a discount"'
        in artifact.unified_diff
    )
    assert artifact.diff_hash == f"sha256:{content_sha256(artifact.unified_diff)}"

    # Immutable artifact: content hash covers every field.
    fields = artifact.model_dump(mode="json")
    fields.pop("artifact_hash")
    assert artifact.artifact_hash == execution_artifact_hash(fields)

    # Cleanup and source immutability are proven, not assumed.
    assert artifact.workspace_destroyed is True
    assert artifact.source_fixture_intact is True
    assert _fixture_repo_hashes() == before

    # Lifecycle audit: write mode only after approval consumption; destruction
    # and source verification recorded.
    stages = [event.stage for event in artifact.lifecycle]
    assert stages.index(SandboxLifecycleStage.APPROVAL_CONSUMED) < stages.index(
        SandboxLifecycleStage.WRITE_ENABLED
    )
    assert stages.index(SandboxLifecycleStage.READ_ONLY) < stages.index(
        SandboxLifecycleStage.WRITE_ENABLED
    )
    for stage in (
        SandboxLifecycleStage.WORKSPACE_CREATED,
        SandboxLifecycleStage.BASE_VERIFIED,
        SandboxLifecycleStage.PATCH_APPLIED,
        SandboxLifecycleStage.DIFF_CAPTURED,
        SandboxLifecycleStage.WORKSPACE_DESTROYED,
        SandboxLifecycleStage.SOURCE_VERIFIED,
    ):
        assert stage in stages

    # Lifecycle is mirrored to the incident timeline with provenance.
    timeline = [t for t in store.list_timeline(incident.id) if t.kind == "sandbox_lifecycle"]
    assert len(timeline) == len(artifact.lifecycle)
    assert all(t.description.startswith("[simulated:fixture-codex]") for t in timeline)


# --- Failure paths: policy, budget, attempts, cleanup ------------------------------


def test_denied_path_fails_execution_and_destroys_workspace() -> None:
    store = InMemoryStore()
    incident = _golden_setup(store)

    def turn(workspace: SandboxWorkspace, task: PatchTaskContext) -> None:
        workspace.write_file("history/commits.json", "tampered\n")

    gateway = _RecordingGateway(turn)
    artifact = _executor(store, gateway=gateway).execute(incident)

    assert artifact.status is PatchExecutionStatus.FAILED
    assert any("outside the approved plan" in r for r in artifact.failure_reasons)
    assert SandboxLifecycleStage.POLICY_VIOLATION in [e.stage for e in artifact.lifecycle]
    assert artifact.workspace_destroyed is True
    assert gateway.workspace is not None
    assert not gateway.workspace.exists()
    assert artifact.source_fixture_intact is True


def test_budget_violation_fails_execution_and_destroys_workspace() -> None:
    store = InMemoryStore()
    incident = _golden_setup(store)

    def turn(workspace: SandboxWorkspace, task: PatchTaskContext) -> None:
        oversized = "".join(f"// line {i}\n" for i in range(200))
        workspace.write_file("src/checkout.ts", oversized)

    gateway = _RecordingGateway(turn)
    artifact = _executor(store, gateway=gateway).execute(incident)

    assert artifact.status is PatchExecutionStatus.FAILED
    assert any("budget" in r for r in artifact.failure_reasons)
    assert artifact.workspace_destroyed is True
    assert gateway.workspace is not None
    assert not gateway.workspace.exists()
    assert artifact.source_fixture_intact is True


def test_patch_without_regression_test_is_refused() -> None:
    store = InMemoryStore()
    incident = _golden_setup(store)

    def turn(workspace: SandboxWorkspace, task: PatchTaskContext) -> None:
        source = workspace.read_file("src/checkout.ts")
        workspace.write_file(
            "src/checkout.ts",
            source.replace(
                "  const code = session.discount.code;",
                "  const code = session.discount?.code ?? null;",
            ),
        )

    artifact = _executor(store, gateway=_RecordingGateway(turn)).execute(incident)
    assert artifact.status is PatchExecutionStatus.FAILED
    assert any("regression test" in r for r in artifact.failure_reasons)
    assert artifact.workspace_destroyed is True


def test_attempt_budget_is_enforced_and_cleanup_happens_on_crash() -> None:
    store = InMemoryStore()
    incident = _golden_setup(store)

    def turn(workspace: SandboxWorkspace, task: PatchTaskContext) -> None:
        raise GatewayTurnError("model produced no usable edit")

    gateway = _RecordingGateway(turn)
    artifact = _executor(store, gateway=gateway).execute(incident)

    assert artifact.status is PatchExecutionStatus.FAILED
    assert gateway.calls == 2  # plan.max_attempts
    assert artifact.attempts_used == 2
    assert any("attempt budget of 2 exhausted" in r for r in artifact.failure_reasons)
    assert artifact.workspace_destroyed is True
    assert gateway.workspace is not None
    assert not gateway.workspace.exists()
    assert artifact.source_fixture_intact is True
    assert artifact.unified_diff == ""


# --- Immutable base manifest fails closed -------------------------------------------


def test_missing_manifest_fails_closed_before_any_workspace(tmp_path: Path) -> None:
    store = InMemoryStore()
    incident = _golden_setup(store)
    (tmp_path / "checkout-api").mkdir()
    with pytest.raises(SandboxSetupError, match="failing closed"):
        _executor(store, fixtures_root=tmp_path).execute(incident)
    assert store.list_patch_executions(incident.id) == []


def test_drifted_source_fails_closed(tmp_path: Path) -> None:
    store = InMemoryStore()
    incident = _golden_setup(store)
    # Clone the real fixture, then tamper with one source byte.
    source = FIXTURES_ROOT / "checkout-api"
    clone = tmp_path / "checkout-api"
    for path in source.rglob("*"):
        if path.is_file():
            target = clone / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    tampered = clone / "repo" / "src" / "checkout.ts"
    tampered.write_text(
        tampered.read_text(encoding="utf-8") + "\n// tampered\n", encoding="utf-8"
    )
    with pytest.raises(SandboxSetupError, match="drifted"):
        _executor(store, fixtures_root=tmp_path).execute(incident)
    assert store.list_patch_executions(incident.id) == []


# --- End-to-end API flow --------------------------------------------------------------


def _start_and_get_approval(client: TestClient) -> dict[str, Any]:
    assert client.post("/api/v1/incidents/inc-demo-0001/start").status_code == 200
    approvals = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()
    assert len(approvals) == 1
    result: dict[str, Any] = approvals[0]
    return result


def test_api_golden_approval_runs_sandbox_and_reaches_review_ready(
    client: TestClient,
) -> None:
    approval = _start_and_get_approval(client)
    decision = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        json={"decision": "approved", "reason": "golden path"},
    )
    assert decision.status_code == 200

    incident = client.get("/api/v1/incidents/inc-demo-0001").json()
    assert incident["state"] == "REVIEW_READY"

    executions = client.get("/api/v1/incidents/inc-demo-0001/patch-executions").json()
    assert len(executions) == 1
    execution = executions[0]
    assert execution["status"] == "succeeded"
    assert execution["simulated"] is True
    assert execution["engine_id"] == "fixture-codex"
    assert execution["approval_id"] == approval["id"]
    assert execution["workspace_destroyed"] is True
    assert execution["source_fixture_intact"] is True
    assert execution["unified_diff"] == GOLDEN_DIFF.read_text(encoding="utf-8")

    patches = client.get("/api/v1/incidents/inc-demo-0001/patches").json()
    assert len(patches) == 1
    assert patches[0]["diff"] == execution["unified_diff"]
    assert patches[0]["files_changed"] == 2
    assert patches[0]["lines_changed"] == 7


def test_api_rejected_approval_never_touches_a_workspace(client: TestClient) -> None:
    approval = _start_and_get_approval(client)
    decision = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        json={"decision": "rejected", "reason": "not safe"},
    )
    assert decision.status_code == 200
    incident = client.get("/api/v1/incidents/inc-demo-0001").json()
    assert incident["state"] == "CANCELLED"
    assert client.get("/api/v1/incidents/inc-demo-0001/patch-executions").json() == []
    assert client.get("/api/v1/incidents/inc-demo-0001/patches").json() == []
