import hashlib
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.enums import WorkflowState
from app.store.sql import SqlAlchemyStore

NEW_INCIDENT = {
    "title": "Checkout API elevated 500 errors",
    "service": "checkout-api",
    "environment": "production",
    "severity": "SEV2",
    "summary": "HTTP 500 rate exceeded 12% after deployment.",
    "signal": {"provider": "demo", "signal_type": "error_rate", "payload": {}},
}


def _start(client: TestClient) -> dict[str, Any]:
    created = client.post("/api/v1/incidents", json=NEW_INCIDENT)
    assert created.status_code == 201
    response = client.post(f"/api/v1/incidents/{created.json()['id']}/start")
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def _approve_patch(client: TestClient, incident_id: str) -> None:
    approval = client.get(f"/api/v1/incidents/{incident_id}/approvals").json()[0]
    response = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        json={"decision": "approved", "reason": "Approve bounded patch."},
    )
    assert response.status_code == 200


def test_manual_evidence_is_redacted_hashed_and_provenanced(client: TestClient) -> None:
    incident = _start(client)
    raw = "failure token=super-secret-value email=operator@example.com"
    response = client.post(
        f"/api/v1/incidents/{incident['id']}/evidence",
        json={
            "kind": "log",
            "source": "operator-console",
            "summary": "Manual reproduction",
            "content": raw,
            "display_ref": "console://manual/1",
            "captured_at": "2026-07-13T12:00:00Z",
            "origin": "incident-commander",
        },
    )
    assert response.status_code == 201
    item = response.json()
    assert "super-secret-value" not in item["content"]
    assert "operator@example.com" not in item["content"]
    assert item["redaction_applied"] is True
    assert item["provider"] == "manual"
    assert item["provenance"] == {
        "manual": True,
        "origin": "incident-commander",
        "simulated": False,
    }
    expected = hashlib.sha256(item["content"].encode()).hexdigest()
    assert item["content_hash"] == f"sha256:{expected}"


def test_hypothesis_feedback_is_strict_and_audited(client: TestClient) -> None:
    incident = _start(client)
    hypotheses = client.get(
        f"/api/v1/incidents/{incident['id']}/hypotheses"
    ).json()
    hypothesis_id = hypotheses[0]["id"]
    response = client.post(
        f"/api/v1/incidents/{incident['id']}/hypotheses/{hypothesis_id}/feedback",
        json={"feedback": "confirmed", "reason": "Matches the reproduction."},
    )
    assert response.status_code == 200
    assert response.json()["feedback"] == "confirmed"
    invalid = client.post(
        f"/api/v1/incidents/{incident['id']}/hypotheses/{hypothesis_id}/feedback",
        json={"feedback": "maybe", "reason": "ambiguous"},
    )
    assert invalid.status_code == 422
    timeline = client.get(f"/api/v1/incidents/{incident['id']}/timeline").json()
    assert timeline[-1]["kind"] == "hypothesis_feedback"


def test_plan_revision_creates_new_hashed_version(client: TestClient) -> None:
    incident = _start(client)
    current = client.get(
        f"/api/v1/incidents/{incident['id']}/remediation-plan/artifact"
    ).json()
    response = client.post(
        f"/api/v1/incidents/{incident['id']}/remediation-plan/revise",
        json={
            "reason": "Clarify rollback for review.",
            "summary": "Guard optional discount access and retain the regression test.",
            "rollback": "Revert the candidate patch in the isolated workspace.",
        },
    )
    assert response.status_code == 200
    revised = response.json()
    assert revised["version"] == current["version"] + 1
    assert revised["id"] != current["id"]
    assert revised["artifact_hash"] != current["artifact_hash"]


def test_patch_diff_and_verification_are_addressable_by_patch_id(client: TestClient) -> None:
    incident = _start(client)
    _approve_patch(client, incident["id"])
    patch = client.get(f"/api/v1/incidents/{incident['id']}/patches").json()[0]
    diff = client.get(f"/api/v1/patches/{patch['id']}/diff")
    assert diff.status_code == 200
    assert diff.json()["unified_diff"] == patch["diff"]
    assert diff.json()["diff_hash"].startswith("sha256:")
    verification = client.get(f"/api/v1/patches/{patch['id']}/verification")
    assert verification.status_code == 200
    assert verification.json()["patch_id"] == patch["id"]
    assert verification.json()["passed"] is True


def test_patch_retry_validates_state_and_reopens_approval_gate(client: TestClient) -> None:
    incident = _start(client)
    _approve_patch(client, incident["id"])
    patch = client.get(f"/api/v1/incidents/{incident['id']}/patches").json()[0]
    wrong_state = client.post(
        f"/api/v1/patches/{patch['id']}/retry", json={"reason": "Retry."}
    )
    assert wrong_state.status_code == 409

    app = cast(FastAPI, client.app)
    store = cast(SqlAlchemyStore, app.state.store)
    store.set_incident_state(incident["id"], WorkflowState.PATCH_FAILED)
    accepted = client.post(
        f"/api/v1/patches/{patch['id']}/retry",
        json={"reason": "Retry after deterministic patch failure."},
    )
    assert accepted.status_code == 200
    body = accepted.json()
    assert body["accepted"] is True
    assert body["state"] == "WAITING_PATCH_APPROVAL"
    assert body["attempts_remaining"] >= 1


def test_integration_inventory_and_tests_never_claim_connectivity(client: TestClient) -> None:
    response = client.get("/api/v1/integrations")
    assert response.status_code == 200
    inventory = response.json()
    assert {item["provider"] for item in inventory} == {"openai", "codex", "github"}
    assert all(item["status"] == "simulated" for item in inventory)
    assert all(item["external_request_made"] is False for item in inventory)

    for provider in ("openai", "codex", "github"):
        probe = client.post(f"/api/v1/integrations/{provider}/test")
        assert probe.status_code == 200
        result = probe.json()
        assert result["connected"] is False
        assert result["external_request_made"] is False
        assert "token" not in result and "credential" not in result


def test_contract_actions_reject_unknown_fields(client: TestClient) -> None:
    incident = _start(client)
    response = client.post(
        f"/api/v1/incidents/{incident['id']}/evidence",
        json={
            "kind": "log",
            "source": "manual",
            "summary": "summary",
            "content": "content",
            "display_ref": "manual:1",
            "captured_at": "2026-07-13T12:00:00Z",
            "secret": "must not be accepted",
        },
    )
    assert response.status_code == 422
