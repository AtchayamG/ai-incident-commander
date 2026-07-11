"""Incident workflow state machine (blueprint section 11).

Only this module decides whether a state change is legal. Agent or provider
output never mutates workflow state directly; deterministic code calls
``advance`` with a trigger and receives either the new state or an error.
"""

from app.domain.enums import WorkflowState

W = WorkflowState

TRANSITIONS: dict[WorkflowState, frozenset[WorkflowState]] = {
    W.RECEIVED: frozenset({W.NORMALIZING, W.CANCELLED}),
    W.NORMALIZING: frozenset({W.COLLECTING_EVIDENCE, W.CANCELLED}),
    W.COLLECTING_EVIDENCE: frozenset({W.EVIDENCE_READY, W.NEEDS_INPUT, W.CANCELLED}),
    W.EVIDENCE_READY: frozenset({W.INVESTIGATING, W.CANCELLED}),
    W.INVESTIGATING: frozenset({W.HYPOTHESES_READY, W.NEEDS_INPUT, W.CANCELLED}),
    W.HYPOTHESES_READY: frozenset({W.PLANNING_REMEDIATION, W.CANCELLED}),
    W.PLANNING_REMEDIATION: frozenset({W.PLAN_READY, W.NO_SAFE_REMEDIATION, W.CANCELLED}),
    W.PLAN_READY: frozenset({W.WAITING_PATCH_APPROVAL, W.CANCELLED}),
    W.WAITING_PATCH_APPROVAL: frozenset({W.PATCHING, W.CANCELLED}),
    W.PATCHING: frozenset({W.VERIFYING, W.PATCH_FAILED, W.CANCELLED}),
    W.VERIFYING: frozenset({W.REVIEW_READY, W.PATCHING, W.PATCH_FAILED, W.CANCELLED}),
    W.REVIEW_READY: frozenset({W.WAITING_PR_APPROVAL, W.RESOLUTION_DRAFTED, W.CANCELLED}),
    W.WAITING_PR_APPROVAL: frozenset({W.CREATING_PR, W.REVIEW_READY, W.CANCELLED}),
    W.CREATING_PR: frozenset({W.PR_READY, W.EXTERNAL_ACTION_FAILED, W.CANCELLED}),
    W.PR_READY: frozenset({W.RESOLUTION_DRAFTED, W.CANCELLED}),
    W.EXTERNAL_ACTION_FAILED: frozenset({W.WAITING_PR_APPROVAL, W.CANCELLED}),
    W.RESOLUTION_DRAFTED: frozenset({W.CLOSED, W.CANCELLED}),
    W.NEEDS_INPUT: frozenset({W.COLLECTING_EVIDENCE, W.CANCELLED}),
    W.PATCH_FAILED: frozenset({W.PLAN_READY, W.CANCELLED}),
    W.NO_SAFE_REMEDIATION: frozenset(),
    W.CLOSED: frozenset(),
    W.CANCELLED: frozenset(),
}

TERMINAL_STATES: frozenset[WorkflowState] = frozenset(
    {W.CLOSED, W.CANCELLED, W.NO_SAFE_REMEDIATION}
)

RECOVERABLE_STATES: frozenset[WorkflowState] = frozenset(
    {W.NEEDS_INPUT, W.PATCH_FAILED, W.EXTERNAL_ACTION_FAILED}
)

APPROVAL_GATED_TRANSITIONS: frozenset[tuple[WorkflowState, WorkflowState]] = frozenset(
    {
        (W.WAITING_PATCH_APPROVAL, W.PATCHING),
        (W.WAITING_PR_APPROVAL, W.CREATING_PR),
    }
)


class InvalidTransitionError(Exception):
    def __init__(self, current: WorkflowState, target: WorkflowState) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Illegal workflow transition {current} -> {target}")


def is_terminal(state: WorkflowState) -> bool:
    return state in TERMINAL_STATES


def can_transition(current: WorkflowState, target: WorkflowState) -> bool:
    return target in TRANSITIONS[current]


def advance(current: WorkflowState, target: WorkflowState) -> WorkflowState:
    """Validate and return the target state, raising on illegal transitions."""
    if not can_transition(current, target):
        raise InvalidTransitionError(current, target)
    return target


def requires_approval(current: WorkflowState, target: WorkflowState) -> bool:
    return (current, target) in APPROVAL_GATED_TRANSITIONS
