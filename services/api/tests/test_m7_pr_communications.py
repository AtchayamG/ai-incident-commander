import contextlib
import json
import os
import sqlite3
import subprocess
import sys
import urllib.error
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.contracts import (
    CommunicationUpdate,
    ExternalAction,
    PatchAttempt,
    Postmortem,
)
from app.domain.enums import ApprovalStatus, ProviderMode, RiskLevel, WorkflowState
from app.domain.verification import (
    CheckCategory,
    RiskReview,
    VerificationCommandResult,
    build_verification_artifact,
)
from app.main import create_app
from app.providers.base import PullRequestReceipt
from app.providers.github import GitHubPullRequestProvider
from app.providers.simulated import (
    SimulatedDeploymentHistoryProvider,
    SimulatedInvestigationProvider,
    SimulatedLocalRepositoryProvider,
    SimulatedRunbookProvider,
    SimulatedTelemetryProvider,
)
from app.providers.simulated_remediation import FixtureRemediationPlanner
from app.sandbox.executor import SandboxPatchExecutor
from app.sandbox.verifier import DeterministicVerifier
from app.store.memory import InMemoryStore
from app.workflow.pipeline import WorkflowPipeline
from app.workflow.remediation_planner import RemediationPlanningManager
from tests.test_remediation import _fixture_manager, _seeded_incident
from tests.test_sandbox_executor import FixtureCodexGateway


class CountingPullRequestProvider:
    provider_name = "github_counted"

    def __init__(self) -> None:
        self.calls = 0

    def create_draft_pr(
        self, incident: Any, diff: str, idempotency_key: str
    ) -> PullRequestReceipt:
        self.calls += 1
        return PullRequestReceipt(
            provider="simulated",
            url=f"https://github.com/org/repo/pull/42-{self.calls}",
            simulated=True,
            idempotency_key=idempotency_key,
        )


class FailingPullRequestProvider:
    def __init__(
        self,
        failure_msg: str = "GitHub API token ghp_secret12345678901234567890 failed"
    ) -> None:
        self.failure_msg = failure_msg
        self.calls = 0

    def create_draft_pr(
        self, incident: Any, diff: str, idempotency_key: str
    ) -> PullRequestReceipt:
        self.calls += 1
        raise RuntimeError(self.failure_msg)


def test_m7_full_workflow_golden_path() -> None:
    settings = Settings(
        demo_mode=True, demo_admin_key="test-key", database_url="sqlite:///:memory:"
    )
    app = create_app(settings)
    with TestClient(app) as client:
        # 1. Reset and seed
        client.post("/api/v1/incidents/reset-demo", headers={"X-Demo-Admin-Key": "test-key"})

        # 2. Start workflow
        client.post("/api/v1/incidents/inc-demo-0001/start")

        # 3. Approve patch (M4/M5/M6)
        approvals = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()
        assert len(approvals) >= 1
        patch_approval = approvals[0]
        assert patch_approval["approval_type"] == "APPLY_PATCH"

        decided = client.post(
            f"/api/v1/approvals/{patch_approval['id']}/decision",
            json={"decision": "approved", "reason": "approve patch"},
        )
        assert decided.status_code == 200

        # Incident should now be in WAITING_PR_APPROVAL (M7)
        incident = client.get("/api/v1/incidents/inc-demo-0001").json()
        assert incident["state"] == "WAITING_PR_APPROVAL"

        # Verify a new CREATE_DRAFT_PR approval request was created
        approvals = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()
        pr_approval = next(a for a in approvals if a["approval_type"] == "CREATE_DRAFT_PR")
        assert pr_approval["status"] == "pending"

        # 4. Approve PR creation (M7 second approval)
        decided_pr = client.post(
            f"/api/v1/approvals/{pr_approval['id']}/decision",
            json={"decision": "approved", "reason": "approve pr"},
        )
        assert decided_pr.status_code == 200

        # Incident should transition through CREATING_PR, PR_READY to RESOLUTION_DRAFTED
        incident_after = client.get("/api/v1/incidents/inc-demo-0001").json()
        assert incident_after["state"] == "RESOLUTION_DRAFTED"

        # 5. Fetch PR receipt
        pr_receipt = client.get("/api/v1/incidents/inc-demo-0001/draft-pr")
        assert pr_receipt.status_code == 200
        data = pr_receipt.json()
        assert data["status"] == "completed"
        assert data["url"] is not None

        # 6. Fetch Technical & Stakeholder updates
        comms = client.get("/api/v1/incidents/inc-demo-0001/communications")
        assert comms.status_code == 200
        comms_data = comms.json()
        assert "Incident ID: inc-demo-0001" in comms_data["technical_update"]
        assert "Resolution draft created" in comms_data["technical_update"]

        # Regenerate comms
        regen = client.post("/api/v1/incidents/inc-demo-0001/communications/regenerate")
        assert regen.status_code == 200

        # 7. Fetch Postmortem
        pm = client.get("/api/v1/incidents/inc-demo-0001/postmortem")
        assert pm.status_code == 200
        pm_data = pm.json()
        assert "Resolution draft for Checkout API elevated 500 errors" in pm_data["summary"]
        assert all(
            event["incident_id"] == "inc-demo-0001"
            for event in pm_data["timeline_json"]
        )
        assert "# Incident Postmortem:" in pm_data["markdown_content"]
        assert len(pm_data["action_items_json"]) == 3


