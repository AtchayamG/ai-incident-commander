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
    WorkflowState,
)
from app.domain.investigation import (
    InvestigationReport,
    InvestigationStatus,
    RankedHypothesis,
)
from app.domain.remediation import (
    ApprovalBinding,
    PlanningOutcome,
    RemediationPlanArtifact,
)
from app.domain.sandbox import PatchExecutionArtifact, PatchExecutionStatus
from app.domain.verification import VerificationFailureKind, VerificationRunArtifact
from app.providers.base import (
    DeploymentHistoryProvider,
    EvidenceSource,
    InvestigationProvider,
    LocalRepositoryProvider,
    RawEvidence,
    RunbookProvider,
    TelemetryProvider,
)
from app.sandbox.executor import (
    ApprovalRequiredError,
    SandboxPatchExecutor,
    SandboxSetupError,
)
from app.sandbox.verifier import VerificationSetupError, Verifier
from app.sandbox.workspace import WorkspaceIntegrityError
from app.security.redaction import redact
from app.store.protocol import StoreProtocol
from app.workflow.investigation_manager import InvestigationManager
from app.workflow.remediation_planner import RemediationPlanningManager

__all__ = ["ApprovalRequiredError", "ChangeBudgetExceededError", "WorkflowPipeline"]

APPROVAL_TTL = timedelta(hours=4)

