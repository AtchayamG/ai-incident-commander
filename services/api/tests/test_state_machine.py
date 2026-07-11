import pytest

from app.domain.enums import WorkflowState as W
from app.workflow.state_machine import (
    TERMINAL_STATES,
    TRANSITIONS,
    InvalidTransitionError,
    advance,
    can_transition,
    is_terminal,
    requires_approval,
)

GOLDEN_PATH = [
    W.RECEIVED,
    W.NORMALIZING,
    W.COLLECTING_EVIDENCE,
    W.EVIDENCE_READY,
    W.INVESTIGATING,
    W.HYPOTHESES_READY,
    W.PLANNING_REMEDIATION,
    W.PLAN_READY,
    W.WAITING_PATCH_APPROVAL,
    W.PATCHING,
    W.VERIFYING,
    W.REVIEW_READY,
    W.RESOLUTION_DRAFTED,
    W.CLOSED,
]


def test_golden_path_is_fully_legal() -> None:
    for current, target in zip(GOLDEN_PATH, GOLDEN_PATH[1:], strict=False):
        assert advance(current, target) == target


def test_illegal_transition_raises() -> None:
    with pytest.raises(InvalidTransitionError):
        advance(W.RECEIVED, W.PATCHING)


def test_terminal_states_have_no_outgoing_transitions() -> None:
    for state in TERMINAL_STATES:
        assert TRANSITIONS[state] == frozenset()
        assert is_terminal(state)


def test_every_state_has_a_transition_entry() -> None:
    assert set(TRANSITIONS) == set(W)


def test_all_non_terminal_states_can_cancel() -> None:
    for state in W:
        if state not in TERMINAL_STATES:
            assert can_transition(state, W.CANCELLED), f"{state} cannot cancel"


def test_approval_gates() -> None:
    assert requires_approval(W.WAITING_PATCH_APPROVAL, W.PATCHING)
    assert requires_approval(W.WAITING_PR_APPROVAL, W.CREATING_PR)
    assert not requires_approval(W.RECEIVED, W.NORMALIZING)


def test_recoverable_paths() -> None:
    assert can_transition(W.NEEDS_INPUT, W.COLLECTING_EVIDENCE)
    assert can_transition(W.PATCH_FAILED, W.PLAN_READY)
    assert can_transition(W.EXTERNAL_ACTION_FAILED, W.WAITING_PR_APPROVAL)
