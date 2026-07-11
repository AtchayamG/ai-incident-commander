# Frontend Testing Strategy

This document outlines the testing patterns and verification gates established for the `@incident-commander/web` Next.js frontend package.

## Verification Gates
1. **Linter**: Enforced via `next lint`. Validates code quality, React hook rules, and accessibility constraints.
2. **Typechecker**: Strict typescript verification via `tsc --noEmit`. Verified against both the shared `@incident-commander/contracts` packages and Next.js page routing types.
3. **Unit / Integration Tests**: Powered by `vitest` running in `threads` pool mode (to prevent Windows-specific tinypool folder-space crashes).
4. **Production Build**: Compiles static assets and dynamic routes via `next build` ensuring all paths, imports, and client/server boundaries resolve cleanly.

## Unit Test Coverage
We have expanded the unit test suite in `apps/web/lib/api.test.ts` to cover the new API endpoints introduced for M1 interactive flows:
- **Transport Security**: Stubs fetch requests to verify that transport errors do not throw uncaught exceptions, returning `{ ok: false, error: ... }` structured failures instead.
- **Incident Cancellation**: Asserts that `cancelIncident` issues a `POST` request to `/api/v1/incidents/{id}/cancel`.
- **Demo Mode Reset**: Asserts that `resetDemo` sets the correct `X-Demo-Admin-Key` header and hits `/api/v1/incidents/reset-demo`.
- **Sub-resource Resolvers**: Verifies GET requests are dispatched to their appropriate resource sub-routes:
  - Timeline: `/api/v1/incidents/{id}/timeline`
  - Evidence: `/api/v1/incidents/{id}/evidence`
  - Hypotheses: `/api/v1/incidents/{id}/hypotheses`
  - Remediation Plans: `/api/v1/incidents/{id}/remediation-plan`
  - Patches: `/api/v1/incidents/{id}/patches`
  - Approvals: `/api/v1/incidents/{id}/approvals`

## Manual Verification
- **API Down States**: The client dashboard automatically identifies when the backend API is unreachable, showing a full-screen alert and a manual "Retry Connection" action.
- **Form Validation**: Incident Intake form performs accessibility-friendly input validation (checking for empty fields and announcing errors using `role="alert"`).
- **Auto-polling**: Detail page updates its state every 5 seconds, checking for new workflow events, hypotheses, or patch proposals, and gracefully disengages once a terminal state is reached.
