from typing import Any

from fastapi.testclient import TestClient

NEW_INCIDENT = {
    "title": "Checkout API elevated 500 errors",
    "service": "checkout-api",
    "environment": "production",
    "severity": "SEV2",
    "summary": "HTTP 500 rate exceeded 12% after deployment.",
    "signal": {"provider": "demo", "signal_type": "error_rate", "payload": {}},
}


def _create_and_start(client: TestClient) -> dict[str, Any]:
    created = client.post("/api/v1/incidents", json=NEW_INCIDENT)
    assert created.status_code == 201
    incident: dict[str, Any] = created.json()
    assert incident["state"] == "RECEIVED"
    assert incident["provider_mode"] == "simulated"

    started = client.post(f"/api/v1/incidents/{incident['id']}/start")
    assert started.status_code == 200
    result: dict[str, Any] = started.json()
    return result


def test_create_rejects_unknown_fields(client: TestClient) -> None:
    response = client.post("/api/v1/incidents", json={**NEW_INCIDENT, "bogus": 1})
    assert response.status_code == 422


def test_create_rejects_invalid_severity(client: TestClient) -> None:
    response = client.post("/api/v1/incidents", json={**NEW_INCIDENT, "severity": "SEV9"})
    assert response.status_code == 422


def test_start_runs_pipeline_to_patch_approval_gate(client: TestClient) -> None:
    incident = _create_and_start(client)
    assert incident["state"] == "WAITING_PATCH_APPROVAL"

    incident_id = incident["id"]
    evidence = client.get(f"/api/v1/incidents/{incident_id}/evidence").json()
    assert len(evidence) == 3
    log_items = [e for e in evidence if e["kind"] == "log"]
    assert log_items[0]["redaction_applied"] is True
    assert "sk-demo1234567890abcdef" not in log_items[0]["content"]
    assert all(e["provenance"].get("simulated") is True for e in evidence)

    timeline = client.get(f"/api/v1/incidents/{incident_id}/timeline").json()
    assert len(timeline) == 3

    hypotheses = client.get(f"/api/v1/incidents/{incident_id}/hypotheses").json()
    assert len(hypotheses) == 1
    assert hypotheses[0]["supporting_evidence_ids"]

    approvals = client.get(f"/api/v1/incidents/{incident_id}/approvals").json()
    assert len(approvals) == 1
    assert approvals[0]["status"] == "pending"
    assert approvals[0]["approval_type"] == "APPLY_PATCH"

    events = client.get(f"/api/v1/incidents/{incident_id}/events").json()
    states = [e["to_state"] for e in events]
    assert states[0] == "RECEIVED"
    assert states[-1] == "WAITING_PATCH_APPROVAL"
    assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))


def test_start_requires_received_state(client: TestClient) -> None:
    incident = _create_and_start(client)
    again = client.post(f"/api/v1/incidents/{incident['id']}/start")
    assert again.status_code == 409


def test_approve_patch_reaches_review_ready(client: TestClient) -> None:
    incident = _create_and_start(client)
    incident_id = incident["id"]
    approval = client.get(f"/api/v1/incidents/{incident_id}/approvals").json()[0]

    decision = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        json={"decision": "approved", "reason": "Bounded workspace patch approved."},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"

    final = client.get(f"/api/v1/incidents/{incident_id}").json()
    assert final["state"] == "REVIEW_READY"

    patches = client.get(f"/api/v1/incidents/{incident_id}/patches").json()
    assert len(patches) == 1
    assert patches[0]["provider_mode"] == "simulated"
    assert "payments/charge.py" in patches[0]["diff"]

    verifications = client.get(f"/api/v1/incidents/{incident_id}/verifications").json()
    assert len(verifications) == 1
    assert verifications[0]["passed"] is True


def test_reject_patch_cancels_incident(client: TestClient) -> None:
    incident = _create_and_start(client)
    incident_id = incident["id"]
    approval = client.get(f"/api/v1/incidents/{incident_id}/approvals").json()[0]

    decision = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        json={"decision": "rejected", "reason": "Too risky right now."},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "rejected"
    assert client.get(f"/api/v1/incidents/{incident_id}").json()["state"] == "CANCELLED"


def test_decided_approval_cannot_be_decided_again(client: TestClient) -> None:
    incident = _create_and_start(client)
    approval = client.get(f"/api/v1/incidents/{incident['id']}/approvals").json()[0]
    first = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        json={"decision": "approved", "reason": "ok"},
    )
    assert first.status_code == 200
    second = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        json={"decision": "approved", "reason": "ok again"},
    )
    assert second.status_code == 409


def test_artifact_version_mismatch_rejected(client: TestClient) -> None:
    incident = _create_and_start(client)
    approval = client.get(f"/api/v1/incidents/{incident['id']}/approvals").json()[0]
    response = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        json={"decision": "approved", "reason": "ok", "artifact_version": 99},
    )
    assert response.status_code == 409


def test_cancel_non_terminal(client: TestClient) -> None:
    created = client.post("/api/v1/incidents", json=NEW_INCIDENT).json()
    cancelled = client.post(f"/api/v1/incidents/{created['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "CANCELLED"
    again = client.post(f"/api/v1/incidents/{created['id']}/cancel")
    assert again.status_code == 409


def test_list_filters(client: TestClient) -> None:
    client.post("/api/v1/incidents", json=NEW_INCIDENT)
    client.post(
        "/api/v1/incidents",
        json={**NEW_INCIDENT, "service": "billing-api", "severity": "SEV3"},
    )
    all_items = client.get("/api/v1/incidents").json()
    assert all_items["total"] >= 3  # golden seed + two created

    filtered = client.get("/api/v1/incidents", params={"service": "billing-api"}).json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["severity"] == "SEV3"

    by_status = client.get("/api/v1/incidents", params={"status": "RECEIVED"}).json()
    assert all(i["state"] == "RECEIVED" for i in by_status["items"])


def test_unknown_incident_404(client: TestClient) -> None:
    assert client.get("/api/v1/incidents/inc-nope").status_code == 404
    assert client.post("/api/v1/incidents/inc-nope/start").status_code == 404


def test_reset_demo_requires_admin_key(client: TestClient) -> None:
    no_key = client.post("/api/v1/incidents/reset-demo")
    assert no_key.status_code == 401

    wrong_key = client.post(
        "/api/v1/incidents/reset-demo", headers={"X-Demo-Admin-Key": "wrong"}
    )
    assert wrong_key.status_code == 401

    ok = client.post(
        "/api/v1/incidents/reset-demo", headers={"X-Demo-Admin-Key": "test-admin-key"}
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["status"] == "reset"
    assert body["seeded_incident_ids"] == ["inc-demo-0001"]

    incidents = client.get("/api/v1/incidents").json()
    assert incidents["total"] == 1
    assert incidents["items"][0]["id"] == "inc-demo-0001"


def test_golden_seed_present_on_startup(client: TestClient) -> None:
    response = client.get("/api/v1/incidents/inc-demo-0001")
    assert response.status_code == 200
    assert response.json()["title"] == "Checkout API elevated 500 errors"