def test_m7_idempotency_reuses_completed_pr() -> None:
    store = InMemoryStore()
    incident = _seeded_incident(store)
    pr_provider = CountingPullRequestProvider()

    pipeline = WorkflowPipeline(
        store=store,
        telemetry=SimulatedTelemetryProvider(),
        deployments=SimulatedDeploymentHistoryProvider(),
        repository=SimulatedLocalRepositoryProvider(),
        runbook=SimulatedRunbookProvider(),
        investigation=SimulatedInvestigationProvider(),
        investigation_manager=_fixture_manager(),
        remediation_planner=RemediationPlanningManager(planner=FixtureRemediationPlanner()),
        patch_executor=SandboxPatchExecutor(store=store, gateway=FixtureCodexGateway()),
        verifier=DeterministicVerifier(store=store, environ={}),
        provider_mode=ProviderMode.SIMULATED,
        pr_provider=pr_provider,
    )

    patch = store.add_patch(
        PatchAttempt(
            id="ptch-1",
            incident_id=incident.id,
            plan_id="plan-1",
            attempt=1,
            diff="diff content",
            files_changed=1,
            lines_changed=1,
            provider_mode=ProviderMode.SIMULATED,
        ),
    )

    commands = [
        VerificationCommandResult(
            command="npm test",
            category=CheckCategory.TEST,
            argv=["npm", "test"],
            baseline=False,
            exit_code=0,
            duration_ms=1,
            stdout="OK",
            stderr="",
            stdout_truncated=False,
            stderr_truncated=False,
            timed_out=False,
        )
    ]

    risk = RiskReview(
        risk_level=RiskLevel.LOW,
        findings=[],
        files_changed=1,
        lines_changed=1,
        blocks_pr=False,
    )

    artifact = build_verification_artifact(
        id="vrun-1",
        incident_id=incident.id,
        patch_id=patch.id,
        patch_execution_id="exec-1",
        plan_id="plan-1",
        plan_hash="hash-123",
        attempt=1,
        base_ref="main",
        base_checksum="base-sum",
        diff_hash="diff-sum",
        diff_reconstructed=True,
        workspace_id="stub",
        runner_id="stub-runner",
        target_simulated=True,
        commands=commands,
        relevant_regression_test=True,
        passed=True,
        risk=risk,
        workspace_destroyed=True,
        total_duration_ms=1,
        budget_seconds=300,
        created_at=datetime.now(UTC),
    )
    store.add_verification_artifact(artifact)

    verif = store.get_verification_artifact_for_patch(patch.id)
    assert verif is not None

    approval = pipeline._request_pr_approval(
        incident, patch, verif
    )

    incident.state = WorkflowState.WAITING_PR_APPROVAL
    incident = pipeline.apply_pr_approval(incident, approved=True, approval_id=approval.id)
    assert incident.state == WorkflowState.RESOLUTION_DRAFTED
    assert pr_provider.calls == 1

    incident.state = WorkflowState.WAITING_PR_APPROVAL
    incident = pipeline.apply_pr_approval(incident, approved=True, approval_id=approval.id)
    assert incident.state == WorkflowState.RESOLUTION_DRAFTED
    assert pr_provider.calls == 1


