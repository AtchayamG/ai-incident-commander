from app.demo.runner import reset_once, run_many


def test_demo_reset_is_protected_and_repeatable() -> None:
    result = reset_once()

    assert result == {
        "incident_id": "inc-demo-0001",
        "state": "RECEIVED",
        "provider_mode": "simulated",
    }


def test_complete_demo_runner_is_repeatable() -> None:
    results = run_many(2)

    assert len(results) == 2
    assert {result["state"] for result in results} == {"RESOLUTION_DRAFTED"}
    assert {result["provider_mode"] for result in results} == {"simulated"}
    assert {result["approval_count"] for result in results} == {2}
    assert all(result["postmortem_timeline_events"] for result in results)
