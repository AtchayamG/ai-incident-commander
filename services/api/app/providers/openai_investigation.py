"""Optional OpenAI Responses gateway for typed investigation synthesis.

Demo mode never constructs this adapter. The gateway receives only persisted,
redacted evidence, requests a strict ``InvestigationDraft``, and returns a
proposal that the deterministic ``InvestigationManager`` citation-validates.
"""

from __future__ import annotations

import json
from typing import Any, Protocol, cast

from app.config import Settings
from app.domain.contracts import EvidenceItem, Incident
from app.domain.investigation import InvestigationDraft, SpecialistFinding
from app.providers.base import InvestigationGateway
from app.providers.simulated_investigation import FixtureInvestigationGateway
from app.security.redaction import redact

_MAX_EVIDENCE_ITEMS = 40
_MAX_FINDINGS = 40
_MAX_CONTENT_CHARS = 2_000


class InvestigationProviderError(RuntimeError):
    """Safe, typed failure at the hosted investigation boundary."""


class InvestigationProviderUnavailableError(InvestigationProviderError):
    """The explicitly selected provider is not configured or reachable."""


class InvestigationProviderResponseError(InvestigationProviderError):
    """The provider returned no schema-valid investigation draft."""


class _ResponsesApi(Protocol):
    def parse(self, **kwargs: Any) -> object: ...


class _OpenAIClient(Protocol):
    responses: _ResponsesApi


def _safe(value: str, limit: int = _MAX_CONTENT_CHARS) -> str:
    return redact(value).content[:limit]


class OpenAIInvestigationGateway:
    """Synchronous Responses API adapter with Pydantic structured output."""

    def __init__(
        self,
        model_id: str,
        timeout_seconds: int = 30,
        client: _OpenAIClient | None = None,
    ) -> None:
        if not model_id or model_id == "simulated-fixture":
            raise InvestigationProviderUnavailableError(
                "a configured OpenAI investigation model is required"
            )
        if timeout_seconds < 1:
            raise InvestigationProviderUnavailableError("OpenAI timeout must be positive")
        self.model_id = model_id
        self._timeout_seconds = timeout_seconds
        if client is not None:
            self._client = client
            return
        try:
            from openai import OpenAI

            self._client = cast(_OpenAIClient, OpenAI())
        except Exception as exc:
            detail = _safe(str(exc), 500)
            raise InvestigationProviderUnavailableError(
                f"OpenAI client initialization failed: {detail}"
            ) from exc

    def synthesize(
        self,
        incident: Incident,
        evidence: list[EvidenceItem],
        findings: list[SpecialistFinding],
    ) -> InvestigationDraft:
        payload = {
            "incident": {
                "id": incident.id,
                "service": _safe(incident.service, 100),
                "severity": incident.severity.value,
                "summary": _safe(incident.summary),
            },
            "evidence": [
                {
                    "evidence_id": item.id,
                    "kind": item.kind.value,
                    "provider": _safe(item.provider, 100),
                    "summary": _safe(item.summary),
                    "content": _safe(item.content),
                    "content_hash": item.content_hash,
                    "display_ref": _safe(item.display_ref, 300),
                }
                for item in evidence[:_MAX_EVIDENCE_ITEMS]
            ],
            "validated_specialist_findings": [
                finding.model_dump(mode="json") for finding in findings[:_MAX_FINDINGS]
            ],
        }
        try:
            response = self._client.responses.parse(
                model=self.model_id,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "Synthesize an incident investigation from only the supplied "
                            "redacted evidence and validated findings. Every material claim "
                            "must cite a supplied evidence_id. Return the strict schema only. "
                            "Use concise conclusions in rationale fields; never provide hidden "
                            "chain-of-thought. If evidence is insufficient, say so in the schema."
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload, sort_keys=True)},
                ],
                text_format=InvestigationDraft,
                reasoning={"effort": "low"},
                store=False,
                timeout=self._timeout_seconds,
            )
        except Exception as exc:
            detail = _safe(str(exc), 500)
            raise InvestigationProviderUnavailableError(
                f"OpenAI investigation request failed: {detail}"
            ) from exc

        parsed = getattr(response, "output_parsed", None)
        if not isinstance(parsed, InvestigationDraft):
            raise InvestigationProviderResponseError(
                "OpenAI investigation response did not contain a schema-valid draft"
            )
        return parsed


def build_investigation_gateway(settings: Settings) -> InvestigationGateway:
    """Select the investigation gateway without ever making demo mode live."""
    if settings.demo_mode:
        return FixtureInvestigationGateway(model_id=settings.investigation_model)
    if settings.investigation_engine != "openai":
        raise InvestigationProviderUnavailableError(
            "live mode requires INVESTIGATION_ENGINE=openai"
        )
    if not settings.openai_api_key_present:
        raise InvestigationProviderUnavailableError("OPENAI_API_KEY is required in live mode")
    return OpenAIInvestigationGateway(
        model_id=settings.investigation_model,
        timeout_seconds=settings.openai_timeout_seconds,
    )
