"""Typed bounded remediation-plan outputs and approval bindings (M4).

A remediation plan is only ever produced from a COMPLETE investigation report
and is grounded in that report's code mapping: every file the plan names must
appear in the mapping's affected files. Plans are bounded by construction —
change budget, attempt budget, timeout, command allowlist, prohibited paths,
network off by default — and always declare a rollback. When the evidence or
the draft cannot satisfy those bounds the planning stage refuses with
``NO_SAFE_REMEDIATION`` (unsafe draft) or ``NEEDS_INPUT`` (insufficient
investigation) instead of emitting a weaker plan.

The approval binding pins a pending APPLY_PATCH approval to one exact plan
artifact (id, version, content hash) so a decision can never authorize a plan
other than the one the approver saw. Like the M3 investigation models, these
are backend-internal (served read-only over the API) and not yet mirrored in
packages/contracts. M5 owns actual workspace patching; nothing here mutates a
repository.
"""

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import ApprovalType, RiskLevel


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanningOutcome(StrEnum):
    PLANNED = "planned"
    NO_SAFE_REMEDIATION = "no_safe_remediation"
    NEEDS_INPUT = "needs_input"


class RemediationPlanDraft(StrictModel):
    """Planner-gateway output before policy validation.

    Deliberately has no citations of its own: grounding is checked structurally
    by the planning manager against the investigation report's code mapping,
    not by trusting planner-supplied references.
    """

    summary: str = Field(min_length=1, max_length=500)
    files_expected: list[str] = Field(min_length=1, max_length=10)
    steps: list[str] = Field(min_length=1, max_length=10)
    verification_commands: list[str] = Field(min_length=1, max_length=10)
    allowed_commands: list[str] = Field(min_length=1, max_length=20)
    max_files_changed: int = Field(ge=1)
    max_lines_changed: int = Field(ge=1)
    max_attempts: int = Field(ge=1)
    timeout_seconds: int = Field(ge=1)
    network_allowed: bool = False
    rollback: str = Field(min_length=1, max_length=500)
    rationale: str = Field(
        min_length=1,
        max_length=600,
        description="Concise justification; never chain-of-thought",
    )


class RemediationPlanArtifact(StrictModel):
    """Validated, persisted bounded remediation plan for one incident run.

    ``artifact_hash`` covers every other field, so any regeneration of the
    plan — even with identical content under a new id or version — is
    detectable, and an approval bound to an older artifact goes stale.
    """

    id: str
    incident_id: str
    investigation_report_id: str
    hypothesis_id: str
    version: int = Field(ge=1)
    summary: str = Field(min_length=1, max_length=500)
    files_expected: list[str] = Field(min_length=1, max_length=10)
    steps: list[str] = Field(min_length=1, max_length=10)
    verification_commands: list[str] = Field(min_length=1, max_length=10)
    allowed_commands: list[str] = Field(min_length=1, max_length=20)
    prohibited_paths: list[str] = Field(min_length=1)
    risk_level: RiskLevel
    max_files_changed: int = Field(ge=1)
    max_lines_changed: int = Field(ge=1)
    max_attempts: int = Field(ge=1)
    timeout_seconds: int = Field(ge=1)
    network_allowed: bool
    rollback: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=600)
    artifact_hash: str = Field(min_length=1, max_length=100)
    created_at: datetime

    @model_validator(mode="after")
    def _validate_bounds(self) -> "RemediationPlanArtifact":
        if self.network_allowed:
            raise ValueError("a bounded remediation plan cannot enable network access")
        if self.risk_level is RiskLevel.HIGH:
            raise ValueError("a high-risk plan cannot be persisted as a bounded artifact")
        if len(self.files_expected) > self.max_files_changed:
            raise ValueError("files_expected exceeds the plan's own file budget")
        return self


def plan_artifact_hash(fields: dict[str, Any]) -> str:
    """Canonical content hash over every artifact field except the hash itself."""
    body = {k: v for k, v in sorted(fields.items()) if k != "artifact_hash"}
    canonical = json.dumps(body, sort_keys=True, default=str)
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def build_plan_artifact(**fields: Any) -> RemediationPlanArtifact:
    """Construct an artifact with its content hash computed from the fields."""
    return RemediationPlanArtifact(**fields, artifact_hash=plan_artifact_hash(fields))


class PlanningDecision(StrictModel):
    """Outcome of one planning run: a bounded plan, or an explicit refusal
    with auditable reasons. A refusal never carries a plan."""

    outcome: PlanningOutcome
    plan: RemediationPlanArtifact | None = None
    reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_shape(self) -> "PlanningDecision":
        if self.outcome is PlanningOutcome.PLANNED:
            if self.plan is None:
                raise ValueError("a PLANNED decision requires a plan artifact")
        else:
            if self.plan is not None:
                raise ValueError("a refusal decision cannot carry a plan artifact")
            if not self.reasons:
                raise ValueError("a refusal decision requires at least one reason")
        return self


class ApprovalBinding(StrictModel):
    """Pins one approval request to one exact plan artifact.

    The decision endpoint refuses to decide when the bound plan is no longer
    the incident's latest artifact (stale id/version/hash) or when the caller's
    role does not match ``approver_role``. Single-use and expiry are enforced
    on the ApprovalRequest itself.
    """

    approval_id: str
    incident_id: str
    plan_id: str
    plan_version: int = Field(ge=1)
    plan_hash: str = Field(min_length=1, max_length=100)
    action: ApprovalType
    risk_level: RiskLevel
    approver_role: str = Field(min_length=1, max_length=100)
    expires_at: datetime
    created_at: datetime

    @model_validator(mode="after")
    def _validate_action(self) -> "ApprovalBinding":
        if self.action not in (ApprovalType.APPLY_PATCH, ApprovalType.CREATE_DRAFT_PR):
            raise ValueError("M4 approval bindings authorize APPLY_PATCH or CREATE_DRAFT_PR only")
        return self
