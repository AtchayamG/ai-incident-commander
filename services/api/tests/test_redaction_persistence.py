"""Planted fixture secrets must never survive into any persisted artifact."""

import sqlite3

from fastapi.testclient import TestClient

from app.providers.simulated import default_fixtures_root

GOLDEN_ID = "inc-demo-0001"

# Secret-shaped tokens planted in fixtures/checkout-api/telemetry/error_samples.log.
PLANTED_SECRETS = ("sk-fixture9c31f7a2b8d4e6f0", "S3cretPw41")


def test_fixture_log_actually_contains_planted_secrets() -> None:
    """Guard: if the fixture drifts, the persistence assertions become vacuous."""
    log = (
        default_fixtures_root() / "checkout-api" / "telemetry" / "error_samples.log"
    ).read_text(encoding="utf-8")
    for secret in PLANTED_SECRETS:
        assert secret in log


def test_secrets_never_reach_api_responses(client: TestClient) -> None:
    assert client.post(f"/api/v1/incidents/{GOLDEN_ID}/start").status_code == 200
    evidence = client.get(f"/api/v1/incidents/{GOLDEN_ID}/evidence").json()

    stack = next(e for e in evidence if "TypeError" in e["summary"])
    assert stack["redaction_applied"] is True
    assert stack["redaction_rules"], "expected at least one matched redaction rule"
    assert "[REDACTED:" in stack["content"]

    for item in evidence:
        for secret in PLANTED_SECRETS:
            assert secret not in item["content"], item["id"]
            assert secret not in item["summary"], item["id"]
            assert secret not in str(item["provenance"]), item["id"]


def test_secrets_never_reach_the_database(client: TestClient, test_db_path: str) -> None:
    """Scan every row of every table in the raw SQLite file for raw secrets."""
    assert client.post(f"/api/v1/incidents/{GOLDEN_ID}/start").status_code == 200

    conn = sqlite3.connect(test_db_path)
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "evidence_items" in tables
        for table in tables:
            for row in conn.execute(f"SELECT * FROM {table}").fetchall():
                dump = repr(row)
                for secret in PLANTED_SECRETS:
                    assert secret not in dump, f"raw secret in table {table}"
    finally:
        conn.close()
