"""Deterministic workflow pipeline for the M0 golden-path slice.

The pipeline advances an incident through the state machine using typed
provider proposals. Providers never change state; this module validates every
transition through ``state_machine.advance`` and records an append-only
workflow event for each change. M1+ moves execution to a durable worker; the
state and event contracts stay the same.
"""

import hashlib
from datetime import UTC, datetime, timedelta

from app.domain.contracts import (
    ApprovalRequest,
    EvidenceItem,
    Hypothesis,
    Incident,
    PatchAttempt,
    RemediationPlan,
    TimelineEvent,
    VerificationCheck,
    VerificationRun,
)
from app.domain.enums import (
    ApprovalStatus,
    ApprovalType,
    ProviderMode,
    RiskLevel,
    WorkflowState,
)
from app.domain.investigation import (
    InvestigationReport,
    InvestigationStatus,
    RankedHypothesis,
)
from app.providers.base import (
    CodeAgentGateway,
    DeploymentHistoryProvider,
    EvidenceSource,
    InvestigationProvider,
    LocalRepositoryProvider,
    RawEvidence,
    RunbookProvider,
    TelemetryProvider,
    VerificationRunner,
)
from app.security.redaction import redact
from app.store.protocol import StoreProtocol
from app.workflow.investigation_manager import InvestigationManager

APPROVAL_TTL = timedelta(hours=4)