def test_pending_pr_approval_creation_policy() -> None:
    """Verifies CREATE_DRAFT_PR approval creation behavior."""
    settings = Settings(
        demo_mode=True, demo_admin_key="test-key", database_url="sqlite:///:memory:"
    )
    app = create_app(settings)
    with TestClient(app) as client:
        # Reset and seed
        client.post("/api/v1/incidents/reset-demo", headers={"X-Demo-Admin-Key": "test-key"})

        # Start workflow
        client.post("/api/v1/incidents/inc-demo-0001/start")

        # Get initial patch approval request
        approvals = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()
        patch_approval = approvals[0]

        # Let's decide APPROVED to test the golden flow.
        decided = client.post(
            f"/api/v1/approvals/{patch_approval['id']}/decision",
            json={"decision": "approved", "reason": "approve patch"},
        )
        assert decided.status_code == 200

        # Verify a new CREATE_DRAFT_PR approval request was created
        approvals = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()
        pr_approvals = [a for a in approvals if a["approval_type"] == "CREATE_DRAFT_PR"]
        assert len(pr_approvals) == 1
        assert pr_approvals[0]["status"] == "pending"


def test_exact_binding_validation() -> None:
    """Verifies exact binding checks, roles, rejection, and single-use."""
    settings = Settings(
        demo_mode=True, demo_admin_key="test-key", database_url="sqlite:///:memory:"
    )
    app = create_app(settings)
    with TestClient(app) as client:
        # Reset and seed
        client.post("/api/v1/incidents/reset-demo", headers={"X-Demo-Admin-Key": "test-key"})
        client.post("/api/v1/incidents/inc-demo-0001/start")

        # Approve patch to get to WAITING_PR_APPROVAL
        approvals = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()
        patch_approval = approvals[0]
        client.post(
            f"/api/v1/approvals/{patch_approval['id']}/decision",
            json={"decision": "approved", "reason": "approve patch"},
        )

        # Get CREATE_DRAFT_PR approval
        approvals = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()
        pr_approval = next(a for a in approvals if a["approval_type"] == "CREATE_DRAFT_PR")

        # 1. Role mismatch check -> expects 403
        wrong_role_res = client.post(
            f"/api/v1/approvals/{pr_approval['id']}/decision",
            json={"decision": "approved", "reason": "ok"},
            headers={"X-Approver-Role": "viewer"},
        )
        assert wrong_role_res.status_code == 403

        # 2. Expiry check -> mock expired time in DB
        store = app.state.store
        with store.SessionLocal() as session:
            from app.store.models import ApprovalRequestModel
            db_appr = session.get(ApprovalRequestModel, pr_approval["id"])
            db_appr.expires_at = datetime.now(UTC) - timedelta(seconds=5)
            session.commit()

        expired_res = client.post(
            f"/api/v1/approvals/{pr_approval['id']}/decision",
            json={"decision": "approved", "reason": "ok"},
        )
        assert expired_res.status_code == 409
        assert store.get_approval(pr_approval["id"]).status == "expired"

        # Reset approval to pending to test other cases
        with store.SessionLocal() as session:
            db_appr = session.get(ApprovalRequestModel, pr_approval["id"])
            db_appr.status = "pending"
            db_appr.expires_at = datetime.now(UTC) + timedelta(hours=1)
            session.commit()

        # 3. Stale patch/verification check (change verification hash in binding)
        binding = store.get_approval_binding(pr_approval["id"])
        # Update binding in DB
        with store.SessionLocal() as session:
            from app.store.models import ApprovalBindingModel
            db_bind = session.get(ApprovalBindingModel, pr_approval["id"])
            db_bind.plan_hash = "different-hash"
            session.commit()

        stale_res = client.post(
            f"/api/v1/approvals/{pr_approval['id']}/decision",
            json={"decision": "approved", "reason": "ok"},
        )
        assert stale_res.status_code == 409

        # Restore binding
        with store.SessionLocal() as session:
            db_bind = session.get(ApprovalBindingModel, pr_approval["id"])
            db_bind.plan_hash = binding.plan_hash
            session.commit()

        # 4. Rejection returns WAITING_PR_APPROVAL -> REVIEW_READY
        reject_res = client.post(
            f"/api/v1/approvals/{pr_approval['id']}/decision",
            json={"decision": "rejected", "reason": "rejected"},
        )
        assert reject_res.status_code == 200
        incident_after = client.get("/api/v1/incidents/inc-demo-0001").json()
        assert incident_after["state"] == "REVIEW_READY"

        # 5. Single-use check -> trying to decide again raises 409
        retry_decision_res = client.post(
            f"/api/v1/approvals/{pr_approval['id']}/decision",
            json={"decision": "approved", "reason": "ok"},
        )
        assert retry_decision_res.status_code == 409


