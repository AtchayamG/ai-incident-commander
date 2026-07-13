"""Credential-safe integration inventory and fail-closed test endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_settings
from app.config import Settings
from app.domain.api_contracts import (
    IntegrationStatus,
    IntegrationStatusKind,
    IntegrationTestResult,
)

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


def _inventory(settings: Settings) -> list[IntegrationStatus]:
    providers = (
        ("openai", "structured investigation", settings.openai_api_key_present),
        ("codex", "isolated workspace patching", bool(settings.codex_model)),
        ("github", "draft pull request", settings.github_token_present),
    )
    result: list[IntegrationStatus] = []
    for provider, capability, configured in providers:
        if settings.demo_mode:
            state = IntegrationStatusKind.SIMULATED
        elif configured:
            state = IntegrationStatusKind.CONFIGURED_NOT_PROBED
        else:
            state = IntegrationStatusKind.UNCONFIGURED
        result.append(
            IntegrationStatus(
                provider=provider,
                capability=capability,
                status=state,
                credential_configured=configured,
            )
        )
    return result


@router.get("", response_model=list[IntegrationStatus])
def list_integrations(
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[IntegrationStatus]:
    return _inventory(settings)


@router.post("/{provider}/test", response_model=IntegrationTestResult)
def test_integration(
    provider: str, settings: Annotated[Settings, Depends(get_settings)]
) -> IntegrationTestResult:
    item = next((entry for entry in _inventory(settings) if entry.provider == provider), None)
    if item is None:
        raise HTTPException(status_code=404, detail="unknown integration provider")
    detail = (
        "Demo adapter selected; no external connectivity was attempted."
        if item.status is IntegrationStatusKind.SIMULATED
        else "Connectivity probe is disabled; configuration presence is not proof of connection."
    )
    return IntegrationTestResult(
        provider=provider,
        status=item.status,
        connected=False,
        external_request_made=False,
        detail=detail,
    )
