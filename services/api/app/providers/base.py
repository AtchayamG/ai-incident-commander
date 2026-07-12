"""Provider interfaces.

Domain and workflow code depends only on these protocols. Live adapters
(GitHub, Sentry, OpenAI Codex, Slack) arrive in M4-M7 and must implement the
same shapes; demo mode binds the simulated implementations instead.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from app.domain.contracts import EvidenceItem, Incident
from app.domain.enums import EvidenceKind
from app.domain.investigation import (
    InvestigationDraft,
    InvestigationReport,
    SpecialistFinding,
    SpecialistKind,
)
from app.domain.remediation import RemediationPlanDraft
from app.sandbox.workspace import SandboxWorkspace


@dataclass(frozen=True)
class RawEvidence:
    """Unredacted evidence as returned by a provider. Must pass the redaction
    boundary before persistence.

    ``observed_at`` is the time the underlying fact happened (deploy time,
    commit time, log timestamp) and drives chronological timeline ordering.
    ``display_ref`` is a stable human-facing reference for the evidence
    origin (dashboard URL, file path, commit ref) shown in the UI.
    """

    kind: EvidenceKind
    provider: str
    source: str
    summary: str
    content: str
    display_ref: str
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
class PatchTaskContext:
    """Bounded, typed instructions for one patch turn inside a workspace.

    Derived from the approved plan artifact only; carries no secrets, no
    credentials, and no host paths beyond the workspace itself.
    """

    incident_id: str
    service: str
    plan_summary: str
    steps: tuple[str, ...]
    files_expected: tuple[str, ...]
    max_files_changed: int
    max_lines_changed: int
    timeout_seconds: int


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
class EvidenceSource(Protocol):
    """Common shape of every evidence-producing provider. The pipeline treats
    all sources uniformly: fetch, redact, hash, persist."""

    def fetch_evidence(self, incident: Incident) -> list[RawEvidence]: ...


@runtime_checkable
class TelemetryProvider(EvidenceSource, Protocol):
    """Fetches alert metrics and log/error samples for an incident's service.

    Live adapters (Sentry, Grafana, CloudWatch) implement the same shape."""

    def fetch_evidence(self, incident: Incident) -> list[RawEvidence]: ...


@runtime_checkable
class DeploymentHistoryProvider(EvidenceSource, Protocol):
    """Fetches deployment history and the commits each deploy shipped.

    Live adapters (GitHub Deployments, Argo, Vercel) implement the same
    shape."""

    def fetch_evidence(self, incident: Incident) -> list[RawEvidence]: ...


@runtime_checkable
class LocalRepositoryProvider(EvidenceSource, Protocol):
    """Inspects a checkout of the affected service's repository (sources and
    tests) for gaps and regressions. Live adapters clone the real repo."""

    def fetch_evidence(self, incident: Incident) -> list[RawEvidence]: ...


@runtime_checkable
class RunbookProvider(EvidenceSource, Protocol):
    """Fetches operator runbook guidance for the affected service.

    Live adapters (Notion, Confluence, repo docs) implement the same shape."""

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
class InvestigationSpecialist(Protocol):
    """Bounded read-only analyst for one investigation angle (telemetry,
    change correlation, code mapping, runbook).

    Specialists see only persisted, redacted evidence for the incident and
    return typed findings whose every claim cites evidence IDs. They never
    mutate state; the investigation manager validates and persists output.
    """

    @property
    def kind(self) -> SpecialistKind: ...

    def analyze(
        self, incident: Incident, evidence: list[EvidenceItem]
    ) -> list[SpecialistFinding]: ...


@runtime_checkable
class InvestigationGateway(Protocol):
    """Replaceable model gateway that synthesizes the typed investigation
    draft (ranked hypotheses, code mapping, unknowns) from specialist
    findings.

    Live adapters wrap a hosted model with structured outputs; the model ID
    comes from the environment (``INVESTIGATION_MODEL``). Demo mode binds the
    deterministic fixture gateway and needs no credentials. Drafts are
    schema-validated and citation-checked by the manager and must never
    contain chain-of-thought.
    """

    @property
    def model_id(self) -> str: ...

    def synthesize(
        self,
        incident: Incident,
        evidence: list[EvidenceItem],
        findings: list[SpecialistFinding],
    ) -> InvestigationDraft: ...


@runtime_checkable
class RemediationPlannerGateway(Protocol):
    """Replaceable model gateway that drafts the smallest safe change plan
    from a COMPLETE investigation report (blueprint section 12.1E).

    Output is a typed draft only; the deterministic planning manager grounds
    it against the report's code mapping and applies the remediation policy
    before anything is persisted or approvable. Demo mode binds the fixture
    planner and needs no credentials.
    """

    @property
    def model_id(self) -> str: ...

    def propose(
        self, incident: Incident, report: InvestigationReport
    ) -> RemediationPlanDraft: ...


@runtime_checkable
class CodeAgentGateway(Protocol):
    """Applies a bounded patch turn inside an isolated ephemeral workspace.

    ``engine_id`` and ``simulated`` are explicit provenance: the fixture
    adapter is deterministic and always labeled simulated; the Codex CLI
    adapter drives the locally installed ``codex exec`` contract and fails
    closed when the binary, model, or credentials are unavailable. Fixture
    output is never described as live Codex. The gateway only edits files
    through (or inside) the workspace; the executor owns approval
    consumption, budget enforcement, diff capture, and destruction.
    """

    @property
    def engine_id(self) -> str: ...

    @property
    def simulated(self) -> bool: ...

    def apply_patch_turn(self, workspace: SandboxWorkspace, task: PatchTaskContext) -> None: ...


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
