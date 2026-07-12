"""Blueprint section 32 evidence bundle: content and provenance completeness."""

import hashlib
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

GOLDEN_ID = "inc-demo-0001"


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _collect_evidence(client: TestClient) -> list[dict[str, Any]]:
    assert client.post(f"/api/v1/incidents/{GOLDEN_ID}/start").status_code == 200
    items: list[dict[str, Any]] = client.get(f"/api/v1/incidents/{GOLDEN_ID}/evidence").json()
    return items


def _find(items: list[dict[str, Any]], fragment: str) -> dict[str, Any]:
    matches = [e for e in items if fragment in e["summary"]]
    assert len(matches) == 1, f"expected exactly one item mentioning {fragment!r}"
    return matches[0]


def test_bundle_contains_all_section_32_elements(client: TestClient) -> None:
    items = _collect_evidence(client)
    assert len(items) == 8

    alert = _find(items, "rose from 0.2% to 12.4%")
    assert alert["kind"] == "metric"

    deploy = _find(items, "Version 2026.07.13.4")
    assert deploy["kind"] == "deploy"
    assert _utc(deploy["captured_at"]) == datetime(2026, 7, 13, 10, 2, tzinfo=UTC)

    start = _find(items, "Incident start 2026-07-13T10:05:00Z")
    assert start["kind"] == "metric"
    assert _utc(start["captured_at"]) == datetime(2026, 7, 13, 10, 5, tzinfo=UTC)

    stack = _find(items, "stack trace points at src/checkout.ts")
    assert stack["kind"] == "log"
    assert "src/checkout.ts:26" in stack["content"]

    commit = _find(items, "Commit c7f2e9a")
    assert commit["kind"] == "diff"
    assert _utc(commit["captured_at"]) == datetime(2026, 7, 13, 9, 48, tzinfo=UTC)
    assert "modified discount handling" in commit["summary"]
    assert "-  const code = session.discount?.code ?? null;" in commit["content"]
    assert "+  const code = session.discount.code;" in commit["content"]

    no_discount = _find(items, "sessions without a discount; discounted sessions succeed")
    assert no_discount["kind"] == "log"
    assert '"failed_with_discount": 0' in no_discount["content"]

    coverage = _find(items, "Test coverage gap")
    assert coverage["kind"] == "config"
    assert "discount:" in coverage["content"]

    runbook = _find(items, "check deployment correlation first")
    assert runbook["kind"] == "manual"
    assert "Reproduce locally" in runbook["content"]


def test_every_item_has_full_provenance(client: TestClient) -> None:
    items = _collect_evidence(client)
    for item in items:
        assert item["provider"].startswith("fixture-"), item["id"]
        assert item["source"].startswith("simulated:"), item["id"]
        assert item["display_ref"].startswith("simulated://checkout-api/"), item["id"]
        assert item["captured_at"], item["id"]
        assert item["provenance"]["simulated"] is True, item["id"]
        assert item["provenance"]["fixture_path"].startswith("fixtures/checkout-api/")
        assert "[SIMULATED]" in item["summary"], item["id"]
        assert isinstance(item["redaction_applied"], bool)
        assert isinstance(item["redaction_rules"], list)
        digest = hashlib.sha256(item["content"].encode("utf-8")).hexdigest()
        assert item["content_hash"] == f"sha256:{digest}", item["id"]


def test_bundle_survives_persistence_round_trip(client: TestClient) -> None:
    """All provenance fields come back identical after a fresh read (DB-backed)."""
    first = _collect_evidence(client)
    second = client.get(f"/api/v1/incidents/{GOLDEN_ID}/evidence").json()
    keys = (
        "id",
        "kind",
        "provider",
        "source",
        "summary",
        "content",
        "content_hash",
        "display_ref",
        "redaction_applied",
        "redaction_rules",
        "provenance",
        "captured_at",
    )
    assert [{k: e[k] for k in keys} for e in first] == [{k: e[k] for k in keys} for e in second]
