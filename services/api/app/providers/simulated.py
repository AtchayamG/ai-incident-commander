"""Deterministic simulated providers for demo mode.

No network, no credentials, no randomness: identical inputs always produce
identical outputs so the golden demo can be asserted byte-for-byte. Fixture
content is clearly labelled simulated and is never presented as live data.
"""

from datetime import UTC, datetime, timedelta

from app.domain.contracts import Incident, RemediationPlan
from app.domain.enums import EvidenceKind
from app.providers.base import (
    HypothesisProposal,
    PatchProposal,
    PlanProposal,
    PullRequestReceipt,
    RawEvidence,
    VerificationCheckResult,
)

_EPOCH = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

# Fixture log deliberately contains a secret-shaped token so tests can prove
# the redaction boundary is applied before persistence.
_FIXTURE_LOG = (
    "ERROR checkout.payments Charge failed: TypeError: 'NoneType' object is not "
    "subscriptable at payments/charge.py:42 in apply_discount\n"
    "config loaded: api_key=sk-demo1234567890abcdef retries=3"
)

_FIXTURE_DIFF = """\
--- a/payments/charge.py
+++ b/payments/charge.py
@@ -39,7 +39,7 @@ def apply_discount(cart, discount):
-    total = cart["total"] - discount["amount"]
+    total = cart["total"] - (discount["amount"] if discount else 0)
     return max(total, 0)
"""


class SimulatedTelemetryProvider:
    def fetch_evidence(self, incident: Incident) -> list[RawEvidence]:
        base = _EPOCH
        service = incident.service
        return [
            RawEvidence(
                kind=EvidenceKind.METRIC,
                source="simulated:telemetry",
                summary=f"[SIMULATED] HTTP 500 rate on {service} rose from 0.2% to 12.4%",
                content=f"error_rate{{service=\"{service}\"}} 0.124 (baseline 0.002)",
                observed_at=base,
                provenance={"provider": "fixture-telemetry", "simulated": True},
            ),
            RawEvidence(
                kind=EvidenceKind.LOG,
                source="simulated:logs",
                summary=f"[SIMULATED] Recurring TypeError in {service} payment path",
                content=_FIXTURE_LOG,
                observed_at=base + timedelta(minutes=2),
                provenance={"provider": "fixture-telemetry", "simulated": True},
            ),
            RawEvidence(
                kind=EvidenceKind.DEPLOY,
                source="simulated:deploys",
                summary=f"[SIMULATED] Deploy d-4821 of {service} completed 6 minutes before spike",
                content="deploy d-4821 commit 9f3ab21 'refactor discount handling'",
                observed_at=base + timedelta(minutes=4),
                provenance={"provider": "fixture-deploy-history", "simulated": True},
            ),
        ]


class SimulatedInvestigationProvider:
    def propose_hypothesis(
        self, incident: Incident, evidence_summaries: list[str]
    ) -> HypothesisProposal:
        return HypothesisProposal(
            statement=(
                "Deploy d-4821 introduced a discount refactor that dereferences a "
                "missing discount object, causing TypeError and HTTP 500s on "
                f"{incident.service}."
            ),
            confidence=0.85,
            supporting_evidence_indexes=list(range(len(evidence_summaries))),
            contradictions=[],
            unknowns=["Whether any carts have discounts that legitimately expire mid-session"],
        )

    def propose_plan(self, incident: Incident, hypothesis: str) -> PlanProposal:
        return PlanProposal(
            summary="Guard against missing discount object in apply_discount",
            steps=[
                "Add a None-guard for the discount argument in payments/charge.py",
                "Run payment unit tests and lint in the isolated workspace",
            ],
            max_files_changed=1,
            max_lines_changed=10,
        )


class SimulatedCodeAgentGateway:
    def propose_patch(self, incident: Incident, plan: RemediationPlan) -> PatchProposal:
        return PatchProposal(diff=_FIXTURE_DIFF, files_changed=1, lines_changed=2)


class SimulatedVerificationRunner:
    def verify(self, incident: Incident, diff: str) -> list[VerificationCheckResult]:
        return [
            VerificationCheckResult(
                name="unit_tests",
                passed=True,
                detail="[SIMULATED] 24 passed in 1.8s (payments test suite)",
            ),
            VerificationCheckResult(
                name="lint", passed=True, detail="[SIMULATED] ruff: no findings"
            ),
            VerificationCheckResult(
                name="typecheck", passed=True, detail="[SIMULATED] mypy: no issues in 1 file"
            ),
        ]


class SimulatedPullRequestProvider:
    def create_draft_pr(
        self, incident: Incident, diff: str, idempotency_key: str
    ) -> PullRequestReceipt:
        return PullRequestReceipt(
            provider="simulated:github",
            url=f"https://example.invalid/simulated-pr/{incident.id}",
            simulated=True,
            idempotency_key=idempotency_key,
        )
