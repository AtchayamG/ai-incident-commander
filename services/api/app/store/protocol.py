"""Store protocol for persistence."""

from typing import Protocol

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


class NotFoundError(Exception):
    pass


class StoreProtocol(Protocol):
    def reset(self) -> None: ...

    def next_id(self, prefix: str) -> str: ...

    def add_incident(self, incident: Incident) -> Incident: ...

    def get_incident(self, incident_id: str) -> Incident: ...

    def list_incidents(
        self,
        status: WorkflowState | None = None,
        severity: Severity | None = None,
        service: str | None = None,
        environment: Environment | None = None,
        limit: int = 50,
    ) -> list[Incident]: ...

    def set_incident_state(self, incident_id: str, state: WorkflowState) -> Incident: ...

    def append_workflow_event(
        self,
        incident_id: str,
        from_state: WorkflowState | None,
        to_state: WorkflowState,
        trigger: str,
    ) -> WorkflowEvent: ...

    def list_workflow_events(self, incident_id: str) -> list[WorkflowEvent]: ...

    def add_evidence(self, item: EvidenceItem) -> EvidenceItem: ...

    def list_evidence(self, incident_id: str) -> list[EvidenceItem]: ...

    def add_timeline_event(self, event: TimelineEvent) -> TimelineEvent: ...

    def list_timeline(self, incident_id: str) -> list[TimelineEvent]: ...

    def add_hypothesis(self, hypothesis: Hypothesis) -> Hypothesis: ...

    def list_hypotheses(self, incident_id: str) -> list[Hypothesis]: ...

    def add_investigation_report(self, report: InvestigationReport) -> InvestigationReport: ...

    def get_investigation_report(self, incident_id: str) -> InvestigationReport | None: ...

    def add_plan(self, plan: RemediationPlan) -> RemediationPlan: ...

    def list_plans(self, incident_id: str) -> list[RemediationPlan]: ...

    def add_patch(self, patch: PatchAttempt) -> PatchAttempt: ...

    def list_patches(self, incident_id: str) -> list[PatchAttempt]: ...

    def add_verification(self, incident_id: str, run: VerificationRun) -> VerificationRun: ...

    def list_verifications(self, incident_id: str) -> list[VerificationRun]: ...

    def add_approval(self, approval: ApprovalRequest) -> ApprovalRequest: ...

    def get_approval(self, approval_id: str) -> ApprovalRequest: ...

    def update_approval(self, approval: ApprovalRequest) -> ApprovalRequest: ...

    def list_approvals(self, incident_id: str) -> list[ApprovalRequest]: ...
