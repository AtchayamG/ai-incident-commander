"""Typed M6 deterministic-verification artifacts (blueprint 14.2, 17.5, 19.4, M6).

One ``VerificationRunArtifact`` is the immutable record of one deterministic
verification pass over one captured candidate patch: the workspace was
materialized from the immutable fixture base plus the exact stored unified
diff (proven by byte-exact reconstruction against the stored diff hash), only
plan-authorized allowlisted argv commands ran (no shell), and every command's
sanitized, size-bounded output and exit code is captured. Pass/fail comes
only from deterministic process results — never from a model claim. Failures
are classified as a patch issue, an environment issue, or a pre-existing
failure using base-state evidence (the same command run against the pristine
base). Like the M4/M5 artifacts, the content hash covers every other field.

Provenance is explicit: the command execution is always a real subprocess
(``runner_id``); ``target_simulated`` says whether the repository under test
is the deterministic demo fixture rather than a live checkout.
"""

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import RiskLevel


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CheckCategory(StrEnum):
    """Deterministic check categories (blueprint 19.2/19.3 command baseline)."""

    TARGETED_TEST = "targeted_test"
    TEST = "test"
    LINT = "lint"
    TYPECHECK = "typecheck"


TEST_CATEGORIES: frozenset[CheckCategory] = frozenset(
    {CheckCategory.TARGETED_TEST, CheckCategory.TEST}
)


class VerificationFailureKind(StrEnum):
    """Deterministic failure classification (blueprint 19.4)."""

    PATCH_ISSUE = "patch_issue"
    ENVIRONMENT_ISSUE = "environment_issue"
    PRE_EXISTING_FAILURE = "pre_existing_failure"


class VerificationCommandResult(StrictModel):
    """One allowlisted command run: what ran, against which tree, and the
    deterministic process outcome. Output is redacted and size-bounded."""

    command: str = Field(min_length=1, max_length=200)
    category: CheckCategory
    argv: list[str] = Field(min_length=1)
    baseline: bool = Field(
        default=False,
        description="True when this run executed against the pristine base "
        "tree to gather pre-existing-failure evidence",
    )
    exit_code: int | None = Field(
        default=None, description="None when the process could not be spawned"
    )
    duration_ms: int = Field(ge=0)
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    timed_out: bool
    spawn_error: str | None = None

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and self.spawn_error is None


class RiskFinding(StrictModel):
    rule: str = Field(min_length=1, max_length=100)
    path: str | None = Field(default=None, max_length=500)
    detail: str = Field(min_length=1, max_length=500)
    risk_level: RiskLevel


class RiskReview(StrictModel):
    """Deterministic review over the captured diff's paths, size, and content.

    ``blocks_pr`` is the default policy outcome: HIGH risk (auth, payments,
    migrations, infra, secrets, crypto) blocks real PR readiness (blueprint
    21.3)."""

    risk_level: RiskLevel
    findings: list[RiskFinding] = Field(default_factory=list)
    files_changed: int = Field(ge=0)
    lines_changed: int = Field(ge=0)
    blocks_pr: bool

    @model_validator(mode="after")
    def _validate_block(self) -> "RiskReview":
        if self.risk_level is RiskLevel.HIGH and not self.blocks_pr:
            raise ValueError("high-risk reviews block PR readiness by default")
        return self


class VerificationRunArtifact(StrictModel):
    """Immutable record of one deterministic verification of one patch."""

    id: str
    incident_id: str
    patch_id: str
    patch_execution_id: str
    plan_id: str
    plan_hash: str = Field(min_length=1, max_length=100)
    attempt: int = Field(ge=1)
    base_ref: str = Field(min_length=1, max_length=200)
    base_checksum: str = Field(min_length=1, max_length=100)
    diff_hash: str = Field(
        min_length=1,
        max_length=100,
        description="Hash of the stored candidate diff this run reconstructed",
    )
    diff_reconstructed: bool = Field(
        description="The workspace diff re-derived byte-exact to the stored diff"
    )
    workspace_id: str = Field(min_length=1, max_length=200)
    runner_id: str = Field(min_length=1, max_length=200)
    target_simulated: bool = Field(
        description="True when the repository under test is the demo fixture"
    )
    commands: list[VerificationCommandResult] = Field(default_factory=list)
    relevant_regression_test: bool
    passed: bool
    failure_kind: VerificationFailureKind | None = None
    failure_evidence: list[str] = Field(default_factory=list)
    risk: RiskReview
    workspace_destroyed: bool
    total_duration_ms: int = Field(ge=0)
    budget_seconds: int = Field(ge=1)
    created_at: datetime
    artifact_hash: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def _validate_shape(self) -> "VerificationRunArtifact":
        if self.passed:
            if self.failure_kind is not None or self.failure_evidence:
                raise ValueError("a passed verification cannot carry failure evidence")
            if not self.relevant_regression_test:
                raise ValueError("a passed verification requires a relevant regression test")
            if not self.diff_reconstructed:
                raise ValueError("a passed verification requires byte-exact diff reconstruction")
            if not self.commands or not all(c.passed for c in self.commands if not c.baseline):
                raise ValueError("a passed verification requires every required check to pass")
        else:
            if self.failure_kind is None or not self.failure_evidence:
                raise ValueError("a failed verification requires classified failure evidence")
        if not self.workspace_destroyed:
            raise ValueError("a verification artifact requires proven workspace destruction")
        return self


def verification_artifact_hash(fields: dict[str, Any]) -> str:
    body = {k: v for k, v in sorted(fields.items()) if k != "artifact_hash"}
    canonical = json.dumps(body, sort_keys=True, default=str)
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def build_verification_artifact(**fields: Any) -> VerificationRunArtifact:
    """Construct a verification artifact with its content hash computed over
    the validated model's canonical JSON representation."""
    provisional = VerificationRunArtifact(**fields, artifact_hash="sha256:pending")
    document = provisional.model_dump(mode="json")
    document.pop("artifact_hash")
    return provisional.model_copy(
        update={"artifact_hash": verification_artifact_hash(document)}
    )
