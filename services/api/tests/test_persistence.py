import contextlib
import os
import tempfile

from alembic.config import Config
from fastapi.testclient import TestClient

from alembic import command
from app.config import Settings
from app.domain.enums import WorkflowState
from app.main import create_app


def test_fresh_migration() -> None:
    """Verify that alembic upgrade head works on a fresh database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        url = f"sqlite:///{path}"
        base_dir = os.path.dirname(os.path.dirname(__file__))
        alembic_cfg = Config(os.path.join(base_dir, "alembic.ini"))
        alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", url)

        # Run the migration
        command.upgrade(alembic_cfg, "head")

        # Verify it works by starting the app and exercising the M2 evidence
        # columns against the migrated schema (no create_all shortcuts).
        settings = Settings(demo_mode=True, database_url=url)
        app = create_app(settings)
        with TestClient(app) as client:
            res = client.get("/api/v1/incidents")
            assert res.status_code == 200
            assert "total" in res.json()

            assert client.post("/api/v1/incidents/inc-demo-0001/start").status_code == 200
            evidence = client.get("/api/v1/incidents/inc-demo-0001/evidence").json()
            assert len(evidence) == 8
            for item in evidence:
                assert item["content_hash"].startswith("sha256:")
                assert item["provider"]
                assert item["display_ref"]
                assert item["captured_at"]

            # The M3 investigation_reports table was created by the migration
            # (no create_all shortcut) and the report persists and reads back.
            report = client.get("/api/v1/incidents/inc-demo-0001/investigation")
            assert report.status_code == 200
            assert report.json()["status"] == "complete"
            assert report.json()["remediation_enabled"] is True
    finally:
        with contextlib.suppress(OSError):
            os.unlink(path)

def test_restart_persistence(test_db_path: str) -> None:
    """Test that data survives an app restart (recreating the app with same DB)."""
    settings = Settings(demo_mode=True, demo_admin_key="test-admin-key", database_url=f"sqlite:///{test_db_path}")

    # Run once
    app1 = create_app(settings)
    with TestClient(app1) as client1:
        client1.post("/api/v1/incidents/reset-demo", headers={"X-Demo-Admin-Key": "test-admin-key"})
        res = client1.post("/api/v1/incidents", json={
            "title": "Test Persistence",
            "service": "test",
            "environment": "production",
            "severity": "SEV1",
            "summary": "This is a test."
        })
        assert res.status_code == 201
        inc_id = res.json()["id"]

    # Run again, simulating process restart
    app2 = create_app(settings)
    with TestClient(app2) as client2:
        res2 = client2.get(f"/api/v1/incidents/{inc_id}")
        assert res2.status_code == 200
        assert res2.json()["title"] == "Test Persistence"

def test_webhook_intake(client: TestClient) -> None:
    """Test generic JSON webhook intake with safe demo behavior."""
    payload = {
        "title": "Webhook Trigger",
        "service": "payment-api",
        "summary": "Some random alert"
    }
    # In demo mode, no signature is required
    res = client.post("/api/v1/incidents/webhook", json=payload)
    assert res.status_code == 201

    data = res.json()
    assert data["title"] == "Webhook Trigger"
    assert data["service"] == "payment-api"
    assert data["state"] == WorkflowState.RECEIVED.value

def test_sse_streaming(client: TestClient) -> None:
    """Test SSE streaming of workflow events."""
    # Reset and seed to have at least one incident
    client.post("/api/v1/incidents/reset-demo", headers={"X-Demo-Admin-Key": "test-admin-key"})

    res = client.post("/api/v1/incidents", json={
        "title": "SSE Test",
        "service": "test",
        "environment": "production",
        "severity": "SEV1",
        "summary": "This is a test."
    })
    inc_id = res.json()["id"]

    # We use TestClient which is synchronous, but httpx can read streams
    with client.stream(
        "GET", f"/api/v1/incidents/{inc_id}/events/stream?once=true"
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        for line in response.iter_lines():
            if line.startswith("data:"):
                # We got an event!
                assert "webhook" not in line  # just check it parses or has content
                break
            if "ping" in line:
                break
