"""Health endpoints (blueprint section 26.3)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_settings
from app.config import Settings
from app.domain.contracts import (
    DependencyStatus,
    HealthDependencies,
    HealthLive,
    HealthReady,
)

router = APIRouter(prefix="/health", tags=["health"])


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
) -> HealthDependencies:
    def external(name: str, configured: bool) -> DependencyStatus:
        if settings.demo_mode:
            return DependencyStatus(name=name, status="simulated")
        return DependencyStatus(
            name=name, status="configured" if configured else "not_configured"
        )

    deps = [
        DependencyStatus(name="store", status="in_memory"),
        external("database", settings.database_url is not None),
        external("redis", settings.redis_url is not None),
        external("openai", settings.openai_api_key_present),
        external("github", settings.github_token_present),
    ]
    return HealthDependencies(status="ok", dependencies=deps)