# The role an APPLY_PATCH approval is bound to. Demo mode has a single human
# operator acting in this role; a decision supplying a different role via
# X-Approver-Role is refused.
PATCH_APPROVER_ROLE = "incident_commander"


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
        remediation_planner: RemediationPlanningManager,
        patch_executor: SandboxPatchExecutor,
        verifier: Verifier,
        provider_mode: ProviderMode,
    ) -> None:
        self._store = store
        self._evidence_sources: tuple[EvidenceSource, ...] = (
            telemetry,
            deployments,
            repository,
            runbook,
        )
        # Legacy M0 proposal provider; the M4 planning manager owns plans now.
        self._investigation = investigation
        self._investigation_manager = investigation_manager
        self._remediation_planner = remediation_planner
        self._patch_executor = patch_executor
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
        artifact = self._plan_bounded(incident, report)
        if artifact is None:
            # Explicit refusal: the draft violated policy (prohibited path,
            # budget breach, disallowed command, high risk, ...). Terminal
            # NO_SAFE_REMEDIATION; no plan row, no approval, nothing to apply.
            return self._transition(
                incident, WorkflowState.NO_SAFE_REMEDIATION, "planning.refused"
            )
        incident = self._transition(incident, WorkflowState.PLAN_READY, "plan.ready")

        self._request_patch_approval(incident, artifact)
        return self._transition(
            incident, WorkflowState.WAITING_PATCH_APPROVAL, "approval.requested"
        )

    def apply_patch_approval(self, incident: Incident, approved: bool) -> Incident:
        """Resolve the APPLY_PATCH approval gate.

        Approved: PATCHING (bounded isolated-workspace execution) ->
        VERIFYING (deterministic checks against the captured candidate diff)
        -> REVIEW_READY only when every required check passes and the risk
        policy allows a real PR. A relevant patch-caused check failure may
        re-enter PATCHING for a bounded repair attempt (blueprint 19.4);
        everything else lands in PATCH_FAILED with structured evidence.
        Rejected: CANCELLED.
        """
        if not approved:
            return self._transition(incident, WorkflowState.CANCELLED, "approval.rejected")

        # Authorization is checked before any transition or workspace exists;
        # the executor re-checks and consumes the single-use approval itself.
        self._assert_patch_authorized(incident)
        incident = self._transition(incident, WorkflowState.PATCHING, "approval.approved")
        try:
            execution = self._patch_executor.execute(incident)
        except (SandboxSetupError, WorkspaceIntegrityError) as exc:
            self._audit_failure(incident, f"Sandbox unavailable; failing closed: {exc}")
            return self._transition(
                incident, WorkflowState.PATCH_FAILED, "patch.sandbox_unavailable"
            )
        if execution.status is not PatchExecutionStatus.SUCCEEDED:
            return self._transition(
                incident, WorkflowState.PATCH_FAILED, "patch.execution_failed"
            )

        while True:
            patch = self._record_patch_attempt(incident, execution)
            incident = self._transition(incident, WorkflowState.VERIFYING, "patch.proposed")
            try:
                verification = self._verifier.verify(
                    incident, execution, patch.id, patch.attempt
                )
            except (VerificationSetupError, SandboxSetupError, WorkspaceIntegrityError) as exc:
                self._audit_failure(
                    incident, f"Verification unavailable; failing closed: {exc}"
                )
                return self._transition(
                    incident, WorkflowState.PATCH_FAILED, "verification.unavailable"
                )
            self._record_verification_run(incident, patch, verification)

            if verification.passed:
                if verification.risk.blocks_pr:
                    # Deterministic risk policy: HIGH-risk changes never
                    # become PR-ready by default (blueprint 21.3).
                    return self._transition(
                        incident, WorkflowState.PATCH_FAILED, "risk.blocked"
                    )
                return self._transition(
                    incident, WorkflowState.REVIEW_READY, "verification.passed"
                )

            repairable = (
                verification.failure_kind is VerificationFailureKind.PATCH_ISSUE
                and self._patch_executor.repair_budget_remaining(incident, execution) > 0
            )
            if not repairable:
                return self._transition(
                    incident, WorkflowState.PATCH_FAILED, "verification.failed"
                )

            incident = self._transition(
                incident, WorkflowState.PATCHING, "verification.repair"
            )
            try:
                execution = self._patch_executor.repair(
                    incident, execution, "; ".join(verification.failure_evidence)
                )
            except (ApprovalRequiredError, SandboxSetupError, WorkspaceIntegrityError) as exc:
                self._audit_failure(incident, f"Repair refused; failing closed: {exc}")
                return self._transition(
                    incident, WorkflowState.PATCH_FAILED, "patch.repair_refused"
                )
            if execution.status is not PatchExecutionStatus.SUCCEEDED:
                return self._transition(
                    incident, WorkflowState.PATCH_FAILED, "patch.execution_failed"
                )

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

    def _plan_bounded(
        self, incident: Incident, report: InvestigationReport
    ) -> RemediationPlanArtifact | None:
        """Run the M4 planning manager. On PLANNED, persist the bounded
        artifact plus the legacy RemediationPlan row (unchanged API shape) and
        return the artifact. On refusal, record the reasons on the timeline
        for audit and return None — no plan or approval is created."""
        previous = self._store.get_latest_plan_artifact(incident.id)
        decision = self._remediation_planner.plan(
            incident,
            report,
            plan_id=self._store.next_id("rplan"),
            now=datetime.now(UTC),
            version=(previous.version + 1) if previous else 1,
        )
        if decision.outcome is not PlanningOutcome.PLANNED or decision.plan is None:
            self._store.add_timeline_event(
                TimelineEvent(
                    id=self._store.next_id("tl"),
                    incident_id=incident.id,
                    at=datetime.now(UTC),
                    kind="planning_refusal",
                    description=(
                        f"Remediation planning refused ({decision.outcome}): "
                        + "; ".join(decision.reasons)
                    )[:1000],
                )
            )
            return None

        artifact = self._store.add_plan_artifact(decision.plan)
        self._store.add_plan(
            RemediationPlan(
                id=self._store.next_id("plan"),
                incident_id=incident.id,
                hypothesis_id=artifact.hypothesis_id,
                summary=artifact.summary,
                steps=list(artifact.steps),
                risk_level=artifact.risk_level,
                max_files_changed=artifact.max_files_changed,
                max_lines_changed=artifact.max_lines_changed,
            )
        )
        return artifact

    def _request_patch_approval(
        self, incident: Incident, artifact: RemediationPlanArtifact
    ) -> ApprovalRequest:
        """Create the pending APPLY_PATCH approval bound to one exact plan
        artifact (id, version, content hash) with an expiry and approver role.
        Only called after a valid bounded plan exists."""
        now = datetime.now(UTC)
        approval = self._store.add_approval(
            ApprovalRequest(
                id=self._store.next_id("apr"),
                incident_id=incident.id,
                approval_type=ApprovalType.APPLY_PATCH,
                risk_level=artifact.risk_level,
                status=ApprovalStatus.PENDING,
                reason=artifact.summary,
                artifact_version=artifact.version,
                requested_at=now,
                expires_at=now + APPROVAL_TTL,
            )
        )
        self._store.add_approval_binding(
            ApprovalBinding(
                approval_id=approval.id,
                incident_id=incident.id,
                plan_id=artifact.id,
                plan_version=artifact.version,
                plan_hash=artifact.artifact_hash,
                action=ApprovalType.APPLY_PATCH,
                risk_level=artifact.risk_level,
                approver_role=PATCH_APPROVER_ROLE,
                expires_at=approval.expires_at,
                created_at=now,
            )
        )
        return approval

    def _assert_patch_authorized(self, incident: Incident) -> None:
        """Defense in depth for the M4 gate: no patch artifact is created (and
        in M5, no workspace is mutated) unless an APPROVED APPLY_PATCH approval
        exists whose binding still matches the incident's latest plan artifact."""
        artifact = self._store.get_latest_plan_artifact(incident.id)
        if artifact is None:
            raise ApprovalRequiredError("no bounded remediation plan exists for this incident")
        for approval in self._store.list_approvals(incident.id):
            if (
                approval.approval_type is not ApprovalType.APPLY_PATCH
                or approval.status is not ApprovalStatus.APPROVED
            ):
                continue
            binding = self._store.get_approval_binding(approval.id)
            if (
                binding is not None
                and binding.plan_id == artifact.id
                and binding.plan_version == artifact.version
                and binding.plan_hash == artifact.artifact_hash
            ):
                return
        raise ApprovalRequiredError(
            "no approved APPLY_PATCH approval is bound to the current plan artifact"
        )

    def _record_patch_attempt(
        self, incident: Incident, execution: PatchExecutionArtifact
    ) -> PatchAttempt:
        plans = self._store.list_plans(incident.id)
        return self._store.add_patch(
            PatchAttempt(
                id=self._store.next_id("patch"),
                incident_id=incident.id,
                plan_id=plans[-1].id,
                attempt=len(self._store.list_patches(incident.id)) + 1,
                diff=execution.unified_diff,
                files_changed=len(execution.changed_files),
                lines_changed=execution.total_additions + execution.total_deletions,
                provider_mode=self._provider_mode,
            )
        )

    def _record_verification_run(
        self, incident: Incident, patch: PatchAttempt, artifact: VerificationRunArtifact
    ) -> VerificationRun:
        """Project the rich M6 artifact onto the public VerificationRun shape
        (unchanged contract): one check per executed command plus the
        regression-test requirement and the deterministic risk decision."""
        checks = [
            VerificationCheck(
                name=f"{result.category}{' (base-state)' if result.baseline else ''}",
                passed=result.passed,
                detail=(
                    f"{result.command}: "
                    + (
                        "timed out"
                        if result.timed_out
                        else f"spawn failed: {result.spawn_error}"
                        if result.spawn_error
                        else f"exit {result.exit_code}"
                    )
                ),
            )
            for result in artifact.commands
        ]
        checks.append(
            VerificationCheck(
                name="regression_test",
                passed=artifact.relevant_regression_test,
                detail="candidate diff adds a regression test and a test check ran"
                if artifact.relevant_regression_test
                else "no relevant regression test in the candidate diff",
            )
        )
        checks.append(
            VerificationCheck(
                name="risk_review",
                passed=not artifact.risk.blocks_pr,
                detail=(
                    f"deterministic risk {artifact.risk.risk_level} over "
                    f"{artifact.risk.files_changed} file(s); "
                    + ("blocks PR readiness" if artifact.risk.blocks_pr else "allows PR")
                ),
            )
        )
        run = VerificationRun(
            id=self._store.next_id("ver"),
            patch_id=patch.id,
            passed=artifact.passed and not artifact.risk.blocks_pr,
            checks=checks,
        )
        return self._store.add_verification(incident.id, run)

    def _audit_failure(self, incident: Incident, description: str) -> None:
        self._store.add_timeline_event(
            TimelineEvent(
                id=self._store.next_id("tl"),
                incident_id=incident.id,
                at=datetime.now(UTC),
                kind="sandbox_lifecycle",
                description=description[:1000],
            )
        )


class ChangeBudgetExceededError(Exception):
    """Legacy M0 budget error; M5 budget violations are enforced inside the
    sandbox workspace and recorded on the execution artifact instead."""
