"""Deterministic simulated remediation planner (M4).

No network, no credentials, no randomness. The fixture planner drafts the
golden checkout-api plan — add the missing no-discount regression test, then
restore the optional discount access commit c7f2e9a removed — naming only the
files the investigation's code mapping identified. The deterministic planning
manager still validates the draft against policy; the fixture earns no trust
for being simulated.
"""

from app.domain.contracts import Incident
from app.domain.investigation import InvestigationReport, InvestigationStatus
from app.domain.remediation import RemediationPlanDraft


class FixtureRemediationPlanner:
    """Deterministic stand-in for a hosted planning model.

    ``model_id`` is environment-driven configuration passed through
    ``Settings``; the fixture output itself never depends on it.
    """

    def __init__(self, model_id: str = "simulated-fixture") -> None:
        self.model_id = model_id

    def propose(self, incident: Incident, report: InvestigationReport) -> RemediationPlanDraft:
        if report.status is not InvestigationStatus.COMPLETE or report.code_mapping is None:
            raise ValueError("the planner requires a COMPLETE investigation with a code mapping")
        mapping = report.code_mapping
        files = sorted(f.path for f in mapping.affected_files)
        return RemediationPlanDraft(
            summary=(
                "Restore optional discount handling in src/checkout.ts and add a "
                "no-discount regression test"
            ),
            files_expected=files,
            steps=[
                "Add a failing regression test in src/checkout.test.ts: applyDiscount "
                "returns the cart total for a session without a discount",
                "Restore optional discount handling in src/checkout.ts: "
                "`session.discount?.code ?? null`",
                "Run the verification commands; make no unrelated refactors",
            ],
            verification_commands=[
                "npm test -- checkout.test.ts",
                "npm test",
                "npm run lint",
                "npm run typecheck",
            ],
            allowed_commands=[
                "git status",
                "git diff",
                "git log",
                "npm test -- checkout.test.ts",
                "npm test",
                "npm run lint",
                "npm run typecheck",
            ],
            max_files_changed=2,
            max_lines_changed=40,
            max_attempts=2,
            timeout_seconds=300,
            network_allowed=False,
            rollback=(
                f"Revert the candidate patch commit; equivalently, revert "
                f"{mapping.suspect_commit} once the regression test is in place. No "
                "production action is taken in this slice."
            ),
            rationale=(
                "The code mapping isolates the defect to the unguarded discount access "
                "in src/checkout.ts and the missing no-discount test in "
                "src/checkout.test.ts; restoring the guard plus one regression test is "
                "the smallest change that fixes the failure and closes the coverage gap."
            ),
        )