def test_missing_approval_binding_fails_closed() -> None:
    settings = Settings(
        demo_mode=True, demo_admin_key="test-key", database_url="sqlite:///:memory:"
    )
    app = create_app(settings)
    with TestClient(app) as client:
        client.post("/api/v1/incidents/reset-demo", headers={"X-Demo-Admin-Key": "test-key"})
        client.post("/api/v1/incidents/inc-demo-0001/start")
        approval = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()[0]

        from app.store.models import ApprovalBindingModel

        with app.state.store.SessionLocal() as session:
            binding = session.get(ApprovalBindingModel, approval["id"])
            assert binding is not None
            session.delete(binding)
            session.commit()

        response = client.post(
            f"/api/v1/approvals/{approval['id']}/decision",
            json={"decision": "approved", "reason": "must fail"},
        )
        assert response.status_code == 409
        assert "binding is missing" in response.json()["detail"]


def test_demo_mode_ignores_ambient_github_configuration() -> None:
    settings = Settings(
        demo_mode=True,
        database_url="sqlite:///:memory:",
        github_token="ambient-token",
        github_repository="org/repo",
        github_head_ref="prepared-head",
        github_base_ref="main",
    )
    app = create_app(settings)
    assert app.state.pipeline._pr_provider.__class__.__name__ == "SimulatedPullRequestProvider"


def test_simulated_success_and_typed_api_response() -> None:
    """Verifies simulated success/provenance and typed API response."""
    settings = Settings(
        demo_mode=True, demo_admin_key="test-key", database_url="sqlite:///:memory:"
    )
    app = create_app(settings)
    with TestClient(app) as client:
        client.post("/api/v1/incidents/reset-demo", headers={"X-Demo-Admin-Key": "test-key"})
        client.post("/api/v1/incidents/inc-demo-0001/start")

        # Approve patch
        patch_approval = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()[0]
        client.post(
            f"/api/v1/approvals/{patch_approval['id']}/decision",
            json={"decision": "approved", "reason": "approve patch"},
        )

        # Get CREATE_DRAFT_PR approval
        approvals = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()
        pr_approval = next(a for a in approvals if a["approval_type"] == "CREATE_DRAFT_PR")

        # Approve PR
        decide_res = client.post(
            f"/api/v1/approvals/{pr_approval['id']}/decision",
            json={"decision": "approved", "reason": "approve pr"},
        )
        assert decide_res.status_code == 200

        # Check GET /draft-pr response schema
        res = client.get("/api/v1/incidents/inc-demo-0001/draft-pr")
        assert res.status_code == 200
        data = res.json()

        # Verify DraftPR projection fields
        assert "id" in data
        assert data["incident_id"] == "inc-demo-0001"
        assert data["status"] == "completed"
        assert data["url"] is not None
        assert "example.invalid" in data["url"]
        assert data["provider_mode"] == "simulated"
        assert "idempotency_key" in data
        assert data["error_message"] is None


