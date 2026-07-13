# M7 Resolution UI — Final Handoff

Status: integrated and independently verified.

## Delivered

- A distinct `WAITING_PR_APPROVAL` gate before any resolution action.
- Typed draft-PR, communications, and postmortem views.
- Visible simulated-provider provenance; no simulated evidence is presented as live.
- Evidence-linked resolution timeline and approval history.
- Responsive layout and keyboard-accessible controls, including the 375 px viewport.

## Verification reproduced by Codex

- `npm run lint`
- `npm run typecheck`
- `npm test -- --run` — 20 passed
- `npm run build`
- `npm run test:e2e` — 16 passed

The real local API golden path resets fixtures, starts an incident, approves the patch,
grants the separate PR approval, and reaches `RESOLUTION_DRAFTED`. It also verifies the
simulated provider, communications artifacts, evidence-linked postmortem, and exactly one
PR approval.

## Remaining limitation

The optional GitHub adapter is covered only by mocked backend tests. No live repository
write, push, merge, or pull-request creation was performed or claimed.
