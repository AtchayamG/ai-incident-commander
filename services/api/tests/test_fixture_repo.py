"""The checkout-api fixture repository: deterministic, complete, no nested git."""

import json

from app.providers.simulated import default_fixtures_root

ROOT = default_fixtures_root() / "checkout-api"


def test_no_nested_git_directory() -> None:
    assert not list(default_fixtures_root().rglob(".git"))


def test_source_contains_unsafe_regression() -> None:
    source = (ROOT / "repo" / "src" / "checkout.ts").read_text(encoding="utf-8")
    assert "const code = session.discount.code;" in source
    assert "session.discount?.code" not in source.replace(
        "//   const code = session.discount?.code ?? null;", ""
    )


def test_tests_cover_discounted_sessions_only() -> None:
    tests = (ROOT / "repo" / "src" / "checkout.test.ts").read_text(encoding="utf-8")
    assert tests.count("discount: { code:") >= 3
    assert "cartTotal: 75" not in tests  # the missing no-discount case arrives with the patch


def test_commit_history_records_the_regression() -> None:
    commits = json.loads(
        (ROOT / "repo" / "history" / "commits.json").read_text(encoding="utf-8")
    )
    regressing = next(c for c in commits if c["sha"] == "c7f2e9a")
    assert regressing["authored_at"] == "2026-07-13T09:48:00Z"
    assert "src/checkout.ts" in regressing["files"]

    diff = (ROOT / "repo" / "history" / "c7f2e9a.diff").read_text(encoding="utf-8")
    assert "-  const code = session.discount?.code ?? null;" in diff
    assert "+  const code = session.discount.code;" in diff


def test_deploy_history_matches_blueprint() -> None:
    deploys = json.loads((ROOT / "deploys" / "deploys.json").read_text(encoding="utf-8"))
    latest = deploys[-1]
    assert latest["version"] == "2026.07.13.4"
    assert latest["deployed_at"] == "2026-07-13T10:02:00Z"
    assert latest["commit"] == "c7f2e9a"
