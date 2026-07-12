# M4 Approval UI Testing Guide

## Overview
This document outlines the testing strategy and execution for the M4 Approval Gate, a critical human-in-the-loop checkpoint within the Autonomous Incident Commander remediation pipeline.

## Testing Layers

### 1. E2E Browser Testing (Playwright)
**File:** `apps/web/e2e/m4-approval.spec.ts`

The Playwright tests execute against the live Next.js application and the mocked/local Python FastAPI backend.
They exercise the full M4 pipeline state progression by resetting the demo state and triggering a pipeline run to reach the `WAITING PATCH APPROVAL` state.

**Scenarios Covered:**
- **Bounded Artifact Rendering**: Verifies the UI successfully pulls and renders details from the active `RemediationPlan` and `PatchAttempt`, displaying diffs, exact file/line changes against budgets, provenance, and fallback regression commands.
- **Justification Enforcement**: Asserts that an approval decision cannot be submitted without a valid justification text.
- **Deterministic Error Handling (Stale State)**: Intercepts the HTTP request to deterministically simulate a 409 Conflict (e.g. stale approval/already consumed), validating that the UI surfaces the error string without progressing the state.
- **Successful Approval**: Tests a subsequent successful POST to `/api/v1/approvals/:id/decision`, verifying the state transitions to `PATCHING` or `VERIFYING`.
- **Rejection Scenario**: Verifies that rejecting the patch successfully logs the decision and transitions state appropriately.

### 2. API Contract Testing (Vitest)
**File:** `apps/web/lib/api.test.ts` (added to existing tests)

Vitest tests ensure the client robustly adheres to the `ApprovalDecisionIn` typing provided by `@incident-commander/contracts`.

**Scenarios Covered:**
- **Contract Adherence**: Asserts the HTTP method (`POST`), headers (`Content-Type`), and payload (`decision`, `reason`, `artifact_version`) exactly match backend expectations.
- **Error Parsing**: Validates that standard FastAPI error bodies (`{ "detail": "..." }`) and HTTP 409 responses are parsed correctly and exposed via the `ApiResult` union return type, preventing unexpected client-side crashes when the backend denies a stale decision.

## Accessibility (a11y)
The Approval Gate is built using semantic HTML. We adhere to the existing zero-tolerance policy for axe violations. Focus visibility and color contrast in the new Remediation Artifact display inherit from existing standard tokens.

## How to Run

**E2E Tests:**
```bash
pnpm test:e2e --project=chromium apps/web/e2e/m4-approval.spec.ts
```

**Unit/Contract Tests:**
```bash
pnpm test
```
