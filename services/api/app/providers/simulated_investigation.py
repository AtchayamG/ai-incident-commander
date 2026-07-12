"""Deterministic simulated investigation specialists and model gateway (M3).

No network, no credentials, no randomness. Specialists analyse only the
persisted, redacted evidence they are handed and cite persisted evidence IDs;
the fixture gateway synthesizes the golden checkout-api investigation draft
(three ranked hypotheses, code/commit mapping, unknowns) from those same
evidence rows. When the golden evidence is missing the gateway returns an
insufficient-evidence draft instead of guessing, which disables remediation
downstream.
"""

from app.domain.contracts import EvidenceItem, Incident
from app.domain.investigation import (
    AffectedFile,
    CodeMapping,
    EvidenceCitation,
    FalsificationTest,
    IncidentSummary,
    InvestigationDraft,
    InvestigationStatus,
    RankedHypothesis,
    SpecialistFinding,
    SpecialistKind,
)


def _find(
    evidence: list[EvidenceItem], ref_suffix: str, summary_contains: str | None = None
) -> EvidenceItem | None:
    """Locate one evidence item by display-ref suffix (and summary text when
    several items share a fixture file). Returns None when absent so callers
    can degrade honestly instead of fabricating citations."""
    for item in evidence:
        if item.display_ref.endswith(ref_suffix) and (
            summary_contains is None or summary_contains in item.summary
        ):
            return item
    return None


def _cite(item: EvidenceItem, note: str) -> EvidenceCitation:
    return EvidenceCitation(evidence_id=item.id, note=note)


class FixtureTelemetrySpecialist:
    """Error-rate, stack-trace, and failure-pattern analysis."""

    kind: SpecialistKind = SpecialistKind.TELEMETRY

    def analyze(
        self, incident: Incident, evidence: list[EvidenceItem]
    ) -> list[SpecialistFinding]:
        findings: list[SpecialistFinding] = []
        breach = _find(evidence, "telemetry/alerts.json", "breached")
        rate = _find(evidence, "telemetry/alerts.json", "rose from")
        if breach is not None and rate is not None:
            findings.append(
                SpecialistFinding(
                    specialist=self.kind,
                    statement=(
                        f"HTTP 500 rate on {incident.service} rose from 0.2% to 12.4%, "
                        "breaching the 5.0% alert threshold at 2026-07-13T10:05Z"
                    ),
                    citations=[
                        _cite(breach, "alert fired at incident start 10:05Z"),
                        _cite(rate, "observed 12.4% against a 0.2% baseline"),
                    ],
                )
            )
        log = _find(evidence, "telemetry/error_samples.log")
        if log is not None:
            findings.append(
                SpecialistFinding(
                    specialist=self.kind,
                    statement=(
                        "Recurring TypeError reading a discount property of undefined at "
                        "applyDiscount in src/checkout.ts"
                    ),
                    citations=[_cite(log, "stack trace points at src/checkout.ts applyDiscount")],
                )
            )
        samples = _find(evidence, "telemetry/samples_analysis.json")
        if samples is not None:
            findings.append(
                SpecialistFinding(
                    specialist=self.kind,
                    statement=(
                        "All 128 failed requests are checkout sessions without a discount; "
                        "sessions carrying a discount succeed"
                    ),
                    citations=[
                        _cite(samples, "128/128 failures lack a discount; 45 discounted succeed")
                    ],
                )
            )
        return findings


class FixtureChangeCorrelationSpecialist:
    """Correlates deploys and commits with the incident window."""

    kind: SpecialistKind = SpecialistKind.CHANGE_CORRELATION

    def analyze(
        self, incident: Incident, evidence: list[EvidenceItem]
    ) -> list[SpecialistFinding]:
        findings: list[SpecialistFinding] = []
        deploy = _find(evidence, "deploys/deploys.json")
        breach = _find(evidence, "telemetry/alerts.json", "breached")
        if deploy is not None and breach is not None:
            findings.append(
                SpecialistFinding(
                    specialist=self.kind,
                    statement=(
                        f"Version 2026.07.13.4 of {incident.service} deployed at "
                        "2026-07-13T10:02Z, three minutes before the 500-rate breach"
                    ),
                    citations=[
                        _cite(deploy, "deploy landed at 10:02Z"),
                        _cite(breach, "500-rate breach started at 10:05Z"),
                    ],
                )
            )
        diff = _find(evidence, "repo/history/c7f2e9a.diff")
        if diff is not None and deploy is not None:
            findings.append(
                SpecialistFinding(
                    specialist=self.kind,
                    statement=(
                        "Deploy 2026.07.13.4 shipped commit c7f2e9a, which modified discount "
                        "handling in src/checkout.ts"
                    ),
                    citations=[
                        _cite(diff, "commit c7f2e9a diff touches src/checkout.ts applyDiscount"),
                        _cite(deploy, "2026.07.13.4 maps to commit c7f2e9a"),
                    ],
                )
            )
        return findings


