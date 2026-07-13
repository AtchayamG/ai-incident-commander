"""Deterministic performance and resilience contract checks from blueprint section 24."""

from __future__ import annotations

import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_fifty_concurrent_incident_reads(client: TestClient) -> None:
    with ThreadPoolExecutor(max_workers=10) as pool:
        responses = list(
            pool.map(lambda _: client.get("/api/v1/incidents/inc-demo-0001"), range(50))
        )

    assert len(responses) == 50
    assert all(response.status_code == 200 for response in responses)


def _start_isolated_workflow(index: int, root: Path) -> str:
    app = create_app(
        Settings(
            demo_mode=True,
            demo_admin_key="performance-test",
            database_url=f"sqlite:///{(root / f'workflow-{index}.db').as_posix()}",
            code_agent_engine="fixture",
        )
    )
    try:
        with TestClient(app) as client:
            reset = client.post(
                "/api/v1/incidents/reset-demo",
                headers={"X-Demo-Admin-Key": "performance-test"},
            )
            assert reset.status_code == 200
            started = client.post("/api/v1/incidents/inc-demo-0001/start")
            assert started.status_code == 200
            return str(started.json()["state"])
    finally:
        app.state.store.engine.dispose()


def test_ten_simultaneous_isolated_workflows_reach_approval_gate() -> None:
    with tempfile.TemporaryDirectory(prefix="incident-concurrency-") as directory:
        root = Path(directory)
        with ThreadPoolExecutor(max_workers=10) as pool:
            states = list(pool.map(lambda index: _start_isolated_workflow(index, root), range(10)))

    assert states == ["WAITING_PATCH_APPROVAL"] * 10


def test_oversized_log_summary_is_rejected_at_request_boundary(client: TestClient) -> None:
    response = client.post(
        "/api/v1/incidents",
        json={
            "title": "Oversized log payload",
            "service": "checkout-api",
            "environment": "production",
            "severity": "SEV1",
            "summary": "x" * 2_000_000,
            "signal": {"provider": "load-test", "signal_type": "logs", "payload": {}},
        },
    )

    assert response.status_code == 422


def _sse_data(client: TestClient) -> list[str]:
    with client.stream(
        "GET", "/api/v1/incidents/inc-demo-0001/events/stream?once=true"
    ) as response:
        assert response.status_code == 200
        return [line for line in response.iter_lines() if line.startswith("data:")]


def test_sse_reconnect_replays_persisted_events(client: TestClient) -> None:
    assert client.post("/api/v1/incidents/inc-demo-0001/start").status_code == 200
    first = _sse_data(client)
    replay = _sse_data(client)

    assert first
    assert replay == first
