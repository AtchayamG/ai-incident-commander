"""Typed investigation-agent outputs (M3).

Structured outputs the investigation stage persists: incident summary,
specialist findings, ranked evidence-grounded hypotheses, code/commit mapping,
explicit unknowns, and bounded falsification tests. Every material claim
carries citations by persisted evidence ID; the investigation manager rejects
claims whose citations do not resolve. Models are strict (``extra="forbid"``)
so a gateway cannot attach free-form fields such as chain-of-thought; the only
narrative field is the length-bounded ``rationale``.

These models are backend-internal for M3 (served read-only over the API) and
are not yet mirrored in packages/contracts.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SpecialistKind(StrEnum):
    TELEMETRY = "telemetry"
    CHANGE_CORRELATION = "change_correlation"
    CODE_MAPPING = "code_mapping"
    RUNBOOK = "runbook"


class InvestigationStatus(StrEnum):
    COMPLETE = "complete"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EvidenceCitation(StrictModel):
    """A material claim's pointer to one persisted, redacted evidence item."""

    evidence_id: str = Field(min_length=1, max_length=100)
    note: str = Field(
        min_length=1, max_length=300, description="What the cited evidence shows"
    )


class SpecialistFinding(StrictModel):
    specialist: SpecialistKind
    statement: str = Field(min_length=1, max_length=1000)
    citations: list[EvidenceCitation] = Field(min_length=1)


class RejectedClaim(StrictModel):
    """A claim the validation stage refused. Kept for audit, never acted on."""

    origin: str = Field(min_length=1, max_length=100)
    statement: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=500)


class FalsificationTest(StrictModel):
    """A bounded, read-only check that could disprove a hypothesis."""

    description: str = Field(min_length=1, max_length=300)
    steps: list[str] = Field(min_length=1, max_length=5)
    expected_if_true: str = Field(min_length=1, max_length=300)
    expected_if_false: str = Field(min_length=1, max_length=300)


class AffectedFile(StrictModel):
    path: str = Field(min_length=1, max_length=300)
    role: str = Field(min_length=1, max_length=300)
    citations: list[EvidenceCitation] = Field(min_length=1)


class CodeMapping(StrictModel):
    """Where the defect lives: files, the suspect commit, and the test gap."""

    affected_files: list[AffectedFile] = Field(min_length=1)
    suspect_commit: str = Field(min_length=1, max_length=100)
    commit_citations: list[EvidenceCitation] = Field(min_length=1)
    coverage_gap: str = Field(min_length=1, max_length=500)
    coverage_gap_citations: list[EvidenceCitation] = Field(min_length=1)


class RankedHypothesis(StrictModel):
    """One ranked root-cause candidate. Supporting and contradicting evidence
    plus at least one explicit unknown are mandatory for every hypothesis."""

    rank: int = Field(ge=1)
    hypothesis_id: str | None = Field(
        default=None, description="ID of the persisted Hypothesis row, set on persist"
    )
    statement: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0.0, le=1.0)
    supporting: list[EvidenceCitation] = Field(min_length=1)
    contradicting: list[EvidenceCitation] = Field(min_length=1)
    unknowns: list[str] = Field(min_length=1)
    falsification_tests: list[FalsificationTest] = Field(min_length=1, max_length=3)
    affected_files: list[str] = Field(default_factory=list)
    suspect_commit: str | None = Field(default=None, max_length=100)
    rationale: str = Field(
        min_length=1,
        max_length=600,
        description="Concise justification; never chain-of-thought",
    )


class IncidentSummary(StrictModel):
    what_happened: str = Field(min_length=1, max_length=1000)
    impact: str = Field(min_length=1, max_length=500)
    citations: list[EvidenceCitation] = Field(min_length=1)


def _check_report_shape(
    status: InvestigationStatus,
    summary: IncidentSummary | None,
    code_mapping: CodeMapping | None,
    hypotheses: list[RankedHypothesis],
) -> None:
    if status is InvestigationStatus.COMPLETE:
        if summary is None:
            raise ValueError("a complete investigation requires an incident summary")
        if code_mapping is None:
            raise ValueError("a complete investigation requires a code mapping")
        if len(hypotheses) < 3:
            raise ValueError("a complete investigation requires at least three hypotheses")
    ranks = [h.rank for h in hypotheses]
    if ranks != list(range(1, len(ranks) + 1)):
        raise ValueError("hypothesis ranks must be contiguous starting at 1")
    confidences = [h.confidence for h in hypotheses]
    if any(a < b for a, b in zip(confidences, confidences[1:], strict=False)):
        raise ValueError("hypothesis confidence must be non-increasing with rank")


class InvestigationDraft(StrictModel):
    """Gateway output before citation validation and persistence."""

    status: InvestigationStatus
    summary: IncidentSummary | None = None
    findings: list[SpecialistFinding] = Field(default_factory=list)
    hypotheses: list[RankedHypothesis] = Field(default_factory=list)
    code_mapping: CodeMapping | None = None
    unknowns: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_shape(self) -> "InvestigationDraft":
        _check_report_shape(self.status, self.summary, self.code_mapping, self.hypotheses)
        return self


class InvestigationReport(StrictModel):
    """Validated, persisted investigation output for one incident run."""

    id: str
    incident_id: str
    status: InvestigationStatus
    gateway: str = Field(description="Model gateway identifier that produced the draft")
    remediation_enabled: bool
    summary: IncidentSummary | None
    findings: list[SpecialistFinding]
    hypotheses: list[RankedHypothesis]
    code_mapping: CodeMapping | None
    unknowns: list[str]
    rejected_claims: list[RejectedClaim]
    created_at: datetime

    @model_validator(mode="after")
    def _validate_shape(self) -> "InvestigationReport":
        _check_report_shape(self.status, self.summary, self.code_mapping, self.hypotheses)
        if self.status is not InvestigationStatus.COMPLETE and self.remediation_enabled:
            raise ValueError("remediation cannot be enabled without a complete investigation")
        return self
