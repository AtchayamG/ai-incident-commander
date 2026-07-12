"""Simulated providers must satisfy the protocol interfaces and stay deterministic."""

from datetime import UTC, datetime

from app.domain.contracts import Incident, RemediationPlan
from app.domain.enums import (
    Environment,
    ProviderMode,
    RiskLevel,
    Severity,
    WorkflowState,
)
from app.providers.base import (
    CodeAgentGateway,
    DeploymentHistoryProvider,
    EvidenceSource,
    InvestigationProvider,
    LocalRepositoryProvider,
    PullRequestProvider,
    RunbookProvider,
    TelemetryProvider,
    VerificationRunner,
)
from app.providers.simulated import (
    SimulatedCodeAgentGateway,
    SimulatedDeploymentHistoryProvider,
    SimulatedInvestigationProvider,
    SimulatedLocalRepositoryProvider,
    SimulatedPullRequestProvider,
    SimulatedRunbookProvider,
    SimulatedTelemetryProvider,
    SimulatedVerificationRunner,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)

INCIDENT = Incident(
    id="inc-test-0001",
    title="Checkout API elevated 500 errors",
    service="checkout-api",
    environment=Environment.PRODUCTION,
    severity=Severity.SEV2,
    summary="HTTP 500 rate exceeded 12% after deployment.",
    state=WorkflowState.RECEIVED,
    provider_mode=ProviderMode.SIMULATED,
    created_at=NOW,
    updated_at=NOW,
)

PLAN = RemediationPlan(
    id="plan-0001",
    incident_id=INCIDENT.id,
    hypothesis_id="hyp-0001",
    summary="Restore optional discount access",
    steps=["step"],
    risk_level=RiskLevel.MEDIUM,
    max_files_changed=2,
    max_lines_changed=40,
)

EVIDENCE_SOURCES = (
    SimulatedTelemetryProvider(),
    SimulatedDeploymentHistoryProvider(),
    SimulatedLocalRepositoryProvider(),
    SimulatedRunbookProvider(),
)


def test_simulated_providers_satisfy_protocols() -> None:
    assert isinstance(SimulatedTelemetryProvider(), TelemetryProvider)
    assert isinstance(SimulatedDeploymentHistoryProvider(), DeploymentHistoryProvider)
    assert isinstance(SimulatedLocalRepositoryProvider(), LocalRepositoryProvider)
    assert isinstance(SimulatedRunbookProvider(), RunbookProvider)
    assert isinstance(SimulatedInvestigationProvider(), InvestigationProvider)
    assert isinstance(SimulatedCodeAgentGateway(), CodeAgentGateway)
    assert isinstance(SimulatedVerificationRunner(), VerificationRunner)
    assert isinstance(SimulatedPullRequestProvider(), PullRequestProvider)
    for source in EVIDENCE_SOURCES:
        assert isinstance(source, EvidenceSource)


def test_evidence_sources_are_deterministic_and_labelled_simulated() -> None:
    for source in EVIDENCE_SOURCES:
        first = source.fetch_evidence(INCIDENT)
        second = source.fetch_evidence(INCIDENT)
        assert first == second
        assert first, f"{type(source).__name__} produced no evidence"
        for raw in first:
            assert raw.provenance.get("simulated") is True
            assert "[SIMULATED]" in raw.summary
            assert raw.provider.startswith("fixture-")
            assert raw.display_ref.startswith("simulated://checkout-api/")
            assert raw.observed_at.tzinfo is not None


def test_deployment_history_correlates_commit_and_deploy() -> None:
    items = SimulatedDeploymentHistoryProvider().fetch_evidence(INCIDENT)
    deploy = next(i for i in items if i.kind == "deploy")
    commit = next(i for i in items if i.kind == "diff")
    assert "2026.07.13.4" in deploy.summary
    assert deploy.observed_at == datetime(2026, 7, 13, 10, 2, tzinfo=UTC)
    assert "c7f2e9a" in commit.summary
    assert commit.observed_at == datetime(2026, 7, 13, 9, 48, tzinfo=UTC)
    assert "session.discount.code" in commit.content
    assert "session.discount?.code ?? null" in commit.content


def test_patch_respects_change_budget_shape() -> None:
    proposal = SimulatedCodeAgentGateway().propose_patch(INCIDENT, PLAN)
    assert proposal.files_changed <= PLAN.max_files_changed
    assert proposal.lines_changed <= PLAN.max_lines_changed
    assert proposal.diff.startswith("---")
    assert "session.discount?.code ?? null" in proposal.diff


def test_pull_request_receipt_is_simulated_and_idempotent_keyed() -> None:
    provider = SimulatedPullRequestProvider()
    receipt = provider.create_draft_pr(INCIDENT, "diff", "key-123")
    assert receipt.simulated is True
    assert receipt.idempotency_key == "key-123"
    assert receipt.url == provider.create_draft_pr(INCIDENT, "diff", "key-123").url