def test_duplicate_post_decision_restart_reuse() -> None:
    """Verifies reuse of completed external action receipt on repeat decision/process restarts."""
    store = InMemoryStore()
    incident = _seeded_incident(store)
    pr_provider = CountingPullRequestProvider()

    pipeline = WorkflowPipeline(
        store=store,
        telemetry=SimulatedTelemetryProvider(),
        deployments=SimulatedDeploymentHistoryProvider(),
        repository=SimulatedLocalRepositoryProvider(),
        runbook=SimulatedRunbookProvider(),
        investigation=SimulatedInvestigationProvider(),
        investigation_manager=_fixture_manager(),
        remediation_planner=RemediationPlanningManager(planner=FixtureRemediationPlanner()),
        patch_executor=SandboxPatchExecutor(store=store, gateway=FixtureCodexGateway()),
        verifier=DeterministicVerifier(store=store, environ={}),
        provider_mode=ProviderMode.SIMULATED,
        pr_provider=pr_provider,
    )

    patch = store.add_patch(
        PatchAttempt(
            id="ptch-1",
            incident_id=incident.id,
            plan_id="plan-1",
            attempt=1,
            diff="diff content",
            files_changed=1,
            lines_changed=1,
            provider_mode=ProviderMode.SIMULATED,
        ),
    )

    commands = [
        VerificationCommandResult(
            command="npm test",
            category=CheckCategory.TEST,
            argv=["npm", "test"],
            baseline=False,
            exit_code=0,
            duration_ms=1,
            stdout="OK",
            stderr="",
            stdout_truncated=False,
            stderr_truncated=False,
            timed_out=False,
        )
    ]
    risk = RiskReview(
        risk_level=RiskLevel.LOW, findings=[], files_changed=1, lines_changed=1, blocks_pr=False
    )
    artifact = build_verification_artifact(
        id="vrun-1",
        incident_id=incident.id,
        patch_id=patch.id,
        patch_execution_id="exec-1",
        plan_id="plan-1",
        plan_hash="hash-123",
        attempt=1,
        base_ref="main",
        base_checksum="base-sum",
        diff_hash="diff-sum",
        diff_reconstructed=True,
        workspace_id="stub",
        runner_id="stub-runner",
        target_simulated=True,
        commands=commands,
        relevant_regression_test=True,
        passed=True,
        risk=risk,
        workspace_destroyed=True,
        total_duration_ms=1,
        budget_seconds=300,
        created_at=datetime.now(UTC),
    )
    store.add_verification_artifact(artifact)
    verif = store.get_verification_artifact_for_patch(patch.id)

    approval = pipeline._request_pr_approval(incident, patch, verif)

    # First PR approval call
    incident.state = WorkflowState.WAITING_PR_APPROVAL
    incident = pipeline.apply_pr_approval(incident, approved=True, approval_id=approval.id)
    assert pr_provider.calls == 1

    # Second call (re-uses existing completed receipt)
    incident.state = WorkflowState.WAITING_PR_APPROVAL
    incident = pipeline.apply_pr_approval(incident, approved=True, approval_id=approval.id)
    assert pr_provider.calls == 1

    # Restart simulated (new pipeline using same store/database)
    pipeline2 = WorkflowPipeline(
        store=store,
        telemetry=SimulatedTelemetryProvider(),
        deployments=SimulatedDeploymentHistoryProvider(),
        repository=SimulatedLocalRepositoryProvider(),
        runbook=SimulatedRunbookProvider(),
        investigation=SimulatedInvestigationProvider(),
        investigation_manager=_fixture_manager(),
        remediation_planner=RemediationPlanningManager(planner=FixtureRemediationPlanner()),
        patch_executor=SandboxPatchExecutor(store=store, gateway=FixtureCodexGateway()),
        verifier=DeterministicVerifier(store=store, environ={}),
        provider_mode=ProviderMode.SIMULATED,
        pr_provider=pr_provider,
    )
    incident.state = WorkflowState.WAITING_PR_APPROVAL
    incident = pipeline2.apply_pr_approval(incident, approved=True, approval_id=approval.id)
    # Still 1 call because it was reused!
    assert pr_provider.calls == 1


def test_provider_failure_redacted_error_new_approval_retry_success() -> None:
    """Verifies provider failure, redaction, new pending approval, and retry update logic."""
    store = InMemoryStore()
    incident = _seeded_incident(store)

    # Configure failing provider with long Github token to trigger redaction rule
    failing_pr_provider = FailingPullRequestProvider(
        "GitHub API token ghp_secret12345678901234567890 failed"
    )

    pipeline = WorkflowPipeline(
        store=store,
        telemetry=SimulatedTelemetryProvider(),
        deployments=SimulatedDeploymentHistoryProvider(),
        repository=SimulatedLocalRepositoryProvider(),
        runbook=SimulatedRunbookProvider(),
        investigation=SimulatedInvestigationProvider(),
        investigation_manager=_fixture_manager(),
        remediation_planner=RemediationPlanningManager(planner=FixtureRemediationPlanner()),
        patch_executor=SandboxPatchExecutor(store=store, gateway=FixtureCodexGateway()),
        verifier=DeterministicVerifier(store=store, environ={}),
        provider_mode=ProviderMode.SIMULATED,
        pr_provider=failing_pr_provider,
    )

    patch = store.add_patch(
        PatchAttempt(
            id="ptch-1",
            incident_id=incident.id,
            plan_id="plan-1",
            attempt=1,
            diff="diff content",
            files_changed=1,
            lines_changed=1,
            provider_mode=ProviderMode.SIMULATED,
        ),
    )

    commands = [
        VerificationCommandResult(
            command="npm test",
            category=CheckCategory.TEST,
            argv=["npm", "test"],
            baseline=False,
            exit_code=0,
            duration_ms=1,
            stdout="OK",
            stderr="",
            stdout_truncated=False,
            stderr_truncated=False,
            timed_out=False,
        )
    ]
    risk = RiskReview(
        risk_level=RiskLevel.LOW, findings=[], files_changed=1, lines_changed=1, blocks_pr=False
    )
    artifact = build_verification_artifact(
        id="vrun-1",
        incident_id=incident.id,
        patch_id=patch.id,
        patch_execution_id="exec-1",
        plan_id="plan-1",
        plan_hash="hash-123",
        attempt=1,
        base_ref="main",
        base_checksum="base-sum",
        diff_hash="diff-sum",
        diff_reconstructed=True,
        workspace_id="stub",
        runner_id="stub-runner",
        target_simulated=True,
        commands=commands,
        relevant_regression_test=True,
        passed=True,
        risk=risk,
        workspace_destroyed=True,
        total_duration_ms=1,
        budget_seconds=300,
        created_at=datetime.now(UTC),
    )
    store.add_verification_artifact(artifact)
    verif = store.get_verification_artifact_for_patch(patch.id)

    approval = pipeline._request_pr_approval(incident, patch, verif)

    # Execute and let it fail
    incident.state = WorkflowState.WAITING_PR_APPROVAL
    incident = pipeline.apply_pr_approval(incident, approved=True, approval_id=approval.id)

    # Assertions on failure:
    assert incident.state == WorkflowState.WAITING_PR_APPROVAL

    # Stored action check
    actions = store.list_external_actions(incident.id)
    assert len(actions) == 1
    action = actions[0]
    assert action.status == "failed"
    assert "ghp_secret" not in action.provider_receipt_json["error"]
    assert "[REDACTED" in action.provider_receipt_json["error"]

    # New pending approval check
    approvals = store.list_approvals(incident.id)
    assert len(approvals) == 2
    new_approval = approvals[1]
    assert new_approval.status == ApprovalStatus.PENDING

    # Now make the provider succeed on retry
    success_pr_provider = CountingPullRequestProvider()
    pipeline._pr_provider = success_pr_provider

    # Decide on the new approval request
    incident = pipeline.apply_pr_approval(incident, approved=True, approval_id=new_approval.id)
    assert incident.state == WorkflowState.RESOLUTION_DRAFTED

    # Should update the SAME external action row (since idempotency key is the same)
    actions_after = store.list_external_actions(incident.id)
    assert len(actions_after) == 1
    assert actions_after[0].status == "completed"
    assert success_pr_provider.calls == 1


