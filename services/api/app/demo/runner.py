"""Portable golden-demo runner and assertion CLI.

The runner always constructs an ephemeral demo-mode application. It performs
both human approval decisions through the public HTTP API, then asserts the
truthful simulated resolution artifacts. No external credential is read or
external action is attempted.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from app.config import Settings
from app.demo.seed import GOLDEN_INCIDENT_ID
from app.main import create_app
from app.store.sql import SqlAlchemyStore


def _object(response_json: Any) -> Mapping[str, Any]:
    if not isinstance(response_json, dict):
        raise AssertionError("expected a JSON object")
    return cast(Mapping[str, Any], response_json)


def _list(response_json: Any) -> list[Mapping[str, Any]]:
    if not isinstance(response_json, list) or not all(
        isinstance(item, dict) for item in response_json
    ):
        raise AssertionError("expected a JSON object list")
    return cast(list[Mapping[str, Any]], response_json)


def _approve(client: TestClient, approval: Mapping[str, Any], reason: str) -> None:
    response = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        json={"decision": "approved", "reason": reason},
    )
    response.raise_for_status()


def run_once(database_url: str) -> dict[str, object]:
    """Run and assert one complete deterministic demo workflow."""
    app = create_app(
        Settings(
            demo_mode=True,
            demo_admin_key="demo-runner",
            database_url=database_url,
            code_agent_engine="fixture",
        )
    )
    store = cast(SqlAlchemyStore, app.state.store)
    try:
        with TestClient(app) as client:
            reset = client.post(
                "/api/v1/incidents/reset-demo",
                headers={"X-Demo-Admin-Key": "demo-runner"},
            )
            reset.raise_for_status()

            start = client.post(f"/api/v1/incidents/{GOLDEN_INCIDENT_ID}/start")
            start.raise_for_status()
            approvals = _list(
                client.get(f"/api/v1/incidents/{GOLDEN_INCIDENT_ID}/approvals").json()
            )
            patch_approval = next(
                approval for approval in approvals if approval["approval_type"] == "APPLY_PATCH"
            )
            _approve(client, patch_approval, "Approve the exact bounded demo patch")

            approvals = _list(
                client.get(f"/api/v1/incidents/{GOLDEN_INCIDENT_ID}/approvals").json()
            )
            pr_approvals = [
                approval
                for approval in approvals
                if approval["approval_type"] == "CREATE_DRAFT_PR"
            ]
            if len(pr_approvals) != 1:
                raise AssertionError("expected exactly one draft-PR approval")
            _approve(client, pr_approvals[0], "Approve one simulated offline draft-PR artifact")

            incident = _object(client.get(f"/api/v1/incidents/{GOLDEN_INCIDENT_ID}").json())
            draft_pr = _object(
                client.get(f"/api/v1/incidents/{GOLDEN_INCIDENT_ID}/draft-pr").json()
            )
            communications = _object(
                client.get(f"/api/v1/incidents/{GOLDEN_INCIDENT_ID}/communications").json()
            )
            postmortem = _object(
                client.get(f"/api/v1/incidents/{GOLDEN_INCIDENT_ID}/postmortem").json()
            )

            if incident["state"] != "RESOLUTION_DRAFTED":
                raise AssertionError(f"unexpected final state: {incident['state']}")
            if draft_pr["status"] != "completed" or draft_pr["provider_mode"] != "simulated":
                raise AssertionError("draft PR must be completed by the simulated provider")
            if not communications.get("technical_update") or not communications.get(
                "stakeholder_update"
            ):
                raise AssertionError("communications drafts are missing")
            if not postmortem.get("timeline_json") or not postmortem.get("markdown_content"):
                raise AssertionError("evidence-linked postmortem is missing")

            result: dict[str, object] = {
                "incident_id": GOLDEN_INCIDENT_ID,
                "state": incident["state"],
                "provider_mode": draft_pr["provider_mode"],
                "approval_count": len(approvals),
                "postmortem_timeline_events": len(
                    cast(list[object], postmortem["timeline_json"])
                ),
            }
    finally:
        store.engine.dispose()
    return result


def run_many(runs: int) -> list[dict[str, object]]:
    if runs < 1:
        raise ValueError("runs must be at least 1")
    results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="incident-commander-demo-") as directory:
        root = Path(directory)
        for index in range(runs):
            database_url = f"sqlite:///{(root / f'run-{index + 1}.db').as_posix()}"
            results.append(run_once(database_url))
    return results


def reset_once() -> dict[str, object]:
    """Exercise the protected reset endpoint against an ephemeral demo store."""
    with tempfile.TemporaryDirectory(prefix="incident-commander-reset-") as directory:
        database_url = f"sqlite:///{(Path(directory) / 'reset.db').as_posix()}"
        app = create_app(
            Settings(
                demo_mode=True,
                demo_admin_key="demo-runner",
                database_url=database_url,
                code_agent_engine="fixture",
            )
        )
        store = cast(SqlAlchemyStore, app.state.store)
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/incidents/reset-demo",
                    headers={"X-Demo-Admin-Key": "demo-runner"},
                )
                response.raise_for_status()
                incident = _object(
                    client.get(f"/api/v1/incidents/{GOLDEN_INCIDENT_ID}").json()
                )
                if incident["state"] != "RECEIVED":
                    raise AssertionError("reset demo incident must be in RECEIVED state")
                result: dict[str, object] = {
                    "incident_id": GOLDEN_INCIDENT_ID,
                    "state": incident["state"],
                    "provider_mode": incident["provider_mode"],
                }
        finally:
            store.engine.dispose()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run and assert the golden incident demo")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--reset-only", action="store_true")
    args = parser.parse_args()
    if args.reset_only:
        print(json.dumps({"reset": True, "result": reset_once()}, indent=2))
        return
    results = run_many(args.runs)
    print(json.dumps({"runs": len(results), "passed": True, "results": results}, indent=2))


if __name__ == "__main__":
    main()
