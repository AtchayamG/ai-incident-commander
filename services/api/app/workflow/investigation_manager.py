"""Investigation manager: the single explicit stage that turns persisted,
redacted evidence into a typed, persistable investigation report (M3).

The manager owns the deterministic control flow and the safety rules; the
bounded specialists and the model gateway are replaceable behind protocols
(``app.providers.base``). The sequence is fixed:

1. Run every bounded specialist over the same persisted evidence.
2. Reject any specialist finding whose citations do not resolve to a
   persisted evidence ID for this incident.
3. Ask the gateway to synthesize a draft (summary, ranked hypotheses, code
   mapping, unknowns) from only the surviving findings.
4. Re-validate every material claim in the draft against persisted evidence;
   drop the summary or code mapping and reject any hypothesis that cites
   unknown evidence.
5. Downgrade to ``INSUFFICIENT_EVIDENCE`` whenever a COMPLETE draft no longer
   has a summary, a code mapping, and at least three grounded hypotheses.

Remediation can only be enabled when the final status is COMPLETE, so the
insufficient-evidence path is safe by construction. Rejected claims are kept
on the report for audit and are never acted on. The strict schema
(``extra="forbid"``) means a gateway cannot smuggle chain-of-thought through;
the only narrative fields are the length-bounded ``rationale``/summary text.
"""

from collections.abc import Sequence
from datetime import datetime

from app.domain.contracts import EvidenceItem, Incident
from app.domain.investigation import (
    CodeMapping,
    EvidenceCitation,
    IncidentSummary,
    InvestigationDraft,
    InvestigationReport,
    InvestigationStatus,
    RankedHypothesis,
    RejectedClaim,
    SpecialistFinding,
)
from app.providers.base import InvestigationGateway, InvestigationSpecialist

_MIN_COMPLETE_HYPOTHESES = 3


def _unresolved(citations: Sequence[EvidenceCitation], valid_ids: set[str]) -> list[str]:
    """Return the sorted, de-duplicated evidence IDs a claim cites that are not
    persisted evidence for this incident."""
    return sorted({c.evidence_id for c in citations if c.evidence_id not in valid_ids})


class InvestigationManager:
    def __init__(
        self,
        specialists: Sequence[InvestigationSpecialist],
        gateway: InvestigationGateway,
    ) -> None:
        self._specialists = tuple(specialists)
        self._gateway = gateway

    @property
    def gateway_model_id(self) -> str:
        return self._gateway.model_id

    def investigate(
        self,
        incident: Incident,
        evidence: list[EvidenceItem],
        report_id: str,
        now: datetime,
    ) -> InvestigationReport:
        """Produce one validated, persistable investigation report.

        Deterministic in its inputs: identical evidence, ``report_id``, and
        ``now`` yield an identical report, so the golden incident is
        assertable byte-for-byte.
        """
        valid_ids = {item.id for item in evidence}
        rejected: list[RejectedClaim] = []

        findings = self._collect_findings(incident, evidence, valid_ids, rejected)
        draft = self._gateway.synthesize(incident, evidence, findings)
        summary, code_mapping, hypotheses = self._validate_draft(draft, valid_ids, rejected)
        status = self._resolve_status(draft.status, summary, code_mapping, hypotheses)

        return InvestigationReport(
            id=report_id,
            incident_id=incident.id,
            status=status,
            gateway=self._gateway.model_id,
            remediation_enabled=status is InvestigationStatus.COMPLETE,
            summary=summary,
            findings=findings,
            hypotheses=hypotheses,
            code_mapping=code_mapping,
            unknowns=list(draft.unknowns),
            rejected_claims=rejected,
            created_at=now,
        )

    # Internal stages -------------------------------------------------------

    def _collect_findings(
        self,
        incident: Incident,
        evidence: list[EvidenceItem],
        valid_ids: set[str],
        rejected: list[RejectedClaim],
    ) -> list[SpecialistFinding]:
        valid: list[SpecialistFinding] = []
        for specialist in self._specialists:
            for finding in specialist.analyze(incident, evidence):
                unresolved = _unresolved(finding.citations, valid_ids)
                if unresolved:
                    rejected.append(
                        RejectedClaim(
                            origin=f"specialist:{finding.specialist}",
                            statement=finding.statement,
                            reason=f"cites unknown evidence: {', '.join(unresolved)}",
                        )
                    )
                else:
                    valid.append(finding)
        return valid

    def _validate_draft(
        self,
        draft: InvestigationDraft,
        valid_ids: set[str],
        rejected: list[RejectedClaim],
    ) -> tuple[IncidentSummary | None, CodeMapping | None, list[RankedHypothesis]]:
        summary = draft.summary
        if summary is not None:
            unresolved = _unresolved(summary.citations, valid_ids)
            if unresolved:
                rejected.append(
                    RejectedClaim(
                        origin="summary",
                        statement=summary.what_happened,
                        reason=f"cites unknown evidence: {', '.join(unresolved)}",
                    )
                )
                summary = None

        code_mapping = draft.code_mapping
        if code_mapping is not None:
            unresolved = self._code_mapping_unresolved(code_mapping, valid_ids)
            if unresolved:
                rejected.append(
                    RejectedClaim(
                        origin="code_mapping",
                        statement=code_mapping.coverage_gap,
                        reason=f"cites unknown evidence: {', '.join(unresolved)}",
                    )
                )
                code_mapping = None

        kept: list[RankedHypothesis] = []
        for hypothesis in draft.hypotheses:
            claims = list(hypothesis.supporting) + list(hypothesis.contradicting)
            unresolved = _unresolved(claims, valid_ids)
            if unresolved:
                rejected.append(
                    RejectedClaim(
                        origin=f"hypothesis:rank-{hypothesis.rank}",
                        statement=hypothesis.statement,
                        reason=f"cites unknown evidence: {', '.join(unresolved)}",
                    )
                )
            else:
                kept.append(hypothesis)

        # Re-rank the survivors so ranks stay contiguous from 1; dropping never
        # reorders, so confidence remains non-increasing.
        reranked = [h.model_copy(update={"rank": i}) for i, h in enumerate(kept, start=1)]
        return summary, code_mapping, reranked

    @staticmethod
    def _code_mapping_unresolved(code_mapping: CodeMapping, valid_ids: set[str]) -> list[str]:
        citations: list[EvidenceCitation] = [
            *code_mapping.commit_citations,
            *code_mapping.coverage_gap_citations,
        ]
        for affected in code_mapping.affected_files:
            citations.extend(affected.citations)
        return _unresolved(citations, valid_ids)

    @staticmethod
    def _resolve_status(
        drafted: InvestigationStatus,
        summary: IncidentSummary | None,
        code_mapping: CodeMapping | None,
        hypotheses: list[RankedHypothesis],
    ) -> InvestigationStatus:
        if drafted is not InvestigationStatus.COMPLETE:
            return drafted
        if (
            summary is None
            or code_mapping is None
            or len(hypotheses) < _MIN_COMPLETE_HYPOTHESES
        ):
            return InvestigationStatus.INSUFFICIENT_EVIDENCE
        return InvestigationStatus.COMPLETE