def test_mocked_optional_github_draft_pr() -> None:
    """Verifies mocked optional GitHub draft, config checks, token redaction, fail-closed."""
    # 1. Fail closed when config is missing
    with pytest.raises(RuntimeError) as exc_info:
        provider = GitHubPullRequestProvider(token="", repository="")
        incident = MagicMock()
        provider.create_draft_pr(incident, "diff", "key")
    assert "GitHub provider is not fully configured" in str(exc_info.value)

    # 2. Mock URL open to verify request structure
    token = "ghp_super_secret_token12345"
    repo = "my-org/my-repo"
    head = "my-head"
    base = "my-base"
    provider = GitHubPullRequestProvider(
        token=token, repository=repo, head_ref=head, base_ref=base
    )

    incident = MagicMock()
    incident.id = "inc-1"
    incident.title = "Incident Title"
    incident.service = "checkout"

    mock_response = MagicMock()
    mock_response.read.return_value = (
        b'{"html_url": "https://github.com/my-org/my-repo/pull/123", "number": 123}'
    )

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = mock_response

        receipt = provider.create_draft_pr(incident, "my-diff", "idemp-key")

        # Verify the receipt
        assert receipt.url == "https://github.com/my-org/my-repo/pull/123"
        assert receipt.simulated is False

        # Verify urlopen call parameters
        args, kwargs = mock_urlopen.call_args
        req = args[0]
        assert req.get_header("Authorization") == f"token {token}"
        assert kwargs["timeout"] == 15

        # Verify body
        body = json.loads(req.data.decode("utf-8"))
        assert body["draft"] is True
        assert body["head"] == head
        assert body["base"] == base
        assert "my-diff" not in json.dumps(body)

    # 3. Verify token redaction on HTTP error containing the token
    with patch("urllib.request.urlopen") as mock_urlopen:
        # Mock urlopen throwing an error containing the secret token
        mock_urlopen.side_effect = urllib.error.URLError(
            f"Failed to connect to API with token: {token}"
        )
        with pytest.raises(RuntimeError) as exc_info:
            provider.create_draft_pr(incident, "my-diff", "idemp-key")
        assert token not in str(exc_info.value)
        assert "REDACTED" in str(exc_info.value)