class FixtureCodeMappingSpecialist:
    """Maps the failure onto files, commits, and the test coverage gap."""

    kind: SpecialistKind = SpecialistKind.CODE_MAPPING

    def analyze(
        self, incident: Incident, evidence: list[EvidenceItem]
    ) -> list[SpecialistFinding]:
        findings: list[SpecialistFinding] = []
        diff = _find(evidence, "repo/history/c7f2e9a.diff")
        if diff is not None:
            findings.append(
                SpecialistFinding(
                    specialist=self.kind,
                    statement=(
                        "Commit c7f2e9a replaced the optional access "
                        "`session.discount?.code ?? null` with unsafe `session.discount.code` "
                        "in src/checkout.ts applyDiscount"
                    ),
                    citations=[_cite(diff, "diff shows the optional guard removed")],
                )
            )
        coverage = _find(evidence, "repo/src/checkout.test.ts")
        if coverage is not None:
            findings.append(
                SpecialistFinding(
                    specialist=self.kind,
                    statement=(
                        "src/checkout.test.ts covers discounted sessions only; no test "
                        "exercises a session without a discount"
                    ),
                    citations=[_cite(coverage, "test file lacks a no-discount case")],
                )
            )
        return findings


class FixtureRunbookSpecialist:
    """Extracts operator guidance relevant to the incident."""

    kind: SpecialistKind = SpecialistKind.RUNBOOK

    def analyze(
        self, incident: Incident, evidence: list[EvidenceItem]
    ) -> list[SpecialistFinding]:
        runbook = _find(evidence, f"runbooks/{incident.service}.txt")
        if runbook is None:
            return []
        return [
            SpecialistFinding(
                specialist=self.kind,
                statement=(
                    f"The {incident.service} runbook directs a deployment-correlation check "
                    "first, then local reproduction of the failing request before patching"
                ),
                citations=[_cite(runbook, "runbook ordering: correlate deploy, then reproduce")],
            )
        ]


