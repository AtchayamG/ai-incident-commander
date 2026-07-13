# Workflow State Machine

Implementation: `services/api/app/workflow/state_machine.py`. TypeScript mirror:
`packages/contracts/src/index.ts`. Only the pipeline advances state; provider
and model outputs are typed proposals.

```mermaid
flowchart LR
    RECEIVED --> NORMALIZING --> COLLECTING_EVIDENCE --> EVIDENCE_READY
    EVIDENCE_READY --> INVESTIGATING --> HYPOTHESES_READY
    HYPOTHESES_READY --> PLANNING_REMEDIATION --> PLAN_READY
    PLAN_READY --> WAITING_PATCH_APPROVAL
    WAITING_PATCH_APPROVAL -->|"approved"| PATCHING --> VERIFYING
    WAITING_PATCH_APPROVAL -->|"rejected"| CANCELLED
    VERIFYING -->|"pass + low/medium risk"| REVIEW_READY
    VERIFYING -->|"failed"| PATCH_FAILED
    VERIFYING -->|"unsafe"| NO_SAFE_REMEDIATION
    REVIEW_READY --> WAITING_PR_APPROVAL
    WAITING_PR_APPROVAL -->|"approved"| CREATING_PR
    WAITING_PR_APPROVAL -->|"rejected"| CANCELLED
    CREATING_PR -->|"success"| PR_READY --> RESOLUTION_DRAFTED --> CLOSED
    CREATING_PR -->|"failure"| EXTERNAL_ACTION_FAILED
```

Every transition appends a monotonic workflow event. Approval decisions are
single-use, expiry-checked, role-checked, and bound to artifact version/hash.
Terminal states have no outgoing transitions; recoverable failure states remain
explicit rather than being reported as success.

Parity and policy evidence:

- `services/api/tests/test_state_machine.py`
- `packages/contracts/src/state-machine.test.ts`
- `services/api/tests/test_remediation.py`
- `services/api/tests/test_verification.py`
- `services/api/tests/test_m7_pr_communications.py`
