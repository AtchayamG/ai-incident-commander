"""Remediation planning manager: the single explicit M4 stage that turns a
COMPLETE investigation report into a bounded, persistable remediation plan —
or an explicit, auditable refusal.

The planner gateway is replaceable behind a protocol (``app.providers.base``);
this manager owns the deterministic control flow and every safety rule:

1. Refuse with NEEDS_INPUT unless the report is COMPLETE, has remediation
   enabled, carries a code mapping, and belongs to this incident.
2. Ask the gateway for a typed draft.
3. Ground the draft structurally: every expected file must appear in the
   report's code mapping, and at least one must be a test file (the plan must
   add a regression test, not just patch code).
4. Apply the remediation policy: prohibited paths, command allowlist, change
   and attempt budgets, timeout ceiling, no-network default, and risk
   classification. HIGH risk is refused, never planned.
5. Any violation yields NO_SAFE_REMEDIATION with the full reason list; only a
   clean draft becomes a persisted artifact with a content hash for approval
   binding.

Deterministic in its inputs: identical report, ``plan_id``, ``version``, and
``now`` yield an identical artifact, hash included.
"""

from datetime import datetime

from app.domain.contracts import Incident
from app.domain.enums import RiskLevel
from app.domain.investigation import InvestigationReport, InvestigationStatus
from app.domain.remediation import (
    PlanningDecision,
    PlanningOutcome,
    RemediationPlanDraft,
    build_plan_artifact,
)
from app.providers.base import RemediationPlannerGateway
from app.workflow.policy import (
    PROHIBITED_PATH_PATTERNS,
    PolicyLimits,
    classify_risk,
    command_allowed,
    path_prohibited,
)


class RemediationPlanningManager:
    def __init__(
        self,
        planner: RemediationPlannerGateway,
        limits: PolicyLimits | None = None,
    ) -> None:
        self._planner = planner
        self._limits = limits or PolicyLimits()

    @property
    def planner_model_id(self) -> str:
        return self._planner.model_id

    def plan(
        self,
        incident: Incident,
        report: InvestigationReport,
        plan_id: str,
        now: datetime,
        version: int = 1,
    ) -> PlanningDecision:
        insufficient = self._insufficient_evidence_reasons(incident, report)
        if insufficient:
            return PlanningDecision(
                outcome=PlanningOutcome.NEEDS_INPUT, reasons=insufficient
            )

        draft = self._planner.propose(incident, report)
        violations = self._policy_violations(incident, report, draft)
        if violations:
            return PlanningDecision(
                outcome=PlanningOutcome.NO_SAFE_REMEDIATION, reasons=violations
            )

        top_hypothesis = report.hypotheses[0]
        artifact = build_plan_artifact(
            id=plan_id,
            incident_id=incident.id,
            investigation_report_id=report.id,
            hypothesis_id=top_hypothesis.hypothesis_id or f"{report.id}:rank-1",
            version=version,
            summary=draft.summary,
            files_expected=list(draft.files_expected),
            steps=list(draft.steps),
            verification_commands=list(draft.verification_commands),
            allowed_commands=list(draft.allowed_commands),
            prohibited_paths=list(PROHIBITED_PATH_PATTERNS),
            risk_level=classify_risk(incident, draft),
            max_files_changed=draft.max_files_changed,
            max_lines_changed=draft.max_lines_changed,
            max_attempts=draft.max_attempts,
            timeout_seconds=draft.timeout_seconds,
            network_allowed=draft.network_allowed,
            rollback=draft.rollback,
            rationale=draft.rationale,
            created_at=now,
        )
        return PlanningDecision(outcome=PlanningOutcome.PLANNED, plan=artifact)

    # Internal stages -------------------------------------------------------

    @staticmethod
    def _insufficient_evidence_reasons(
        incident: Incident, report: InvestigationReport
    ) -> list[str]:
        reasons: list[str] = []
        if report.incident_id != incident.id:
            reasons.append("investigation report does not belong to this incident")
        if report.status is not InvestigationStatus.COMPLETE:
            reasons.append("investigation is not COMPLETE; remediation cannot be planned")
        if not report.remediation_enabled:
            reasons.append("investigation did not enable remediation")
        if report.code_mapping is None:
            reasons.append("investigation has no code mapping to ground a plan in")
        if not report.hypotheses:
            reasons.append("investigation has no ranked hypotheses")
        return reasons

    def _policy_violations(
        self,
        incident: Incident,
        report: InvestigationReport,
        draft: RemediationPlanDraft,
    ) -> list[str]:
        assert report.code_mapping is not None  # guarded by _insufficient_evidence_reasons
        mapped = {f.path for f in report.code_mapping.affected_files}
        violations: list[str] = []

        for path in draft.files_expected:
            if path not in mapped:
                violations.append(
                    f"file {path} is not grounded in the investigation code mapping"
                )
            if path_prohibited(path):
                violations.append(f"file {path} matches a prohibited path pattern")
        if not any("test" in path.lower() for path in draft.files_expected):
            violations.append("plan does not name a test file; a regression test is required")

        for command in [*draft.verification_commands, *draft.allowed_commands]:
            if not command_allowed(command):
                violations.append(f"command not in the safe allowlist: {command}")
        for command in draft.verification_commands:
            if command not in draft.allowed_commands:
                violations.append(f"verification command not in the plan's allowlist: {command}")

        limits = self._limits
        if len(draft.files_expected) > draft.max_files_changed:
            violations.append("plan names more files than its own file budget")
        if draft.max_files_changed > limits.max_files:
            violations.append(
                f"file budget {draft.max_files_changed} exceeds policy limit {limits.max_files}"
            )
        if draft.max_lines_changed > limits.max_lines:
            violations.append(
                f"line budget {draft.max_lines_changed} exceeds policy limit {limits.max_lines}"
            )
        if draft.max_attempts > limits.max_attempts:
            violations.append(
                f"attempt budget {draft.max_attempts} exceeds policy limit"
                f" {limits.max_attempts}"
            )
        if draft.timeout_seconds > limits.max_timeout_seconds:
            violations.append(
                f"timeout {draft.timeout_seconds}s exceeds policy limit"
                f" {limits.max_timeout_seconds}s"
            )
        if draft.network_allowed:
            violations.append("plan requests network access; network is off by default")

        if classify_risk(incident, draft) is RiskLevel.HIGH:
            violations.append("plan classifies as HIGH risk; automated remediation refused")
        return violations
