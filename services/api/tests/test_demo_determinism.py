"""Two fresh app instances must produce identical demo pipeline artifacts."""

from typing import Any

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

SETTINGS = Settings(demo_mode=True, demo_admin_key="test", database_url="sqlite:///:memory:")


def _run_golden_path() -> dict[str, Any]:
    app = create_app(SETTINGS)
    with TestClient(app) as client:
        client.post("/api/v1/incidents/inc-demo-0001/start")
        approval = client.get("/api/v1/incidents/inc-demo-0001/approvals").json()[0]
        client.post(
            f"/api/v1/approvals/{approval['id']}/decision",
            json={"decision": "approved", "reason": "golden path"},
        )
        return {
            "state": client.get("/api/v1/incidents/inc-demo-0001").json()["state"],
            "evidence": [
                (
                    e["id"],
                    e["kind"],
                    e["provider"],
                    e["summary"],
                    e["content"],
                    e["content_hash"],
                    e["display_ref"],
                    e["redaction_applied"],
                    tuple(e["redaction_rules"]),
                    e["captured_at"],
                )
                for e in client.get("/api/v1/incidents/inc-demo-0001/evidence").json()
            ],
            "timeline": [
                (t["id"], t["at"], t["kind"], t["description"], t["evidence_id"])
                for t in client.get("/api/v1/incidents/inc-demo-0001/timeline").json()
            ],
            "hypotheses": [
                (h["id"], h["statement"], h["confidence"])
                for h in client.get("/api/v1/incidents/inc-demo-0001/hypotheses").json()
            ],
            "diff": client.get("/api/v1/incidents/inc-demo-0001/patches").json()[0]["diff"],
            "transitions": [
                (e["sequence"], e["from_state"], e["to_state"], e["trigger"])
                for e in client.get("/api/v1/incidents/inc-demo-0001/events").json()
            ],
        }


def test_golden_path_is_deterministic_across_runs() -> None:
    first = _run_golden_path()
    second = _run_golden_path()
    assert first == second
    assert first["state"] == "REVIEW_READY"