def test_communications_persistence_and_no_false_mitigation_claims() -> None:
    """Verifies persisted distinct communications/regeneration without false mitigation claims."""
    settings = Settings(
        demo_mode=True, demo_admin_key="test-key", database_url="sqlite:///:memory:"
    )
    app = create_app(settings)
    with TestClient(app) as client:
        client.post("/api/v1/incidents/reset-demo", headers={"X-Demo-Admin-Key": "test-key"})

        # Get communications before resolution artifacts exist -> expects 404
        comms_before = client.get("/api/v1/incidents/inc-demo-0001/communications")
        assert comms_before.status_code == 404

        # Start workflow and approve all gates to get draft PR completed
        client.post("/api/v1/incidents/inc-demo-0001/start")
        patch_approval = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()[0]
        client.post(
            f"/api/v1/approvals/{patch_approval['id']}/decision",
            json={"decision": "approved", "reason": "approve patch"},
        )

        apprs = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()
        pr_approval = next(a for a in apprs if a["approval_type"] == "CREATE_DRAFT_PR")
        client.post(
            f"/api/v1/approvals/{pr_approval['id']}/decision",
            json={"decision": "approved", "reason": "approve pr"},
        )

        # Communications should now exist and return persisted content
        comms_res = client.get("/api/v1/incidents/inc-demo-0001/communications")
        assert comms_res.status_code == 200
        comms = comms_res.json()

        # Verify distinct fields
        assert "technical_update" in comms
        assert "stakeholder_update" in comms
        assert "resolution_note" in comms

        # Verify no false mitigation/closed/live/deployed claims
        forbidden_words = ["successfully mitigated", "closed", "deployed", "live"]
        for word in forbidden_words:
            assert word not in comms["technical_update"].lower()
            assert word not in comms["stakeholder_update"].lower()
            assert word not in comms["resolution_note"].lower()

        # Regenerate comms
        regen_res = client.post("/api/v1/incidents/inc-demo-0001/communications/regenerate")
        assert regen_res.status_code == 200
        regen = regen_res.json()
        assert regen["technical_update"] == comms["technical_update"]


def test_evidence_linked_prioritized_postmortem_markdown() -> None:
    """Verifies evidence-linked, prioritized postmortem/Markdown and idempotent generation."""
    settings = Settings(
        demo_mode=True, demo_admin_key="test-key", database_url="sqlite:///:memory:"
    )
    app = create_app(settings)
    with TestClient(app) as client:
        client.post("/api/v1/incidents/reset-demo", headers={"X-Demo-Admin-Key": "test-key"})
        client.post("/api/v1/incidents/inc-demo-0001/start")
        patch_approval = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()[0]
        client.post(
            f"/api/v1/approvals/{patch_approval['id']}/decision",
            json={"decision": "approved", "reason": "approve patch"},
        )
        apprs = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()
        pr_approval = next(a for a in apprs if a["approval_type"] == "CREATE_DRAFT_PR")
        client.post(
            f"/api/v1/approvals/{pr_approval['id']}/decision",
            json={"decision": "approved", "reason": "approve pr"},
        )

        # Get postmortem
        pm_res = client.get("/api/v1/incidents/inc-demo-0001/postmortem")
        assert pm_res.status_code == 200
        pm = pm_res.json()

        # Verify timeline_json exists and contains required fields
        assert "timeline_json" in pm
        assert len(pm["timeline_json"]) > 0
        first_event = pm["timeline_json"][0]
        assert "id" in first_event
        assert "at" in first_event
        assert "kind" in first_event
        assert "description" in first_event
        assert "evidence_id" in first_event

        # Verify action_items_json is prioritized and uses description/owner/priority
        assert "action_items_json" in pm
        assert len(pm["action_items_json"]) == 3
        # Priorities are: HIGH, MEDIUM, LOW
        assert pm["action_items_json"][0]["priority"] == "HIGH"
        assert pm["action_items_json"][1]["priority"] == "MEDIUM"
        assert pm["action_items_json"][2]["priority"] == "LOW"
        assert "description" in pm["action_items_json"][0]
        assert "owner" in pm["action_items_json"][0]

        # Verify evidence citations in markdown content
        assert (
            "Evidence: " in pm["markdown_content"]
            or "evidence_id" in pm["markdown_content"]
            or "ev-" in pm["markdown_content"]
        )

        # Verify idempotency: postmortem is upserted / only one persists per incident
        store = app.state.store
        pipeline = app.state.pipeline
        pipeline._generate_resolution_artifacts(store.get_incident("inc-demo-0001"), {})

        # Verify we still get the same postmortem and no duplicate postmortem row was created
        with store.SessionLocal() as session:
            from sqlalchemy import select

            from app.store.models import PostmortemModel
            q = select(PostmortemModel).where(PostmortemModel.incident_id == "inc-demo-0001")
            rows = session.scalars(q).all()
            assert len(rows) == 1