class FixtureInvestigationGateway:
    """Deterministic stand-in for a hosted structured-output model.

    ``model_id`` is environment-driven configuration passed through
    ``Settings``; the fixture output itself never depends on it.
    """

    def __init__(self, model_id: str = "simulated-fixture") -> None:
        self.model_id = model_id

    def synthesize(
        self,
        incident: Incident,
        evidence: list[EvidenceItem],
        findings: list[SpecialistFinding],
    ) -> InvestigationDraft:
        breach = _find(evidence, "telemetry/alerts.json", "breached")
        rate = _find(evidence, "telemetry/alerts.json", "rose from")
        log = _find(evidence, "telemetry/error_samples.log")
        samples = _find(evidence, "telemetry/samples_analysis.json")
        deploy = _find(evidence, "deploys/deploys.json")
        diff = _find(evidence, "repo/history/c7f2e9a.diff")
        coverage = _find(evidence, "repo/src/checkout.test.ts")
        if (
            breach is None
            or rate is None
            or log is None
            or samples is None
            or deploy is None
            or diff is None
            or coverage is None
        ):
            return InvestigationDraft(
                status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
                findings=list(findings),
                unknowns=[
                    "Required golden-incident evidence (telemetry, deploy history, commit "
                    "diff, or test coverage) is missing; hypotheses cannot be grounded"
                ],
            )

        summary = IncidentSummary(
            what_happened=(
                f"HTTP 500 rate on {incident.service} rose from 0.2% to 12.4% starting "
                "2026-07-13T10:05Z, three minutes after deploy 2026.07.13.4; every failed "
                "request is a checkout session without a discount."
            ),
            impact=(
                "About one in eight checkout requests fails with HTTP 500; customers "
                "without a discount code cannot complete checkout."
            ),
            citations=[
                _cite(breach, "breach at 10:05Z"),
                _cite(deploy, "deploy at 10:02Z"),
                _cite(samples, "all 128 failures lack a discount"),
            ],
        )

        top = RankedHypothesis(
            rank=1,
            statement=(
                "Commit c7f2e9a, shipped in deploy 2026.07.13.4, replaced the optional "
                "discount access with unsafe `session.discount.code` in src/checkout.ts "
                "applyDiscount; checkout sessions without a discount throw TypeError and "
                "return HTTP 500."
            ),
            confidence=0.85,
            supporting=[
                _cite(diff, "diff replaces `session.discount?.code ?? null` with unsafe access"),
                _cite(deploy, "2026.07.13.4 landed at 10:02Z, three minutes before the breach"),
                _cite(log, "TypeError raised at applyDiscount in src/checkout.ts"),
                _cite(samples, "failures are exactly the sessions without a discount"),
            ],
            contradicting=[
                _cite(
                    samples,
                    "sampled window is only four minutes; no pre-deploy sample proves the "
                    "no-discount path worked before 2026.07.13.4",
                )
            ],
            unknowns=[
                "Whether any no-discount checkout succeeded on 2026.07.13.4 outside the "
                "sampled window",
                "Whether discounts expiring mid-checkout can produce the same failure shape",
            ],
            falsification_tests=[
                FalsificationTest(
                    description="Reproduce the failure at the suspect commit, locally only",
                    steps=[
                        "Check out the service repository at commit c7f2e9a",
                        "Run applyDiscount with a session lacking a discount via a unit test",
                        "Record the thrown error",
                    ],
                    expected_if_true="TypeError reading the discount code of undefined",
                    expected_if_false="cartTotal returned unchanged",
                ),
                FalsificationTest(
                    description="Verify the parent commit is unaffected",
                    steps=[
                        "Check out the repository at commit a1e5c30",
                        "Run the same no-discount unit test",
                    ],
                    expected_if_true="the test passes on a1e5c30",
                    expected_if_false="failure predates c7f2e9a and the hypothesis is wrong",
                ),
            ],
            affected_files=["src/checkout.ts", "src/checkout.test.ts"],
            suspect_commit="c7f2e9a",
            rationale=(
                "Deploy timing, the stack-trace location, the no-discount failure pattern, "
                "and the commit diff all point at the same unguarded property access; the "
                "missing no-discount test explains why CI passed."
            ),
        )

        bad_data = RankedHypothesis(
            rank=2,
            statement=(
                "Malformed or expired discount payloads stored in checkout sessions cause "
                "the discount lookup in src/checkout.ts to crash."
            ),
            confidence=0.30,
            supporting=[
                _cite(log, "TypeError raised inside the discount code path"),
                _cite(rate, "error rate jumped abruptly, consistent with data-shaped failures"),
            ],
            contradicting=[
                _cite(
                    samples,
                    "every failure is a session with no discount at all while discounted "
                    "sessions succeed - the opposite of the malformed-discount prediction",
                ),
                _cite(
                    diff,
                    "the c7f2e9a code change alone is sufficient to explain the failures "
                    "without any bad data",
                ),
            ],
            unknowns=[
                "Contents of session-store discount payloads at failure time were not captured"
            ],
            falsification_tests=[
                FalsificationTest(
                    description="Inspect failing session payloads, read-only",
                    steps=[
                        "Pull the 128 failed sessions from the sampled window",
                        "Check each for a discount object and its shape",
                    ],
                    expected_if_true="failing sessions contain malformed discount objects",
                    expected_if_false="failing sessions carry no discount object at all",
                )
            ],
            affected_files=["src/checkout.ts"],
            rationale=(
                "A data-quality regression could raise the same TypeError, but the observed "
                "failure pattern cuts against it."
            ),
        )

        infra = RankedHypothesis(
            rank=3,
            statement=(
                "The 2026.07.13.4 rollout itself (bad instance, configuration, or partial "
                f"rollout) degraded {incident.service}, rather than a code defect."
            ),
            confidence=0.15,
            supporting=[
                _cite(deploy, "deploy at 10:02Z immediately precedes the breach"),
            ],
            contradicting=[
                _cite(
                    log,
                    "failures are a deterministic TypeError at one code location, not "
                    "infrastructure-shaped errors",
                ),
                _cite(samples, "failures key on request shape (no discount), not on host"),
            ],
            unknowns=["Per-instance error distribution was not collected"],
            falsification_tests=[
                FalsificationTest(
                    description="Check error skew across instances, read-only",
                    steps=[
                        "Group the sampled HTTP 500s by serving instance",
                        "Compare per-instance error rates",
                    ],
                    expected_if_true="errors concentrate on a subset of instances",
                    expected_if_false="errors are uniform and keyed to request shape",
                )
            ],
            rationale=(
                "Deploy timing alone permits an infrastructure fault, but the error "
                "signature and request-shaped failure pattern point away from it."
            ),
        )

        code_mapping = CodeMapping(
            affected_files=[
                AffectedFile(
                    path="src/checkout.ts",
                    role=(
                        "Defect site: applyDiscount reads session.discount.code without an "
                        "optional guard"
                    ),
                    citations=[
                        _cite(diff, "commit diff removes the optional guard"),
                        _cite(log, "stack trace lands in applyDiscount"),
                    ],
                ),
                AffectedFile(
                    path="src/checkout.test.ts",
                    role=(
                        "Coverage gap: only discounted sessions are exercised; the failing "
                        "no-discount path is untested"
                    ),
                    citations=[_cite(coverage, "no test for a session without a discount")],
                ),
            ],
            suspect_commit="c7f2e9a",
            commit_citations=[
                _cite(diff, "refactor commit that removed the optional guard"),
                _cite(deploy, "shipped in deploy 2026.07.13.4"),
            ],
            coverage_gap=(
                "src/checkout.test.ts has no test for a session without a discount, so the "
                "c7f2e9a regression passed CI unnoticed."
            ),
            coverage_gap_citations=[_cite(coverage, "test file covers discounted sessions only")],
        )

        return InvestigationDraft(
            status=InvestigationStatus.COMPLETE,
            summary=summary,
            findings=list(findings),
            hypotheses=[top, bad_data, infra],
            code_mapping=code_mapping,
            unknowns=[
                "Whether discounts expiring mid-checkout can reproduce the same failure",
                "No pre-deploy sample of no-discount traffic exists for baseline comparison",
            ],
        )
