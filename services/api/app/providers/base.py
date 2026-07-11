"""Provider interfaces.

Domain and workflow code depends only on these protocols. Live adapters
(GitHub, Sentry, OpenAI Codex, Slack) arrive in M4-M7 and must implement the
same shapes; demo mode binds the simulated implementations instead.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from app.domain.contracts import Incident, RemediationPlan
from app.domain.enums import EvidenceKind


@dataclass(frozen=True)
class RawEvidence:
    """Unredacted evidence as returned by a provider. Must pass the redaction
    boundary before persistence."""

    kind: EvidenceKind
    source: str
    summary: str
    content: str
    observed_at: datetime
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HypothesisProposal:
    statement: str
    confidence: float
    supporting_evidence_indexes: list[int]
    contradictions: list[str]
    unknowns: list[str]


@dataclass(frozen=True)
class PlanProposal:
    summary: str
    steps: list[str]
    max_files_changed: int
    max_lines_changed: int


@dataclass(frozen=True)
class PatchProposal:
    diff: str
    files_changed: int
    lines_changed: int


@dataclass(frozen=True)
class VerificationCheckResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class PullRequestReceipt:
    provider: str
    url: str
    simulated: bool
    idempotency_key: str


@runtime_checkable
class TelemetryProvider(Protocol):
    """Fetches signals/logs/deploy history for an incident's service."""

    def fetch_evidence(self, incident: Incident) -> list[RawEvidence]: ...


@runtime_checkable
class InvestigationProvider(Protocol):
    """Produces root-cause hypotheses and remediation plans as typed proposals.

    In live mode this wraps the OpenAI Agents SDK; output is a proposal that
    deterministic workflow code evaluates — it never mutates state itself.
    """

    def propose_hypothesis(
        self, incident: Incident, evidence_summaries: list[str]
    ) -> HypothesisProposal: ...

    def propose_plan(self, incident: Incident, hypothesis: str) -> PlanProposal: ...


@runtime_checkable
class CodeAgentGateway(Protocol):
    """Produces a bounded patch for an approved remediation plan.

    In live mode this wraps the OpenAI Codex SDK against an isolated
    workspace; in demo mode it returns a deterministic fixture diff.
    """

    def propose_patch(self, incident: Incident, plan: RemediationPlan) -> PatchProposal: ...


@runtime_checkable
class VerificationRunner(Protocol):
    """Runs tests/lint/typecheck against a patched workspace."""

    def verify(self, incident: Incident, diff: str) -> list[VerificationCheckResult]: ...


@runtime_checkable
class PullRequestProvider(Protocol):
    """Creates draft pull requests. External writes must be idempotent."""

    def create_draft_pr(
        self, incident: Incident, diff: str, idempotency_key: str
    ) -> PullRequestReceipt: ...
