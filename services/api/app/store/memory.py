"""In-memory incident store for M0.

Deliberately mirrors the repository interface that the SQLAlchemy-backed
store will implement in M1, so route and workflow code does not change when
persistence arrives. Deterministic IDs keep the demo assertable.
"""

import threading
from datetime import UTC, datetime

from app.domain.contracts import (
    ApprovalRequest,
    EvidenceItem,
    Hypothesis,
    Incident,
    PatchAttempt,
    RemediationPlan,
    TimelineEvent,
    VerificationRun,
    WorkflowEvent,
)
from app.domain.enums import Environment, Severity, WorkflowState
from app.domain.investigation import InvestigationReport
from app.domain.remediation import ApprovalBinding, RemediationPlanArtifact
from app.domain.sandbox import PatchExecutionArtifact
from app.store.protocol import NotFoundError


class InMemoryStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._incidents: dict[str, Incident] = {}
        self._evidence: dict[str, list[EvidenceItem]] = {}
        self._timeline: dict[str, list[TimelineEvent]] = {}
        self._hypotheses: dict[str, list[Hypothesis]] = {}
        self._investigation_reports: dict[str, list[InvestigationReport]] = {}
        self._plans: dict[str, list[RemediationPlan]] = {}
        self._plan_artifacts: dict[str, list[RemediationPlanArtifact]] = {}
        self._patches: dict[str, list[PatchAttempt]] = {}
        self._patch_executions: dict[str, list[PatchExecutionArtifact]] = {}
        self._verifications: dict[str, list[VerificationRun]] = {}
        self._approvals: dict[str, ApprovalRequest] = {}
        self._approval_bindings: dict[str, ApprovalBinding] = {}
        self._workflow_events: dict[str, list[WorkflowEvent]] = {}
        self._counter = 0

    def reset(self) -> None:
        with self._lock:
            self._incidents.clear()
            self._evidence.clear()
            self._timeline.clear()
            self._hypotheses.clear()
            self._investigation_reports.clear()
            self._plans.clear()
            self._plan_artifacts.clear()
            self._patches.clear()
            self._patch_executions.clear()
            self._verifications.clear()
            self._approvals.clear()
            self._approval_bindings.clear()
            self._workflow_events.clear()
            self._counter = 0

    def next_id(self, prefix: str) -> str:
        with self._lock:
            self._counter += 1
            return f"{prefix}-{self._counter:04d}"

    # Incidents -----------------------------------------------------------

    def add_incident(self, incident: Incident) -> Incident:
        with self._lock:
            self._incidents[incident.id] = incident
            return incident

    def get_incident(self, incident_id: str) -> Incident:
        with self._lock:
            incident = self._incidents.get(incident_id)
            if incident is None:
                raise NotFoundError(f"incident {incident_id} not found")
            return incident

    def list_incidents(
        self,
        status: WorkflowState | None = None,
        severity: Severity | None = None,
        service: str | None = None,
        environment: Environment | None = None,
        limit: int = 50,
    ) -> list[Incident]:
        with self._lock:
            items = list(self._incidents.values())
        if status is not None:
            items = [i for i in items if i.state == status]
        if severity is not None:
            items = [i for i in items if i.severity == severity]
        if service is not None:
            items = [i for i in items if i.service == service]
        if environment is not None:
            items = [i for i in items if i.environment == environment]
        items.sort(key=lambda i: i.created_at, reverse=True)
        return items[:limit]

    def set_incident_state(self, incident_id: str, state: WorkflowState) -> Incident:
        with self._lock:
            incident = self.get_incident(incident_id)
            updated = incident.model_copy(
                update={"state": state, "updated_at": datetime.now(UTC)}
            )
            self._incidents[incident_id] = updated
            return updated

    # Workflow events -----------------------------------------------------

    def append_workflow_event(
        self,
        incident_id: str,
        from_state: WorkflowState | None,
        to_state: WorkflowState,
        trigger: str,
    ) -> WorkflowEvent:
        with self._lock:
            events = self._workflow_events.setdefault(incident_id, [])
            event = WorkflowEvent(
                id=self.next_id("evt"),
                incident_id=incident_id,
                sequence=len(events) + 1,
                from_state=from_state,
                to_state=to_state,
                trigger=trigger,
                at=datetime.now(UTC),
            )
            events.append(event)
            return event

    def list_workflow_events(self, incident_id: str) -> list[WorkflowEvent]:
        with self._lock:
            return list(self._workflow_events.get(incident_id, []))

    # Evidence and timeline ------------------------------------------------

    def add_evidence(self, item: EvidenceItem) -> EvidenceItem:
        with self._lock:
            self._evidence.setdefault(item.incident_id, []).append(item)
            return item

    def list_evidence(self, incident_id: str) -> list[EvidenceItem]:
        with self._lock:
            return sorted(
                self._evidence.get(incident_id, []), key=lambda e: (e.captured_at, e.id)
            )

    def add_timeline_event(self, event: TimelineEvent) -> TimelineEvent:
        with self._lock:
            self._timeline.setdefault(event.incident_id, []).append(event)
            return event

    def list_timeline(self, incident_id: str) -> list[TimelineEvent]:
        with self._lock:
            return sorted(self._timeline.get(incident_id, []), key=lambda e: (e.at, e.id))

    # Investigation artifacts ----------------------------------------------

    def add_hypothesis(self, hypothesis: Hypothesis) -> Hypothesis:
        with self._lock:
            self._hypotheses.setdefault(hypothesis.incident_id, []).append(hypothesis)
            return hypothesis

    def list_hypotheses(self, incident_id: str) -> list[Hypothesis]:
        with self._lock:
            return list(self._hypotheses.get(incident_id, []))

    def add_investigation_report(self, report: InvestigationReport) -> InvestigationReport:
        with self._lock:
            self._investigation_reports.setdefault(report.incident_id, []).append(report)
            return report

    def get_investigation_report(self, incident_id: str) -> InvestigationReport | None:
        with self._lock:
            reports = self._investigation_reports.get(incident_id, [])
            return reports[-1] if reports else None

    def add_plan(self, plan: RemediationPlan) -> RemediationPlan:
        with self._lock:
            self._plans.setdefault(plan.incident_id, []).append(plan)
            return plan

    def list_plans(self, incident_id: str) -> list[RemediationPlan]:
        with self._lock:
            return list(self._plans.get(incident_id, []))

    def add_plan_artifact(self, artifact: RemediationPlanArtifact) -> RemediationPlanArtifact:
        with self._lock:
            self._plan_artifacts.setdefault(artifact.incident_id, []).append(artifact)
            return artifact

    def get_latest_plan_artifact(self, incident_id: str) -> RemediationPlanArtifact | None:
        with self._lock:
            artifacts = self._plan_artifacts.get(incident_id, [])
            return artifacts[-1] if artifacts else None

    def list_plan_artifacts(self, incident_id: str) -> list[RemediationPlanArtifact]:
        with self._lock:
            return list(self._plan_artifacts.get(incident_id, []))

    def add_patch(self, patch: PatchAttempt) -> PatchAttempt:
        with self._lock:
            self._patches.setdefault(patch.incident_id, []).append(patch)
            return patch

    def list_patches(self, incident_id: str) -> list[PatchAttempt]:
        with self._lock:
            return list(self._patches.get(incident_id, []))

    def add_patch_execution(self, artifact: PatchExecutionArtifact) -> PatchExecutionArtifact:
        with self._lock:
            self._patch_executions.setdefault(artifact.incident_id, []).append(artifact)
            return artifact

    def list_patch_executions(self, incident_id: str) -> list[PatchExecutionArtifact]:
        with self._lock:
            return list(self._patch_executions.get(incident_id, []))

    def add_verification(self, incident_id: str, run: VerificationRun) -> VerificationRun:
        with self._lock:
            self._verifications.setdefault(incident_id, []).append(run)
            return run

    def list_verifications(self, incident_id: str) -> list[VerificationRun]:
        with self._lock:
            return list(self._verifications.get(incident_id, []))

    # Approvals -------------------------------------------------------------

    def add_approval(self, approval: ApprovalRequest) -> ApprovalRequest:
        with self._lock:
            self._approvals[approval.id] = approval
            return approval

    def get_approval(self, approval_id: str) -> ApprovalRequest:
        with self._lock:
            approval = self._approvals.get(approval_id)
            if approval is None:
                raise NotFoundError(f"approval {approval_id} not found")
            return approval

    def update_approval(self, approval: ApprovalRequest) -> ApprovalRequest:
        with self._lock:
            if approval.id not in self._approvals:
                raise NotFoundError(f"approval {approval.id} not found")
            self._approvals[approval.id] = approval
            return approval

    def list_approvals(self, incident_id: str) -> list[ApprovalRequest]:
        with self._lock:
            return [a for a in self._approvals.values() if a.incident_id == incident_id]

    def add_approval_binding(self, binding: ApprovalBinding) -> ApprovalBinding:
        with self._lock:
            self._approval_bindings[binding.approval_id] = binding
            return binding

    def get_approval_binding(self, approval_id: str) -> ApprovalBinding | None:
        with self._lock:
            return self._approval_bindings.get(approval_id)
