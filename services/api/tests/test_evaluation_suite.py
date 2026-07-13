"""Deterministic integration and mutation tests for the blueprint M9 eval suite."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evals.runner import SCENARIOS_DIR, run_eval_scenario

# Verify directory exists
assert SCENARIOS_DIR.exists(), f"Scenarios directory not found at: {SCENARIOS_DIR}"
SCENARIO_FILES = sorted(SCENARIOS_DIR.glob("scenario_*.json"))


def test_exactly_eight_scenarios_exist() -> None:
    """Assert exactly eight unique evaluation scenarios exist in the fixtures directory."""
    assert len(SCENARIO_FILES) == 8, f"Expected exactly 8 scenarios, found {len(SCENARIO_FILES)}"

    scenario_ids = set()
    for f in SCENARIO_FILES:
        with open(f, encoding="utf-8") as f_in:
            data = json.load(f_in)
            scenario_ids.add(data["scenario_id"])

    assert len(scenario_ids) == 8, "Expected 8 unique scenario IDs"
    assert scenario_ids == {f"scenario-{i}" for i in range(1, 9)}

    expected_names = {
        "golden_path",
        "missing_environment_variable",
        "dependency_timeout_mitigation",
        "preexisting_failing_test",
        "misleading_deploy_correlation",
        "secret_log_redaction",
        "prompt_injection_safety",
        "high_risk_auth_regression",
    }
    names = {
        json.loads(path.read_text(encoding="utf-8"))["name"] for path in SCENARIO_FILES
    }
    assert names == expected_names


@pytest.mark.parametrize("scenario_file", SCENARIO_FILES, ids=lambda p: p.stem)
def test_evaluation_scenarios_pass_normally(scenario_file: Path) -> None:
    """Verify that all scenarios pass successfully under normal evaluation execution."""
    res = run_eval_scenario(scenario_file)
    assert res["passed"] is True, (
        f"Scenario {res['scenario_id']} failed: {res['failure_reason']}"
    )
    assert res["failure_reason"] is None


def test_mutation_secret_redaction_fails() -> None:
    """Verify that bypassing redaction causes the secret scenario to fail."""
    scenario_file = SCENARIOS_DIR / "scenario_6_secret_redaction.json"
    res = run_eval_scenario(scenario_file, mutate_type="bypass_redaction")
    assert res["passed"] is False

    err = (res["failure_reason"] or "").lower()
    assert "redaction" in err or "prohibited" in err


def test_mutation_high_risk_auth_fails() -> None:
    """Verify that bypassing risk review causes the auth scenario to fail."""
    scenario_file = SCENARIOS_DIR / "scenario_8_auth_regression.json"
    res = run_eval_scenario(scenario_file, mutate_type="bypass_risk")
    assert res["passed"] is False

    # Bypassed risk check, so risk level was low instead of high.
    # Therefore, the pipeline did not transition to PATCH_FAILED or block the PR.
    err = (res["failure_reason"] or "").lower()
    assert "risk" in err or res["final_state"] != "PATCH_FAILED"


def test_mutation_preexisting_baseline_pass_fails() -> None:
    """Verify that hiding a pre-existing failure is caught by expected outcome grading."""
    scenario_file = SCENARIOS_DIR / "scenario_4_preexisting_failure.json"
    res = run_eval_scenario(scenario_file, mutate_type="baseline_test_pass")
    assert res["passed"] is False

    err = (res["failure_reason"] or "").lower()
    assert "state" in err or res["final_state"] != "PATCH_FAILED"
