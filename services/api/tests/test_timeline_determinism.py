"""Timeline ordering: chronological, evidence-linked, deterministic, idempotent."""

from typing import Any

from fastapi.testclient import TestClient

GOLDEN_ID = "inc-demo-0001"
ADMIN = {"X-Demo-Admin-Key": "test-admin-key"}


def _run_and_fetch(client: TestClient) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    assert client.post(f"/api/v1/incidents/{GOLDEN_ID}/start").status_code == 200
    timeline: list[dict[str, Any]] = client.get(
        f"/api/v1/incidents/{GOLDEN_ID}/timeline"
    ).json()
    evidence: list[dict[str, Any]] = client.get(
        f"/api/v1/incidents/{GOLDEN_ID}/evidence"
    ).json()
    return timeline, evidence


def test_timeline_is_chronological_and_linked_to_evidence(client: TestClient) -> None:
    timeline, evidence = _run_and_fetch(client)
    assert len(timeline) == 8

    stamps = [t["at"] for t in timeline]
    assert stamps == sorted(stamps)

    evidence_by_id = {e["id"]: e for e in evidence}
    for event in timeline:
        assert event["evidence_id"] in evidence_by_id
        linked = evidence_by_id[event["evidence_id"]]
        assert event["at"] == linked["captured_at"]
        assert event["kind"] == linked["kind"]
        assert event["description"] == linked["summary"]

    # The causal story reads in order: commit -> deploy -> incident start.
    descriptions = [t["description"] for t in timeline]
    commit_idx = next(i for i, d in enumerate(descriptions) if "Commit c7f2e9a" in d)
    deploy_idx = next(i for i, d in enumerate(descriptions) if "Version 2026.07.13.4" in d)
    start_idx = next(i for i, d in enumerate(descriptions) if "Incident start" in d)
    assert commit_idx < deploy_idx < start_idx


def test_timeline_and_evidence_stable_across_reset_and_rerun(client: TestClient) -> None:
    """reset-demo + start is idempotent: identical IDs, order, hashes, stamps."""

    def snapshot() -> dict[str, Any]:
        timeline, evidence = _run_and_fetch(client)
        return {
            "timeline": [
                (t["id"], t["at"], t["kind"], t["description"], t["evidence_id"])
                for t in timeline
            ],
            "evidence": [
                (e["id"], e["captured_at"], e["content_hash"], e["display_ref"])
                for e in evidence
            ],
        }

    first = snapshot()
    reset = client.post("/api/v1/incidents/reset-demo", headers=ADMIN)
    assert reset.status_code == 200
    assert reset.json()["seeded_incident_ids"] == [GOLDEN_ID]
    second = snapshot()
    assert first == second


def test_repeated_reset_is_idempotent(client: TestClient) -> None:
    first = client.post("/api/v1/incidents/reset-demo", headers=ADMIN).json()
    second = client.post("/api/v1/incidents/reset-demo", headers=ADMIN).json()
    assert first == second
    incidents = client.get("/api/v1/incidents").json()
    assert incidents["total"] == 1
    assert incidents["items"][0]["state"] == "RECEIVED"