class WorkflowPipeline:
    def __init__(
        self,
        store: StoreProtocol,
        telemetry: TelemetryProvider,
        deployments: DeploymentHistoryProvider,
        repository: LocalRepositoryProvider,
        runbook: RunbookProvider,
        investigation: InvestigationProvider,
        investigation_manager: InvestigationManager,
        code_agent: CodeAgentGateway,
        verifier: VerificationRunner,
        provider_mode: ProviderMode,
    ) -> None:
        self._store = store
        self._evidence_sources: tuple[EvidenceSource, ...] = (
            telemetry,
            deployments,
            repository,
            runbook,
        )
        self._investigation = investigation
        self._investigation_manager = investigation_manager
        self._code_agent = code_agent
        self._verifier = verifier
        self._provider_mode = provider_mode

    def _transition(self, incident: Incident, target: WorkflowState, trigger: str) -> Incident:
        from app.workflow import state_machine

        new_state = state_machine.advance(incident.state, target)
        updated = self._store.set_incident_state(incident.id, new_state)
        self._store.append_workflow_event(incident.id, incident.state, new_state, trigger)
        return updated

    def start(self, incident: Incident) -> Incident:
        """RECEIVED -> ... -> WAITING_PATCH_APPROVAL, gathering evidence and
        producing a hypothesis, plan, and approval request along the way."""
        incident = self._transition(incident, WorkflowState.NORMALIZING, "workflow.start")
        incident = self._transition(
            incident, WorkflowState.COLLECTING_EVIDENCE, "normalization.complete"
        )

        evidence_items = self._collect_evidence(incident)
        incident = self._transition(incident, WorkflowState.EVIDENCE_READY, "evidence.collected")

        incident = self._transition(incident, WorkflowState.INVESTIGATING, "investigation.start")
        top_hypothesis, report = self._investigate(incident, evidence_items)
        if report.status is not InvestigationStatus.COMPLETE or top_hypothesis is None:
            # Safe insufficient-evidence path: the investigation is not
            # grounded well enough to remediate. Stop at NEEDS_INPUT; no plan,
            # patch, or approval is created, so no remediation can proceed
            # until more evidence arrives.
            return self._transition(
                incident, WorkflowState.NEEDS_INPUT, "investigation.insufficient_evidence"
            )
        incident = self._transition(incident, WorkflowState.HYPOTHESES_READY, "hypotheses.ready")

        incident = self._transition(
            incident, WorkflowState.PLANNING_REMEDIATION, "planning.start"
        )
        plan = self._plan(incident, top_hypothesis)
        incident = self._transition(incident, WorkflowState.PLAN_READY, "plan.ready")

        self._request_patch_approval(incident, plan)
        return self._transition(
            incident, WorkflowState.WAITING_PATCH_APPROVAL, "approval.requested"
        )

    def apply_patch_approval(self, incident: Incident, approved: bool) -> Incident:
        """Resolve the APPLY_PATCH approval gate.

        Approved: PATCHING -> VERIFYING -> REVIEW_READY (simulated verification).
        Rejected: CANCELLED.
        """
        if not approved:
            return self._transition(incident, WorkflowState.CANCELLED, "approval.rejected")

        incident = self._transition(incident, WorkflowState.PATCHING, "approval.approved")
        patch = self._create_patch(incident)
        incident = self._transition(incident, WorkflowState.VERIFYING, "patch.proposed")
        verification = self._verify(incident, patch)
        if verification.passed:
            return self._transition(incident, WorkflowState.REVIEW_READY, "verification.passed")
        return self._transition(incident, WorkflowState.PATCH_FAILED, "verification.failed")

    # Internal stages -------------------------------------------------------

    def _collect_evidence(self, incident: Incident) -> list[EvidenceItem]:
        """Gather evidence from every source, redact, hash, persist, and build
        the chronological timeline.

        Raw items are sorted by (observed_at, provider, display_ref) before any
        ID is allocated, so IDs, persisted rows, and timeline order are stable
        across runs regardless of provider iteration order.
        """
        raw_items: list[RawEvidence] = []
        for source in self._evidence_sources:
            raw_items.extend(source.fetch_evidence(incident))
        raw_items.sort(key=lambda r: (r.observed_at, r.provider, r.display_ref))

        items: list[EvidenceItem] = []
        for raw in raw_items:
            redacted = redact(raw.content)
            digest = hashlib.sha256(redacted.content.encode("utf-8")).hexdigest()
            item = EvidenceItem(
                id=self._store.next_id("ev"),
                incident_id=incident.id,
                kind=raw.kind,
                provider=raw.provider,
                source=raw.source,
                summary=raw.summary,
                content=redacted.content,
                content_hash=f"sha256:{digest}",
                display_ref=raw.display_ref,
                redaction_applied=redacted.applied,
                redaction_rules=redacted.matched_rules,
                provenance=raw.provenance,
                captured_at=raw.observed_at,
                created_at=datetime.now(UTC),
            )
            self._store.add_evidence(item)
            items.append(item)

        for item in items:
            self._store.add_timeline_event(
                TimelineEvent(
                    id=self._store.next_id("tl"),
                    incident_id=incident.id,
                    at=item.captured_at,
                    kind=str(item.kind),
                    description=item.summary,
                    evidence_id=item.id,
                )
            )
        return items

    def _investigate(
        self, incident: Incident, evidence: list[EvidenceItem]
    ) -> tuple[Hypothesis | None, InvestigationReport]:
        """Run the investigation manager, persist the typed report and one
        Hypothesis row per ranked hypothesis, and return the top hypothesis
        (None when the investigation is not COMPLETE) plus the report.

        The manager owns citation validation and the remediation gate; this
        stage only persists its deterministic output.
        """
        report_id = self._store.next_id("inv")
        report = self._investigation_manager.investigate(
            incident, evidence, report_id, datetime.now(UTC)
        )

        persisted: list[Hypothesis] = []
        linked: list[RankedHypothesis] = []
        for ranked in report.hypotheses:
            hypothesis = Hypothesis(
                id=self._store.next_id("hyp"),
                incident_id=incident.id,
                statement=ranked.statement,
                confidence=ranked.confidence,
                supporting_evidence_ids=[c.evidence_id for c in ranked.supporting],
                contradictions=[c.note for c in ranked.contradicting],
                unknowns=list(ranked.unknowns),
            )
            self._store.add_hypothesis(hypothesis)
            persisted.append(hypothesis)
            linked.append(ranked.model_copy(update={"hypothesis_id": hypothesis.id}))

        report = report.model_copy(update={"hypotheses": linked})
        self._store.add_investigation_report(report)

        top = persisted[0] if persisted else None
        return top, report

    def _plan(self, incident: Incident, hypothesis: Hypothesis) -> RemediationPlan:
        proposal = self._investigation.propose_plan(incident, hypothesis.statement)
        plan = RemediationPlan(
            id=self._store.next_id("plan"),
            incident_id=incident.id,
            hypothesis_id=hypothesis.id,
            summary=proposal.summary,
            steps=proposal.steps,
            risk_level=RiskLevel.MEDIUM,
            max_files_changed=proposal.max_files_changed,
            max_lines_changed=proposal.max_lines_changed,
        )
        return self._store.add_plan(plan)

    def _request_patch_approval(
        self, incident: Incident, plan: RemediationPlan
    ) -> ApprovalRequest:
        now = datetime.now(UTC)
        approval = ApprovalRequest(
            id=self._store.next_id("apr"),
            incident_id=incident.id,
            approval_type=ApprovalType.APPLY_PATCH,
            risk_level=plan.risk_level,
            status=ApprovalStatus.PENDING,
            reason=plan.summary,
            artifact_version=1,
            requested_at=now,
            expires_at=now + APPROVAL_TTL,
        )
        return self._store.add_approval(approval)

    def _create_patch(self, incident: Incident) -> PatchAttempt:
        plans = self._store.list_plans(incident.id)
        plan = plans[-1]
        proposal = self._code_agent.propose_patch(incident, plan)
        if (
            proposal.files_changed > plan.max_files_changed
            or proposal.lines_changed > plan.max_lines_changed
        ):
            raise ChangeBudgetExceededError(
                f"patch touches {proposal.files_changed} files / {proposal.lines_changed} lines,"
                f" budget is {plan.max_files_changed} files / {plan.max_lines_changed} lines"
            )
        patch = PatchAttempt(
            id=self._store.next_id("patch"),
            incident_id=incident.id,
            plan_id=plan.id,
            attempt=len(self._store.list_patches(incident.id)) + 1,
            diff=proposal.diff,
            files_changed=proposal.files_changed,
            lines_changed=proposal.lines_changed,
            provider_mode=self._provider_mode,
        )
        return self._store.add_patch(patch)

    def _verify(self, incident: Incident, patch: PatchAttempt) -> VerificationRun:
        results = self._verifier.verify(incident, patch.diff)
        run = VerificationRun(
            id=self._store.next_id("ver"),
            patch_id=patch.id,
            passed=all(r.passed for r in results),
            checks=[
                VerificationCheck(name=r.name, passed=r.passed, detail=r.detail)
                for r in results
            ],
        )
        return self._store.add_verification(incident.id, run)


class ChangeBudgetExceededError(Exception):
    pass
