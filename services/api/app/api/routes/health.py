"""Health endpoints (blueprint section 26.3)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends

from app.api.deps import get_settings, get_sql_store
from app.config import Settings
from app.domain.contracts import (
    DependencyStatus,
    HealthDependencies,
    HealthLive,
    HealthReady,
    HealthWorkers,
    WorkerStatus,
)
from app.runtime import redis_connected, worker_heartbeat
from app.store.sql import SqlAlchemyStore

router = APIRouter(prefix="/health", tags=["health"])
DependencyState = Literal[
    "connected", "configured", "simulated", "not_configured", "unavailable"
]


@router.get("/live", response_model=HealthLive)
def live() -> HealthLive:
    return HealthLive(status="ok")


@router.get("/ready", response_model=HealthReady)
def ready(settings: Annotated[Settings, Depends(get_settings)]) -> HealthReady:
    return HealthReady(
        status="ok",
        demo_mode=settings.demo_mode,
        provider_mode=settings.provider_mode,
    )


@router.get("/dependencies", response_model=HealthDependencies)
def dependencies(
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[SqlAlchemyStore, Depends(get_sql_store)],
) -> HealthDependencies:
    def external(name: str, configured: bool) -> DependencyStatus:
        if settings.demo_mode:
            return DependencyStatus(name=name, status="simulated")
        return DependencyStatus(
            name=name, status="configured" if configured else "not_configured"
        )

    database_ok = store.ping()
    redis_status: DependencyState = (
        "connected"
        if settings.redis_url and redis_connected(settings.redis_url)
        else "unavailable" if settings.redis_url else "not_configured"
    )
    deps = [
        DependencyStatus(name="store", status="connected" if database_ok else "unavailable"),
        DependencyStatus(name="database", status="connected" if database_ok else "unavailable"),
        DependencyStatus(name="redis", status=redis_status),
        external("openai", settings.openai_api_key_present),
        external("github", settings.github_token_present),
    ]
    required_ok = database_ok and (not settings.redis_url or redis_status == "connected")
    return HealthDependencies(status="ok" if required_ok else "degraded", dependencies=deps)


@router.get("/workers", response_model=HealthWorkers)
def workers(settings: Annotated[Settings, Depends(get_settings)]) -> HealthWorkers:
    if not settings.redis_url:
        worker = WorkerStatus(name="workflow", status="not_configured")
    elif heartbeat := worker_heartbeat(settings.redis_url):
        worker = WorkerStatus(name="workflow", status="ready", last_heartbeat_at=heartbeat)
    else:
        worker = WorkerStatus(name="workflow", status="unavailable")
    return HealthWorkers(
        status="ok" if worker.status == "ready" else "degraded",
        workers=[worker],
    )
