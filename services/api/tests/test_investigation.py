"""M3 investigation: typed structured outputs, the manager stage, citation
validation, determinism, and the safe insufficient-evidence path.

These tests exercise the manager directly against deterministically built
golden evidence (no network, no credentials) and end-to-end through the
pipeline for the safety-critical no-remediation path.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.domain.contracts import EvidenceItem, Incident
from app.domain.enums import Environment, ProviderMode, Severity, WorkflowState
from app.domain.investigation import (
    EvidenceCitation,
    FalsificationTest,
    IncidentSummary,
    InvestigationDraft,
    InvestigationReport,
    InvestigationStatus,
    RankedHypothesis,
    SpecialistFinding,
    SpecialistKind,
)
from app.main import create_app
from app.providers.base import EvidenceSource, RawEvidence
from app.providers.code_agent import FixtureCodexGateway
from app.providers.simulated import (
    SimulatedDeploymentHistoryProvider,
    SimulatedInvestigationProvider,
    SimulatedLocalRepositoryProvider,
    SimulatedRunbookProvider,
    SimulatedTelemetryProvider,
    SimulatedVerificationRunner,
)
from app.providers.simulated_investigation import (
    FixtureChangeCorrelationSpecialist,
    FixtureCodeMappingSpecialist,
    FixtureInvestigationGateway,
    FixtureRunbookSpecialist,
    FixtureTelemetrySpecialist,
)
from app.providers.simulated_remediation import FixtureRemediationPlanner
from app.sandbox.executor import SandboxPatchExecutor
from app.security.redaction import redact
from app.store.memory import InMemoryStore
from app.workflow.investigation_manager import InvestigationManager
from app.workflow.pipeline import WorkflowPipeline
from app.workflow.remediation_planner import RemediationPlanningManager

NOW = datetime(2026, 7, 13, 11, 0, tzinfo=UTC)


def _incident() -> Incident:
    return Incident(
        id="inc-test-0001",
        title="Checkout API elevated 500 errors",
        service="checkout-api",
        environment=Environment.PRODUCTION,
        severity=Severity.SEV2,
        summary="HTTP 500 rate exceeded 12% after deployment.",
        state=WorkflowState.INVESTIGATING,
        provider_mode=ProviderMode.SIMULATED,
        created_at=NOW,
        updated_at=NOW,
    )


def _golden_evidence(incident: Incident) -> list[EvidenceItem]:
    """Rebuild the persisted, redacted evidence the pipeline would produce,
    with deterministic ev-NNNN IDs, so the manager can be tested in isolation."""
    sources: list[EvidenceSource] = [
        SimulatedTelemetryProvider(),
        SimulatedDeploymentHistoryProvider(),
        SimulatedLocalRepositoryProvider(),
        SimulatedRunbookProvider(),
    ]
    raws: list[RawEvidence] = []
    for source in sources:
        raws.extend(source.fetch_evidence(incident))
    raws.sort(key=lambda r: (r.observed_at, r.provider, r.display_ref))

    items: list[EvidenceItem] = []
    for i, raw in enumerate(raws, start=1):
        redacted = redact(raw.content)
        items.append(
            EvidenceItem(
                id=f"ev-{i:04d}",
                incident_id=incident.id,
                kind=raw.kind,
                provider=raw.provider,
                source=raw.source,
                summary=raw.summary,
                content=redacted.content,
                content_hash="sha256:test",
                display_ref=raw.display_ref,
                redaction_applied=redacted.applied,
                redaction_rules=redacted.matched_rules,
                provenance=raw.provenance,
                captured_at=raw.observed_at,
                created_at=NOW,
            )
        )
    return items


def _fixture_manager(model_id: str = "simulated-fixture") -> InvestigationManager:
    return InvestigationManager(
        specialists=(
            FixtureTelemetrySpecialist(),
            FixtureChangeCorrelationSpecialist(),
            FixtureCodeMappingSpecialist(),
            FixtureRunbookSpecialist(),
        ),
        gateway=FixtureInvestigationGateway(model_id=model_id),
    )


# --- Schema strictness -------------------------------------------------------


def _falsification() -> FalsificationTest:
    return FalsificationTest(
        description="d", steps=["s"], expected_if_true="t", expected_if_false="f"
    )


def test_ranked_hypothesis_requires_contradicting_and_unknowns() -> None:
    # Missing contradicting evidence is rejected.
    with pytest.raises(ValidationError):
        RankedHypothesis(
            rank=1,
            statement="something broke",
            confidence=0.5,
            supporting=[EvidenceCitation(evidence_id="ev-1", note="x")],
            contradicting=[],
            unknowns=["u"],
            falsification_tests=[_falsification()],
            rationale="r",
        )
    # Missing unknowns is rejected.
    with pytest.raises(ValidationError):
        RankedHypothesis(
            rank=1,
            statement="something broke",
            confidence=0.5,
            supporting=[EvidenceCitation(evidence_id="ev-1", note="x")],
            contradicting=[EvidenceCitation(evidence_id="ev-2", note="y")],
            unknowns=[],
            falsification_tests=[_falsification()],
            rationale="r",
        )


def test_strict_models_forbid_extra_fields_like_chain_of_thought() -> None:
    with pytest.raises(ValidationError):
        EvidenceCitation(evidence_id="ev-1", note="x", chain_of_thought="secret")  # type: ignore[call-arg]


def test_complete_draft_requires_three_hypotheses() -> None:
    summary = IncidentSummary(
        what_happened="x", impact="y", citations=[EvidenceCitation(evidence_id="ev-1", note="n")]
    )
    with pytest.raises(ValidationError):
        InvestigationDraft(status=InvestigationStatus.COMPLETE, summary=summary, hypotheses=[])


def test_report_cannot_enable_remediation_without_complete() -> None:
    with pytest.raises(ValidationError):
        InvestigationReport(
            id="inv-1",
            incident_id="inc-1",
            status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
            gateway="g",
            remediation_enabled=True,
            summary=None,
            findings=[],
            hypotheses=[],
            code_mapping=None,
            unknowns=[],
            rejected_claims=[],
            created_at=NOW,
        )


# --- Golden determinism ------------------------------------------------------


def test_golden_investigation_is_complete_and_deterministic() -> None:
    incident = _incident()
    evidence = _golden_evidence(incident)
    manager = _fixture_manager()

    first = manager.investigate(incident, evidence, "inv-0001", NOW)
    second = manager.investigate(incident, evidence, "inv-0001", NOW)

    assert first.model_dump() == second.model_dump()
    assert first.status is InvestigationStatus.COMPLETE
    assert first.remediation_enabled is True
    assert len(first.hypotheses) == 3
    assert first.rejected_claims == []
    # Non-increasing confidence with rank; contiguous ranks.
    assert [h.rank for h in first.hypotheses] == [1, 2, 3]
    confidences = [h.confidence for h in first.hypotheses]
    assert confidences == sorted(confidences, reverse=True)


def test_top_hypothesis_is_unsafe_discount_access_from_c7f2e9a() -> None:
    incident = _incident()
    evidence = _golden_evidence(incident)
    report = _fixture_manager().investigate(incident, evidence, "inv-0001", NOW)

    top = report.hypotheses[0]
    assert "session.discount.code" in top.statement
    assert "c7f2e9a" in top.statement
    assert top.suspect_commit == "c7f2e9a"
    # Every supporting/contradicting citation resolves to persisted evidence.
    valid_ids = {e.id for e in evidence}
    for citation in [*top.supporting, *top.contradicting]:
        assert citation.evidence_id in valid_ids
    # Contradicting evidence and at least one unknown are mandatory.
    assert top.contradicting
    assert top.unknowns
    assert top.falsification_tests


def test_code_mapping_identifies_files_commit_and_coverage_gap() -> None:
    incident = _incident()
    evidence = _golden_evidence(incident)
    report = _fixture_manager().investigate(incident, evidence, "inv-0001", NOW)

    assert report.code_mapping is not None
    mapping = report.code_mapping
    paths = {f.path for f in mapping.affected_files}
    assert paths == {"src/checkout.ts", "src/checkout.test.ts"}
    assert mapping.suspect_commit == "c7f2e9a"
    assert "discount" in mapping.coverage_gap
    valid_ids = {e.id for e in evidence}
    cites = [*mapping.commit_citations, *mapping.coverage_gap_citations]
    for affected in mapping.affected_files:
        cites.extend(affected.citations)
    assert all(c.evidence_id in valid_ids for c in cites)


# --- Citation validation and rejection --------------------------------------


class _BogusSpecialist:
    """Emits one finding citing evidence that was never persisted."""

    kind = SpecialistKind.TELEMETRY

    def analyze(
        self, incident: Incident, evidence: list[EvidenceItem]
    ) -> list[SpecialistFinding]:
        return [
            SpecialistFinding(
                specialist=self.kind,
                statement="fabricated claim with no grounding",
                citations=[EvidenceCitation(evidence_id="ev-ghost", note="does not exist")],
            )
        ]


def test_unsupported_specialist_claim_is_rejected_but_report_completes() -> None:
    incident = _incident()
    evidence = _golden_evidence(incident)
    manager = InvestigationManager(
        specialists=(
            FixtureTelemetrySpecialist(),
            FixtureChangeCorrelationSpecialist(),
            FixtureCodeMappingSpecialist(),
            FixtureRunbookSpecialist(),
            _BogusSpecialist(),
        ),
        gateway=FixtureInvestigationGateway(),
    )
    report = manager.investigate(incident, evidence, "inv-0001", NOW)

    assert report.status is InvestigationStatus.COMPLETE
    assert any(rc.origin.startswith("specialist:") for rc in report.rejected_claims)
    assert any("ev-ghost" in rc.reason for rc in report.rejected_claims)
    # The fabricated claim never reaches the surviving findings.
    assert all("fabricated" not in f.statement for f in report.findings)


class _TamperGateway:
    """Wraps the fixture gateway and injects an ungrounded citation into the
    top hypothesis, simulating a model that fabricates evidence IDs."""

    model_id = "tamper"

    def __init__(self) -> None:
        self._inner = FixtureInvestigationGateway()

    def synthesize(
        self,
        incident: Incident,
        evidence: list[EvidenceItem],
        findings: list[SpecialistFinding],
    ) -> InvestigationDraft:
        draft = self._inner.synthesize(incident, evidence, findings)
        top = draft.hypotheses[0].model_copy(
            update={"supporting": [EvidenceCitation(evidence_id="ev-ghost", note="fabricated")]}
        )
        return draft.model_copy(update={"hypotheses": [top, *draft.hypotheses[1:]]})


def test_ungrounded_hypothesis_rejected_and_downgrades_to_insufficient() -> None:
    incident = _incident()
    evidence = _golden_evidence(incident)
    manager = InvestigationManager(
        specialists=(FixtureTelemetrySpecialist(),),
        gateway=_TamperGateway(),
    )
    report = manager.investigate(incident, evidence, "inv-0001", NOW)

    # Dropping the fabricated hypothesis leaves fewer than three, so the
    # investigation is downgraded and remediation is disabled.
    assert report.status is InvestigationStatus.INSUFFICIENT_EVIDENCE
    assert report.remediation_enabled is False
    assert any(rc.origin.startswith("hypothesis:") for rc in report.rejected_claims)


def test_missing_evidence_yields_insufficient_and_disables_remediation() -> None:
    incident = _incident()
    # Drop the commit diff, one of the required golden anchors.
    evidence = [e for e in _golden_evidence(incident) if not e.display_ref.endswith("c7f2e9a.diff")]
    report = _fixture_manager().investigate(incident, evidence, "inv-0001", NOW)

    assert report.status is InvestigationStatus.INSUFFICIENT_EVIDENCE
    assert report.remediation_enabled is False
    assert report.hypotheses == []
    assert report.unknowns


# --- Pipeline safe path ------------------------------------------------------


class _InsufficientGateway:
    model_id = "insufficient"

    def synthesize(
        self,
        incident: Incident,
        evidence: list[EvidenceItem],
        findings: list[SpecialistFinding],
    ) -> InvestigationDraft:
        return InvestigationDraft(
            status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
            findings=list(findings),
            unknowns=["insufficient evidence for a grounded hypothesis"],
        )


def test_pipeline_insufficient_evidence_stops_before_remediation() -> None:
    store = InMemoryStore()
    incident = _incident().model_copy(update={"state": WorkflowState.RECEIVED})
    store.add_incident(incident)
    store.append_workflow_event(incident.id, None, WorkflowState.RECEIVED, "test.seed")

    manager = InvestigationManager(
        specialists=(FixtureTelemetrySpecialist(),),
        gateway=_InsufficientGateway(),
    )
    pipeline = WorkflowPipeline(
        store=store,
        telemetry=SimulatedTelemetryProvider(),
        deployments=SimulatedDeploymentHistoryProvider(),
        repository=SimulatedLocalRepositoryProvider(),
        runbook=SimulatedRunbookProvider(),
        investigation=SimulatedInvestigationProvider(),
        investigation_manager=manager,
        remediation_planner=RemediationPlanningManager(planner=FixtureRemediationPlanner()),
        patch_executor=SandboxPatchExecutor(store=store, gateway=FixtureCodexGateway()),
        verifier=SimulatedVerificationRunner(),
        provider_mode=ProviderMode.SIMULATED,
    )

    result = pipeline.start(incident)

    assert result.state is WorkflowState.NEEDS_INPUT
    # No remediation artifacts were created behind the approval gate.
    assert store.list_plans(incident.id) == []
    assert store.list_approvals(incident.id) == []
    report = store.get_investigation_report(incident.id)
    assert report is not None
    assert report.status is InvestigationStatus.INSUFFICIENT_EVIDENCE
    assert report.remediation_enabled is False


def test_pipeline_golden_persists_report_available_via_route() -> None:
    settings = Settings(demo_mode=True, database_url="sqlite:///:memory:")
    app = create_app(settings)
    with TestClient(app) as client:
        client.post("/api/v1/incidents/inc-demo-0001/start")
        res = client.get("/api/v1/incidents/inc-demo-0001/investigation")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "complete"
        assert body["remediation_enabled"] is True
        assert len(body["hypotheses"]) == 3
        assert body["gateway"] == "simulated-fixture"
        assert "session.discount.code" in body["hypotheses"][0]["statement"]
        assert body["code_mapping"]["suspect_commit"] == "c7f2e9a"
