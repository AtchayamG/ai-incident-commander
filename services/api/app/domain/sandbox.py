"""Typed M5 sandbox patch-execution artifacts (blueprint FR-007/FR-008, 19.1).

One ``PatchExecutionArtifact`` is the immutable record of one isolated
workspace run: which approval it consumed, which engine produced the patch
(with explicit simulated/live provenance), the captured unified diff with
per-file addition/deletion counts, the full lifecycle event log, and proof
that the ephemeral workspace was destroyed and the source fixture was never
mutated. Like the M4 plan artifact, the content hash covers every other
field so any tampering or regeneration is detectable.
"""

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import ProviderMode


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PatchExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SandboxLifecycleStage(StrEnum):
    """Auditable stages of the workspace lifecycle (blueprint 19.1)."""

    WORKSPACE_CREATED = "workspace_created"
    BASE_VERIFIED = "base_verified"
    READ_ONLY = "read_only"
    APPROVAL_CONSUMED = "approval_consumed"
    WRITE_ENABLED = "write_enabled"
    PATCH_TURN_STARTED = "patch_turn_started"
    PATCH_TURN_FAILED = "patch_turn_failed"
    PATCH_APPLIED = "patch_applied"
    POLICY_VIOLATION = "policy_violation"
    DIFF_CAPTURED = "diff_captured"
    WORKSPACE_DESTROYED = "workspace_destroyed"
    SOURCE_VERIFIED = "source_verified"


class SandboxLifecycleEvent(StrictModel):
    at: datetime
    stage: SandboxLifecycleStage
    detail: str = Field(min_length=1, max_length=1000)


class FileChange(StrictModel):
    """Per-file change statistics captured from the workspace diff."""

    path: str = Field(min_length=1, max_length=500)
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)


class PatchExecutionArtifact(StrictModel):
    """Immutable record of one isolated-workspace patch execution."""

    id: str
    incident_id: str
    plan_id: str
    plan_version: int = Field(ge=1)
    plan_hash: str = Field(min_length=1, max_length=100)
    approval_id: str = Field(
        min_length=1, description="The single-use APPLY_PATCH approval this run consumed"
    )
    engine_id: str = Field(min_length=1, max_length=200)
    simulated: bool
    provider_mode: ProviderMode
    workspace_id: str = Field(min_length=1, max_length=200)
    base_ref: str = Field(min_length=1, max_length=200)
    base_checksum: str = Field(min_length=1, max_length=100)
    status: PatchExecutionStatus
    changed_files: list[FileChange] = Field(default_factory=list)
    total_additions: int = Field(ge=0)
    total_deletions: int = Field(ge=0)
    unified_diff: str
    diff_hash: str = Field(min_length=1, max_length=100)
    attempts_used: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    failure_reasons: list[str] = Field(default_factory=list)
    workspace_destroyed: bool
    source_fixture_intact: bool
    lifecycle: list[SandboxLifecycleEvent] = Field(min_length=1)
    created_at: datetime
    artifact_hash: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def _validate_shape(self) -> "PatchExecutionArtifact":
        if self.simulated != (self.provider_mode is ProviderMode.SIMULATED):
            raise ValueError("simulated flag must match the provider mode")
        if self.status is PatchExecutionStatus.SUCCEEDED:
            if self.failure_reasons:
                raise ValueError("a succeeded execution cannot carry failure reasons")
            if not self.unified_diff or not self.changed_files:
                raise ValueError("a succeeded execution requires a captured non-empty diff")
            if not self.workspace_destroyed:
                raise ValueError("a succeeded execution requires proven workspace destruction")
            if not self.source_fixture_intact:
                raise ValueError("a succeeded execution requires an unmutated source fixture")
        else:
            if not self.failure_reasons:
                raise ValueError("a failed execution requires at least one failure reason")
        return self


def execution_artifact_hash(fields: dict[str, Any]) -> str:
    """Canonical content hash over the JSON form of every artifact field
    except the hash itself, so persisted documents re-verify byte-for-byte."""
    body = {k: v for k, v in sorted(fields.items()) if k != "artifact_hash"}
    canonical = json.dumps(body, sort_keys=True, default=str)
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def build_patch_execution_artifact(**fields: Any) -> PatchExecutionArtifact:
    """Construct an execution artifact with its content hash computed over
    the validated model's canonical JSON representation."""
    provisional = PatchExecutionArtifact(**fields, artifact_hash="sha256:pending")
    document = provisional.model_dump(mode="json")
    document.pop("artifact_hash")
    return provisional.model_copy(update={"artifact_hash": execution_artifact_hash(document)})
