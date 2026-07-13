"""Typed API and workflow contracts (Pydantic v2).

These models are the single source of truth for the backend. The TypeScript
mirror lives in packages/contracts and must be kept in sync when these change.
Request models forbid unknown fields so contract drift fails loudly.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    ApprovalDecision,
    ApprovalStatus,
    ApprovalType,
    Environment,
    EvidenceKind,
    ProviderMode,
    RiskLevel,
    Severity,
    WorkflowState,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SignalIn(StrictModel):
    provider: str = Field(min_length=1, max_length=100)
    signal_type: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)


class IncidentCreate(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    service: str = Field(min_length=1, max_length=100)
    environment: Environment
    severity: Severity
    summary: str = Field(min_length=1, max_length=2000)
    signal: SignalIn | None = None


class Incident(StrictModel):
    id: str
    title: str
    service: str
    environment: Environment
    severity: Severity
    summary: str
    state: WorkflowState
    provider_mode: ProviderMode
    created_at: datetime
    updated_at: datetime


class EvidenceItem(StrictModel):
    id: str
    incident_id: str
    kind: EvidenceKind
    provider: str = Field(description="Identifier of the provider adapter that captured this")
    source: str
    summary: str
    content: str = Field(description="Redacted content; raw payloads never cross this boundary")
    content_hash: str = Field(description="sha256 of the redacted content, prefixed 'sha256:'")
    display_ref: str = Field(description="Stable human-facing reference to the evidence origin")
    redaction_applied: bool
    redaction_rules: list[str] = Field(
        default_factory=list, description="Names of redaction rules that matched"
    )
    provenance: dict[str, Any] = Field(default_factory=dict)
    captured_at: datetime = Field(description="When the underlying fact was observed")
    created_at: datetime


class TimelineEvent(StrictModel):
    id: str
    incident_id: str
    at: datetime
    kind: str
    description: str
    evidence_id: str | None = None


class Hypothesis(StrictModel):
    id: str
    incident_id: str
    statement: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class RemediationPlan(StrictModel):
    id: str
    incident_id: str
    hypothesis_id: str
    summary: str
    steps: list[str]
    risk_level: RiskLevel
    max_files_changed: int = Field(ge=1)
    max_lines_changed: int = Field(ge=1)


class PatchAttempt(StrictModel):
    id: str
    incident_id: str
    plan_id: str
    attempt: int = Field(ge=1)
    diff: str
    files_changed: int = Field(ge=0)
    lines_changed: int = Field(ge=0)
    provider_mode: ProviderMode


class VerificationCheck(StrictModel):
    name: str
    passed: bool
    detail: str


class VerificationRun(StrictModel):
    id: str
    patch_id: str
    passed: bool
    checks: list[VerificationCheck]


class ApprovalRequest(StrictModel):
    id: str
    incident_id: str
    approval_type: ApprovalType
    risk_level: RiskLevel
    status: ApprovalStatus
    reason: str
    artifact_version: int = Field(ge=1)
    requested_at: datetime
    expires_at: datetime
    decided_at: datetime | None = None
    decision_reason: str | None = None


class ApprovalDecisionIn(StrictModel):
    decision: ApprovalDecision
    reason: str = Field(min_length=1, max_length=2000)
    artifact_version: int | None = Field(
        default=None,
        description="If provided, must match the approval's artifact_version",
    )


class WorkflowEvent(StrictModel):
    id: str
    incident_id: str
    sequence: int = Field(ge=1)
    from_state: WorkflowState | None
    to_state: WorkflowState
    trigger: str
    at: datetime


class IncidentList(StrictModel):
    items: list[Incident]
    total: int


class HealthLive(StrictModel):
    status: str


class HealthReady(StrictModel):
    status: str
    demo_mode: bool
    provider_mode: ProviderMode


class DependencyStatus(StrictModel):
    name: str
    status: str


class HealthDependencies(StrictModel):
    status: str
    dependencies: list[DependencyStatus]


class ResetResult(StrictModel):
    status: str
    seeded_incident_ids: list[str]


class ActionItem(StrictModel):
    description: str
    priority: str
    owner: str = "TBD"


class Postmortem(StrictModel):
    id: str
    incident_id: str
    summary: str
    impact: str
    root_cause: str
    resolution: str
    timeline_json: list[dict[str, Any]]
    action_items_json: list[ActionItem]
    markdown_content: str
    markdown_uri: str | None = None
    created_at: datetime


class ExternalAction(StrictModel):
    id: str
    incident_id: str
    action_type: str
    provider: str
    idempotency_key: str
    approval_request_id: str
    status: str
    request_json: dict[str, Any]
    provider_receipt_json: dict[str, Any] | None = None
    created_at: datetime
    completed_at: datetime | None = None


class DraftPR(StrictModel):
    id: str
    incident_id: str
    status: str
    url: str | None = None
    reference: str | None = None
    provider_mode: ProviderMode
    idempotency_key: str
    error_message: str | None = None
    created_at: datetime


class CommunicationUpdate(StrictModel):
    incident_id: str
    technical_update: str
    stakeholder_update: str
    resolution_note: str
    created_at: datetime


