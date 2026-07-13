from fastapi.testclient import TestClient


def test_live(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_demo_mode(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["demo_mode"] is True
    assert body["provider_mode"] == "simulated"


def test_dependencies_report_real_local_store_and_optional_services(client: TestClient) -> None:
    response = client.get("/health/dependencies")
    assert response.status_code == 200
    body = response.json()
    statuses = {d["name"]: d["status"] for d in body["dependencies"]}
    assert body["status"] == "ok"
    assert statuses["store"] == "connected"
    assert statuses["database"] == "connected"
    assert statuses["redis"] == "not_configured"
    assert statuses["openai"] == "simulated"
    assert statuses["github"] == "simulated"


def test_workers_are_truthfully_not_configured_without_redis(client: TestClient) -> None:
    response = client.get("/health/workers")
    assert response.status_code == 200
    assert response.json() == {
        "status": "degraded",
        "workers": [
            {"name": "workflow", "status": "not_configured", "last_heartbeat_at": None}
        ],
    }
