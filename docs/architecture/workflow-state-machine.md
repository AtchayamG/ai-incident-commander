# Workflow State Machine

Implementation: `services/api/app/workflow/state_machine.py`
TypeScript mirror: `packages/contracts/src/index.ts` (`TRANSITIONS`)
Blueprint source: section 11.

## Rules

1. Only the workflow service (pipeline) changes workflow state, always through `advance()`.
2. Every transition appends a `WorkflowEvent` (monotonic per-incident sequence).
3. Agent/provider output is a typed proposal; it never mutates state.
4. Terminal states: `CLOSED`, `CANCELLED`, `NO_SAFE_REMEDIATION` — no outgoing transitions.
5. Recoverable states: `NEEDS_INPUT`, `PATCH_FAILED`, `EXTERNAL_ACTION_FAILED`.
6. Approval-gated transitions: `WAITING_PATCH_APPROVAL → PATCHING`, `WAITING_PR_APPROVAL → CREATING_PR`.
7. Every non-terminal state may transition to `CANCELLED`.

## M0 golden path (implemented, deterministic)

```
RECEIVED → NORMALIZING → COLLECTING_EVIDENCE → EVIDENCE_READY
  → INVESTIGATING → HYPOTHESES_READY → PLANNING_REMEDIATION → PLAN_READY
  → WAITING_PATCH_APPROVAL
  ── human approves ──> PATCHING → VERIFYING → REVIEW_READY
  ── human rejects ───> CANCELLED
```

`REVIEW_READY → RESOLUTION_DRAFTED → CLOSED` and the PR branch (`WAITING_PR_APPROVAL`...) are contract-complete in the transition map but not yet driven by the pipeline (M5-M6).

## Parity

Both language mirrors are pinned by tests that walk the golden path, assert terminal states have no exits, and assert recoverable re-entry:

- `services/api/tests/test_state_machine.py`
- `packages/contracts/src/state-machine.test.ts`
