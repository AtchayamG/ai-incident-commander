import os
import tempfile
import asyncio
from typing import AsyncGenerator
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.config import Settings
from app.main import create_app
from app.domain.enums import WorkflowState

def test_fresh_migration():
    """Verify that alembic upgrade head works on a fresh database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        url = f"sqlite:///{path}"
        alembic_cfg = Config(os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini"))
        alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", url)
        
        # Run the migration
        command.upgrade(alembic_cfg, "head")
        
        # Verify it works by starting the app
        settings = Settings(demo_mode=True, database_url=url)
        app = create_app(settings)
        with TestClient(app) as client:
            res = client.get("/api/v1/incidents")
            assert res.status_code == 200
            assert "total" in res.json()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

def test_restart_persistence(test_db_path):
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

def test_webhook_intake(client):
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

def test_sse_streaming(client):
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
    with client.stream("GET", f"/api/v1/incidents/{inc_id}/events/stream") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        
        # Read the first event
        for line in response.iter_lines():
            if line.startswith("data:"):
                # We got an event!
                assert "webhook" not in line  # just check it parses or has content
                break
