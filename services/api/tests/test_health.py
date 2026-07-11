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


def test_dependencies_all_simulated_in_demo_mode(client: TestClient) -> None:
    response = client.get("/health/dependencies")
    assert response.status_code == 200
    body = response.json()
    statuses = {d["name"]: d["status"] for d in body["dependencies"]}
    assert statuses["store"] == "in_memory"
    for name in ("database", "redis", "openai", "github"):
        assert statuses[name] == "simulated"
