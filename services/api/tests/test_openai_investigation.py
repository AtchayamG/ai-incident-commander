from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.config import Settings
from app.domain.contracts import EvidenceItem, Incident
from app.domain.enums import Environment, EvidenceKind, ProviderMode, Severity, WorkflowState
from app.domain.investigation import InvestigationDraft, InvestigationStatus
from app.providers.openai_investigation import (
    InvestigationProviderResponseError,
    InvestigationProviderUnavailableError,
    OpenAIInvestigationGateway,
    build_investigation_gateway,
)
from app.providers.simulated_investigation import FixtureInvestigationGateway


class _FakeResponses:
    def __init__(self, parsed: object | None = None, error: Exception | None = None) -> None:
        self.parsed = parsed
        self.error = error
        self.kwargs: dict[str, Any] = {}

    def parse(self, **kwargs: Any) -> object:
        self.kwargs = kwargs
        if self.error is not None:
            raise self.error
        return SimpleNamespace(output_parsed=self.parsed)


class _FakeClient:
    def __init__(self, responses: _FakeResponses) -> None:
        self.responses = responses


def _incident() -> Incident:
    now = datetime(2026, 7, 13, tzinfo=UTC)
    return Incident(
        id="inc-1",
        title="Checkout failure",
        service="checkout-api",
        environment=Environment.PRODUCTION,
        severity=Severity.SEV2,
        summary="token=super-secret-value should be redacted",
        state=WorkflowState.INVESTIGATING,
        provider_mode=ProviderMode.LIVE,
        created_at=now,
        updated_at=now,
    )


def _evidence() -> EvidenceItem:
    now = datetime(2026, 7, 13, tzinfo=UTC)
    return EvidenceItem(
        id="ev-1",
        incident_id="inc-1",
        kind=EvidenceKind.LOG,
        provider="test",
        source="test",
        summary="checkout failure",
        content="password=hunter2 and stack trace",
        content_hash="sha256:test",
        display_ref="logs/1",
        redaction_applied=True,
        redaction_rules=["assigned_secret"],
        captured_at=now,
        created_at=now,
    )


def test_openai_gateway_requests_strict_parsed_output_and_redacts_payload() -> None:
    draft = InvestigationDraft(
        status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
        unknowns=["More evidence is required"],
    )
    responses = _FakeResponses(parsed=draft)
    gateway = OpenAIInvestigationGateway(
        model_id="configured-model", client=cast(Any, _FakeClient(responses)), timeout_seconds=17
    )

    result = gateway.synthesize(_incident(), [_evidence()], [])

    assert result is draft
    assert responses.kwargs["model"] == "configured-model"
    assert responses.kwargs["text_format"] is InvestigationDraft
    assert responses.kwargs["reasoning"] == {"effort": "low"}
    assert responses.kwargs["store"] is False
    assert responses.kwargs["timeout"] == 17
    request_text = str(responses.kwargs["input"])
    assert "super-secret-value" not in request_text
    assert "hunter2" not in request_text
    assert "[REDACTED:assigned_secret]" in request_text
    assert "chain-of-thought" in request_text


def test_openai_gateway_rejects_unparsed_response() -> None:
    gateway = OpenAIInvestigationGateway(
        model_id="configured-model", client=cast(Any, _FakeClient(_FakeResponses(parsed={})))
    )
    with pytest.raises(InvestigationProviderResponseError, match="schema-valid"):
        gateway.synthesize(_incident(), [_evidence()], [])


def test_openai_gateway_redacts_provider_failure() -> None:
    responses = _FakeResponses(error=RuntimeError("api_key=sk-abcdefghijklmnop"))
    gateway = OpenAIInvestigationGateway(
        model_id="configured-model", client=cast(Any, _FakeClient(responses))
    )
    with pytest.raises(InvestigationProviderUnavailableError) as caught:
        gateway.synthesize(_incident(), [_evidence()], [])
    assert "sk-abcdefghijklmnop" not in str(caught.value)
    assert "[REDACTED:" in str(caught.value)


def test_factory_keeps_demo_fixture_even_with_live_configuration() -> None:
    gateway = build_investigation_gateway(
        Settings(
            demo_mode=True,
            investigation_engine="openai",
            investigation_model="configured-model",
            openai_api_key_present=True,
        )
    )
    assert isinstance(gateway, FixtureInvestigationGateway)


def test_factory_fails_closed_without_explicit_live_configuration() -> None:
    with pytest.raises(InvestigationProviderUnavailableError, match="INVESTIGATION_ENGINE"):
        build_investigation_gateway(Settings(demo_mode=False))
    with pytest.raises(InvestigationProviderUnavailableError, match="OPENAI_API_KEY"):
        build_investigation_gateway(
            Settings(
                demo_mode=False,
                investigation_engine="openai",
                investigation_model="configured-model",
            )
        )