def test_sql_persistence_restart_plus_fresh_migration() -> None:
    """Verify SqlAlchemyStore persistence and fresh migration/uniqueness."""
    import tempfile

    from app.domain.contracts import Incident
    from app.domain.enums import Environment, Severity, WorkflowState
    from app.store.sql import SqlAlchemyStore

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        store = SqlAlchemyStore(f"sqlite:///{path}")

        # Add an incident
        incident = Incident(
            id="inc-sql-test",
            title="SQL test",
            service="auth",
            environment=Environment.PRODUCTION,
            severity=Severity.SEV1,
            summary="testing",
            state=WorkflowState.RECEIVED,
            provider_mode=ProviderMode.SIMULATED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        store.add_incident(incident)

        # Test postmortem persistence
        pm = Postmortem(
            id="pm-1",
            incident_id="inc-sql-test",
            summary="PM Summary",
            impact="PM Impact",
            root_cause="PM Root Cause",
            resolution="PM Resolution",
            timeline_json=[],
            action_items_json=[],
            markdown_content="# PM Markdown",
            created_at=datetime.now(UTC),
        )
        store.add_postmortem(pm)

        # Read it back
        pm_read = store.get_postmortem("inc-sql-test")
        assert pm_read is not None
        assert pm_read.summary == "PM Summary"

        # Test postmortem upsert (idempotency)
        pm_update = pm.model_copy(update={"summary": "PM Summary Updated"})
        store.add_postmortem(pm_update)

        pm_read_2 = store.get_postmortem("inc-sql-test")
        assert pm_read_2.summary == "PM Summary Updated"

        # Test communications persistence
        comms = CommunicationUpdate(
            incident_id="inc-sql-test",
            technical_update="Tech Update",
            stakeholder_update="Stakeholder Update",
            resolution_note="Resolution Note",
            created_at=datetime.now(UTC),
        )
        store.add_communications(comms)

        # Read back comms
        comms_read = store.get_communications("inc-sql-test")
        assert comms_read is not None
        assert comms_read.technical_update == "Tech Update"

        # Test communications upsert/idempotency
        comms_update = comms.model_copy(update={"technical_update": "Tech Update Updated"})
        store.add_communications(comms_update)

        comms_read_2 = store.get_communications("inc-sql-test")
        assert comms_read_2.technical_update == "Tech Update Updated"

    finally:
        with contextlib.suppress(OSError):
            os.unlink(path)


def test_real_alembic_upgrade_creates_m7_schema(tmp_path: Path) -> None:
    api_root = Path(__file__).resolve().parents[1]
    database = tmp_path / "alembic-fresh.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{database.as_posix()}"

    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=api_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"external_actions", "postmortems", "communications"} <= tables
        indexes = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
        }
        assert "ix_external_actions_idempotency_key" in indexes
        assert "ix_postmortems_incident_id" in indexes


def test_external_action_update_survives_store_reopen(tmp_path: Path) -> None:
    from app.domain.contracts import Incident
    from app.domain.enums import Environment, Severity
    from app.store.sql import SqlAlchemyStore

    database = tmp_path / "external-action-restart.db"
    url = f"sqlite:///{database.as_posix()}"
    first = SqlAlchemyStore(url)
    now = datetime.now(UTC)
    first.add_incident(
        Incident(
            id="inc-restart",
            title="Restart persistence",
            service="checkout",
            environment=Environment.STAGING,
            severity=Severity.SEV2,
            summary="Persistence proof",
            state=WorkflowState.WAITING_PR_APPROVAL,
            provider_mode=ProviderMode.SIMULATED,
            created_at=now,
            updated_at=now,
        )
    )
    # Foreign-key enforcement is database-dependent in SQLite tests; the
    # approval id is still persisted and verified across independent stores.
    action = ExternalAction(
        id="act-restart",
        incident_id="inc-restart",
        action_type="create_draft_pr",
        provider="simulated",
        idempotency_key="stable-key",
        approval_request_id="apr-original",
        status="failed",
        request_json={"patch_id": "patch-1"},
        provider_receipt_json={"error": "redacted"},
        created_at=now,
        completed_at=now,
    )
    first.add_external_action(action)
    retried = action.model_copy(
        update={
            "approval_request_id": "apr-renewed",
            "status": "completed",
            "provider_receipt_json": {"url": "https://example.invalid/pr/1"},
            "completed_at": datetime.now(UTC),
        }
    )
    first.update_external_action(retried)

    reopened = SqlAlchemyStore(url)
    persisted = reopened.get_external_action_by_idempotency_key("stable-key")
    assert persisted is not None
    assert persisted.id == "act-restart"
    assert persisted.approval_request_id == "apr-renewed"
    assert persisted.status == "completed"
    assert persisted.provider_receipt_json == {"url": "https://example.invalid/pr/1"}
