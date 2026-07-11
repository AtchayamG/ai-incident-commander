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
    InvestigationProvider,
    PullRequestProvider,
    TelemetryProvider,
    VerificationRunner,
)
from app.providers.simulated import (
    SimulatedCodeAgentGateway,
    SimulatedInvestigationProvider,
    SimulatedPullRequestProvider,
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
    summary="Guard against missing discount object",
    steps=["step"],
    risk_level=RiskLevel.MEDIUM,
    max_files_changed=1,
    max_lines_changed=10,
)


def test_simulated_providers_satisfy_protocols() -> None:
    assert isinstance(SimulatedTelemetryProvider(), TelemetryProvider)
    assert isinstance(SimulatedInvestigationProvider(), InvestigationProvider)
    assert isinstance(SimulatedCodeAgentGateway(), CodeAgentGateway)
    assert isinstance(SimulatedVerificationRunner(), VerificationRunner)
    assert isinstance(SimulatedPullRequestProvider(), PullRequestProvider)


def test_telemetry_is_deterministic_and_labelled_simulated() -> None:
    provider = SimulatedTelemetryProvider()
    first = provider.fetch_evidence(INCIDENT)
    second = provider.fetch_evidence(INCIDENT)
    assert first == second
    assert all(e.provenance.get("simulated") is True for e in first)
    assert all("[SIMULATED]" in e.summary for e in first)


def test_patch_respects_change_budget_shape() -> None:
    proposal = SimulatedCodeAgentGateway().propose_patch(INCIDENT, PLAN)
    assert proposal.files_changed <= PLAN.max_files_changed
    assert proposal.lines_changed <= PLAN.max_lines_changed
    assert proposal.diff.startswith("---")


def test_pull_request_receipt_is_simulated_and_idempotent_keyed() -> None:
    provider = SimulatedPullRequestProvider()
    receipt = provider.create_draft_pr(INCIDENT, "diff", "key-123")
    assert receipt.simulated is True
    assert receipt.idempotency_key == "key-123"
    assert receipt.url == provider.create_draft_pr(INCIDENT, "diff", "key-123").url
