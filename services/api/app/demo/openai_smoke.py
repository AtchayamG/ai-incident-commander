"""Minimal credentialed GPT-5.6 structured-output smoke with a safe receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from typing import Any, cast

from openai import OpenAI

from app.domain.contracts import EvidenceItem, Incident
from app.domain.enums import (
    Environment,
    EvidenceKind,
    ProviderMode,
    Severity,
    WorkflowState,
)
from app.providers.openai_investigation import OpenAIInvestigationGateway


class _RecordingResponses:
    def __init__(self, delegate: Any) -> None:
        self._delegate = delegate
        self.safe_receipt: dict[str, object] = {}

    def parse(self, **kwargs: Any) -> object:
        response = self._delegate.parse(**kwargs)
        response_id = str(getattr(response, "id", ""))
        usage = getattr(response, "usage", None)
        self.safe_receipt = {
            "response_id_sha256": hashlib.sha256(response_id.encode("utf-8")).hexdigest(),
            "model_returned": str(getattr(response, "model", "unknown")),
            "service_tier": str(getattr(response, "service_tier", "unknown")),
            "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        }
        return response


class _RecordingClient:
    def __init__(self, client: Any) -> None:
        self.responses = _RecordingResponses(client.responses)


def _synthetic_incident() -> Incident:
    now = datetime.now(UTC)
    return Incident(
        id="smoke-gpt56-0001",
        title="Synthetic checkout error-rate regression",
        service="checkout-api-fixture",
        environment=Environment.STAGING,
        severity=Severity.SEV2,
        summary="Synthetic HTTP 500 rate rose after a fixture deployment.",
        state=WorkflowState.INVESTIGATING,
        provider_mode=ProviderMode.LIVE,
        created_at=now,
        updated_at=now,
    )


def _synthetic_evidence() -> EvidenceItem:
    now = datetime.now(UTC)
    content = "Synthetic metric: error rate 0.2% -> 5.0% after fixture deploy fixture-2026-07-13."
    return EvidenceItem(
        id="smoke-ev-0001",
        incident_id="smoke-gpt56-0001",
        kind=EvidenceKind.METRIC,
        provider="submission-smoke-fixture",
        source="synthetic://metrics/checkout-api",
        summary="Synthetic error-rate increase follows fixture deployment.",
        content=content,
        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        display_ref="synthetic-metric-1",
        redaction_applied=True,
        redaction_rules=[],
        captured_at=now,
        created_at=now,
    )


def run_smoke(client: Any, model: str = "gpt-5.6") -> dict[str, object]:
    recording = _RecordingClient(client)
    gateway = OpenAIInvestigationGateway(
        model_id=model,
        client=cast(Any, recording),
        timeout_seconds=90,
    )
    draft = gateway.synthesize(_synthetic_incident(), [_synthetic_evidence()], [])
    return {
        "passed": True,
        "checked_at": datetime.now(UTC).isoformat(),
        "model_requested": model,
        "structured_output": draft.__class__.__name__,
        "investigation_status": draft.status.value,
        "synthetic_input": True,
        "stored_by_request": False,
        "external_action_attempted": False,
        **recording.responses.safe_receipt,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt-5.6")
    args = parser.parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required; no key value was read or printed")
    print(json.dumps(run_smoke(OpenAI(), model=args.model), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
