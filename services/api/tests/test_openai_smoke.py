from types import SimpleNamespace
from typing import Any

from app.demo.openai_smoke import run_smoke
from app.domain.investigation import InvestigationDraft, InvestigationStatus


class _FakeResponses:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] = {}

    def parse(self, **kwargs: Any) -> object:
        self.kwargs = kwargs
        return SimpleNamespace(
            id="resp-private-proof-id",
            model="gpt-5.6-sol-2026-07-01",
            service_tier="default",
            usage=SimpleNamespace(input_tokens=100, output_tokens=20, total_tokens=120),
            output_parsed=InvestigationDraft(
                status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
                unknowns=["A single synthetic metric is insufficient for a root-cause claim."],
            ),
        )


class _FakeClient:
    def __init__(self) -> None:
        self.responses = _FakeResponses()


def test_smoke_returns_safe_hashed_receipt_and_strict_output() -> None:
    client = _FakeClient()
    receipt = run_smoke(client)

    assert receipt["passed"] is True
    assert receipt["model_requested"] == "gpt-5.6"
    assert receipt["model_returned"] == "gpt-5.6-sol-2026-07-01"
    assert receipt["structured_output"] == "InvestigationDraft"
    assert receipt["response_id_sha256"] != "resp-private-proof-id"
    assert len(str(receipt["response_id_sha256"])) == 64
    assert receipt["total_tokens"] == 120
    assert client.responses.kwargs["store"] is False
    assert client.responses.kwargs["reasoning"] == {"effort": "low"}
