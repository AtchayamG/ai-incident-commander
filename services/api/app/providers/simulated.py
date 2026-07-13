"""Deterministic simulated providers for demo mode.

No network, no credentials, no randomness: identical inputs always produce
identical outputs so the golden demo can be asserted byte-for-byte. Evidence
content comes from the checkout-api fixture repository under ``fixtures/``
(blueprint section 32); everything is clearly labelled simulated and is never
presented as live data.

The fixture error log deliberately contains secret-shaped tokens so tests can
prove the redaction boundary is applied before persistence.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.domain.contracts import Incident
from app.domain.enums import EvidenceKind
from app.providers.base import (
    HypothesisProposal,
    PlanProposal,
    PullRequestReceipt,
    RawEvidence,
)

FIXTURE_SERVICE = "checkout-api"


def default_fixtures_root() -> Path:
    """Locate the fixtures directory.

    Order: explicit ``FIXTURES_DIR`` env var, the ``fixtures`` directory next
    to the ``app`` package (services/api/fixtures locally, /srv/fixtures in
    the container), then ``fixtures`` under the current working directory.
    """
    candidates: list[Path] = []
    env_dir = os.environ.get("FIXTURES_DIR")
    if env_dir:
        candidates.append(Path(env_dir))
    candidates.append(Path(__file__).resolve().parents[2] / "fixtures")
    candidates.append(Path.cwd() / "fixtures")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    searched = ", ".join(str(c) for c in candidates)
    raise FileNotFoundError(f"fixtures directory not found; searched: {searched}")


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


class _FixtureFiles:
    """Read access to the checkout-api fixture repository."""

    def __init__(self, fixtures_root: Path | None = None) -> None:
        root = fixtures_root or default_fixtures_root()
        self.root = root / FIXTURE_SERVICE

    def text(self, relative: str) -> str:
        return (self.root / relative).read_text(encoding="utf-8")

    def json(self, relative: str) -> Any:
        return json.loads(self.text(relative))

    def ref(self, relative: str) -> str:
        return f"simulated://{FIXTURE_SERVICE}/{relative}"

    def provenance(self, relative: str, **extra: Any) -> dict[str, Any]:
        return {
            "simulated": True,
            "fixture_path": f"fixtures/{FIXTURE_SERVICE}/{relative}",
            **extra,
        }


class SimulatedTelemetryProvider:
    """Alert rates, incident start, stack-trace and no-discount error samples."""

    provider_id = "fixture-telemetry"

    def __init__(self, fixtures_root: Path | None = None) -> None:
        self._files = _FixtureFiles(fixtures_root)

    def fetch_evidence(self, incident: Incident) -> list[RawEvidence]:
        service = incident.service
        alert = self._files.json("telemetry/alerts.json")["alert"]
        analysis = self._files.json("telemetry/samples_analysis.json")
        error_log = self._files.text("telemetry/error_samples.log")
        baseline = alert["baseline_rate"] * 100
        observed = alert["observed_rate"] * 100
        return [
            RawEvidence(
                kind=EvidenceKind.METRIC,
                provider=self.provider_id,
                source="simulated:alerts",
                summary=(
                    f"[SIMULATED] Incident start {alert['incident_start']}: HTTP 500 "
                    f"rate breached the {alert['threshold'] * 100:.1f}% threshold on {service}"
                ),
                content=json.dumps(alert, indent=2, sort_keys=True),
                display_ref=self._files.ref("telemetry/alerts.json"),
                observed_at=_parse_utc(alert["incident_start"]),
                provenance=self._files.provenance(
                    "telemetry/alerts.json", provider=self.provider_id
                ),
            ),
            RawEvidence(
                kind=EvidenceKind.METRIC,
                provider=self.provider_id,
                source="simulated:alerts",
                summary=(
                    f"[SIMULATED] HTTP 500 rate on {service} rose from "
                    f"{baseline:.1f}% to {observed:.1f}%"
                ),
                content=(
                    f'error_rate{{service="{service}"}} {alert["observed_rate"]} '
                    f"(baseline {alert['baseline_rate']})"
                ),
                display_ref=self._files.ref("telemetry/alerts.json"),
                observed_at=_parse_utc(alert["observed_at"]),
                provenance=self._files.provenance(
                    "telemetry/alerts.json", provider=self.provider_id
                ),
            ),
            RawEvidence(
                kind=EvidenceKind.LOG,
                provider=self.provider_id,
                source="simulated:logs",
                summary=(
                    f"[SIMULATED] Recurring TypeError in {service}: stack trace points "
                    "at src/checkout.ts applyDiscount"
                ),
                content=error_log,
                display_ref=self._files.ref("telemetry/error_samples.log"),
                observed_at=_parse_utc("2026-07-13T10:06:12Z"),
                provenance=self._files.provenance(
                    "telemetry/error_samples.log", provider=self.provider_id
                ),
            ),
            RawEvidence(
                kind=EvidenceKind.LOG,
                provider=self.provider_id,
                source="simulated:logs",
                summary=(
                    f"[SIMULATED] All {analysis['failed_requests']} failed requests on "
                    f"{service} are sessions without a discount; discounted sessions succeed"
                ),
                content=json.dumps(analysis, indent=2, sort_keys=True),
                display_ref=self._files.ref("telemetry/samples_analysis.json"),
                observed_at=_parse_utc(analysis["observed_at"]),
                provenance=self._files.provenance(
                    "telemetry/samples_analysis.json", provider=self.provider_id
                ),
            ),
        ]


class SimulatedDeploymentHistoryProvider:
    """Deployment/version evidence plus the correlated regressing commit."""

    provider_id = "fixture-deploy-history"

    def __init__(self, fixtures_root: Path | None = None) -> None:
        self._files = _FixtureFiles(fixtures_root)

    def fetch_evidence(self, incident: Incident) -> list[RawEvidence]:
        service = incident.service
        deploys = self._files.json("deploys/deploys.json")
        latest = deploys[-1]
        commits = self._files.json("repo/history/commits.json")
        regressing = next(c for c in commits if c["sha"] == latest["commit"])
        diff_artifact = f"repo/history/{regressing['diff_artifact']}"
        diff = self._files.text(diff_artifact)
        return [
            RawEvidence(
                kind=EvidenceKind.DEPLOY,
                provider=self.provider_id,
                source="simulated:deploys",
                summary=(
                    f"[SIMULATED] Version {latest['version']} of {service} deployed at "
                    f"{latest['deployed_at']}, 3 minutes before incident start"
                ),
                content=json.dumps(deploys, indent=2, sort_keys=True),
                display_ref=self._files.ref("deploys/deploys.json"),
                observed_at=_parse_utc(latest["deployed_at"]),
                provenance=self._files.provenance(
                    "deploys/deploys.json",
                    provider=self.provider_id,
                    version=latest["version"],
                ),
            ),
            RawEvidence(
                kind=EvidenceKind.DIFF,
                provider=self.provider_id,
                source="simulated:commits",
                summary=(
                    f"[SIMULATED] Commit {regressing['sha']} at {regressing['authored_at']} "
                    "modified discount handling in src/checkout.ts and shipped in "
                    f"{latest['version']}"
                ),
                content=diff,
                display_ref=self._files.ref(diff_artifact),
                observed_at=_parse_utc(regressing["authored_at"]),
                provenance=self._files.provenance(
                    diff_artifact,
                    provider=self.provider_id,
                    commit=regressing["sha"],
                ),
            ),
        ]


class SimulatedLocalRepositoryProvider:
    """Source/test inspection of the fixture checkout-api repository."""

    provider_id = "fixture-local-repo"

    def __init__(self, fixtures_root: Path | None = None) -> None:
        self._files = _FixtureFiles(fixtures_root)

    def fetch_evidence(self, incident: Incident) -> list[RawEvidence]:
        tests = self._files.text("repo/src/checkout.test.ts")
        return [
            RawEvidence(
                kind=EvidenceKind.CONFIG,
                provider=self.provider_id,
                source="simulated:repo",
                summary=(
                    "[SIMULATED] Test coverage gap: checkout.test.ts covers discounted "
                    "sessions only; no test exercises a session without a discount"
                ),
                content=tests,
                display_ref=self._files.ref("repo/src/checkout.test.ts"),
                observed_at=_parse_utc("2026-07-13T10:10:00Z"),
                provenance=self._files.provenance(
                    "repo/src/checkout.test.ts", provider=self.provider_id
                ),
            ),
        ]


class SimulatedRunbookProvider:
    """Operator runbook guidance for the affected service."""

    provider_id = "fixture-runbook"

    def __init__(self, fixtures_root: Path | None = None) -> None:
        self._files = _FixtureFiles(fixtures_root)

    def fetch_evidence(self, incident: Incident) -> list[RawEvidence]:
        runbook = self._files.text("runbooks/checkout-api.txt")
        return [
            RawEvidence(
                kind=EvidenceKind.MANUAL,
                provider=self.provider_id,
                source="simulated:runbook",
                summary=(
                    "[SIMULATED] Runbook: check deployment correlation first, then "
                    "reproduce the failing request locally before patching"
                ),
                content=runbook,
                display_ref=self._files.ref("runbooks/checkout-api.txt"),
                observed_at=_parse_utc("2026-07-13T10:11:00Z"),
                provenance=self._files.provenance(
                    "runbooks/checkout-api.txt", provider=self.provider_id
                ),
            ),
        ]


class SimulatedInvestigationProvider:
    def propose_hypothesis(
        self, incident: Incident, evidence_summaries: list[str]
    ) -> HypothesisProposal:
        return HypothesisProposal(
            statement=(
                "Deploy 2026.07.13.4 shipped commit c7f2e9a, which replaced the safe "
                "optional discount access with unsafe `session.discount.code` in "
                "src/checkout.ts; sessions without a discount throw TypeError and "
                f"return HTTP 500 on {incident.service}."
            ),
            confidence=0.85,
            supporting_evidence_indexes=list(range(len(evidence_summaries))),
            contradictions=[],
            unknowns=["Whether any sessions carry discounts that expire mid-checkout"],
        )

    def propose_plan(self, incident: Incident, hypothesis: str) -> PlanProposal:
        return PlanProposal(
            summary="Restore optional discount access in checkout.ts and add a regression test",
            steps=[
                "Add a regression test for a checkout session without a discount",
                "Restore optional handling: `session.discount?.code ?? null`",
                "Run targeted checkout tests, then the complete suite with lint/typecheck",
            ],
            max_files_changed=2,
            max_lines_changed=40,
        )


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
