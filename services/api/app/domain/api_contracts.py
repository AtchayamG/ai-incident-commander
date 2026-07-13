"""Strict request and response contracts for public API actions."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import EvidenceKind, WorkflowState


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ManualEvidenceCreate(StrictModel):
    kind: EvidenceKind
    source: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=100_000)
    display_ref: str = Field(min_length=1, max_length=500)
    captured_at: datetime
    origin: str = Field(default="operator", min_length=1, max_length=100)


class HypothesisFeedbackKind(StrEnum):
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"


class HypothesisFeedbackCreate(StrictModel):
    feedback: HypothesisFeedbackKind
    reason: str = Field(min_length=1, max_length=1000)


class HypothesisFeedbackReceipt(StrictModel):
    incident_id: str
    hypothesis_id: str
    feedback: HypothesisFeedbackKind
    reason: str
    recorded_at: datetime


class RemediationPlanRevision(StrictModel):
    reason: str = Field(min_length=1, max_length=1000)
    summary: str | None = Field(default=None, min_length=1, max_length=500)
    steps: list[str] | None = Field(default=None, min_length=1, max_length=10)
    rollback: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def _require_change(self) -> "RemediationPlanRevision":
        if self.summary is None and self.steps is None and self.rollback is None:
            raise ValueError("at least one bounded plan field must be revised")
        return self


class PatchDiffResponse(StrictModel):
    patch_id: str
    incident_id: str
    attempt: int
    unified_diff: str
    diff_hash: str
    files_changed: int
    lines_changed: int


class PatchRetryRequest(StrictModel):
    reason: str = Field(min_length=1, max_length=1000)


class PatchRetryResponse(StrictModel):
    patch_id: str
    incident_id: str
    accepted: Literal[True]
    state: WorkflowState
    attempts_used: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    attempts_remaining: int = Field(ge=0)


class IntegrationStatusKind(StrEnum):
    SIMULATED = "simulated"
    UNCONFIGURED = "unconfigured"
    CONFIGURED_NOT_PROBED = "configured_not_probed"


class IntegrationStatus(StrictModel):
    provider: str
    capability: str
    status: IntegrationStatusKind
    credential_configured: bool
    external_request_made: bool = False


class IntegrationTestResult(StrictModel):
    provider: str
    status: IntegrationStatusKind
    connected: Literal[False]
    external_request_made: Literal[False]
    detail: str
