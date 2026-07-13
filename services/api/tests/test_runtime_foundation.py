from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.runtime import WORKER_KEY, redis_connected, run_worker, worker_heartbeat
from app.store.sql import SqlAlchemyStore


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.closed = False

    def ping(self) -> bool:
        return True

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.values[key] = value

    def close(self) -> None:
        self.closed = True


def test_store_ping_and_sqlite_startup_remain_supported() -> None:
    store = SqlAlchemyStore("sqlite:///:memory:")
    assert store.ping() is True
    with TestClient(create_app(Settings(database_url="sqlite:///:memory:"))) as client:
        assert client.get("/health/live").json() == {"status": "ok"}


def test_redis_connectivity_and_worker_heartbeat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeRedis()
    monkeypatch.setattr("app.runtime.redis_client", lambda _url: fake)
    assert redis_connected("redis://test") is True

    def stop_after_first_heartbeat(_seconds: float) -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_worker("redis://test", sleep=stop_after_first_heartbeat)

    heartbeat = worker_heartbeat("redis://test")
    assert heartbeat is not None
    assert heartbeat.tzinfo == UTC
    assert WORKER_KEY in fake.values


def test_health_reports_connected_dependencies_and_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    monkeypatch.setattr("app.api.routes.health.redis_connected", lambda _url: True)
    monkeypatch.setattr("app.api.routes.health.worker_heartbeat", lambda _url: now)
    settings = Settings(database_url="sqlite:///:memory:", redis_url="redis://test")
    with TestClient(create_app(settings)) as client:
        dependency_body: dict[str, Any] = client.get("/health/dependencies").json()
        statuses = {item["name"]: item["status"] for item in dependency_body["dependencies"]}
        assert dependency_body["status"] == "ok"
        assert statuses["database"] == "connected"
        assert statuses["redis"] == "connected"
        worker_body = client.get("/health/workers").json()
        assert worker_body["status"] == "ok"
        assert worker_body["workers"][0]["status"] == "ready"
