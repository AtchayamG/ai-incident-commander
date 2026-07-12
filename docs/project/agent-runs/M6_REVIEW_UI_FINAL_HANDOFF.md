# M6 Review UI Handoff

## Summary of Changes
- Added `getIncidentVerifications` to fetch authoritative verification runs
  from the existing incident endpoint and correlate them by `patch_id`.
- Added `VerificationRun` type import from `@incident-commander/contracts`.
- Updated `IncidentDetailPage` to load `VerificationRuns` associated with each `PatchAttempt`.
- Rendered verification test results (passes/failures and individual checks) within the Patch Attempt bounds section.
- Enforced a hard block on PR Approval (when `approval.approval_type === "CREATE_DRAFT_PR"`) if the verification is missing or failed.
- Added Playwright scenarios to `m6-review.spec.ts` for verifying PR-block under missing/failed verification, and unblocking upon successful verification.
- Added Vitest unit test for `getPatchVerification` in `api.test.ts`.

## M5 Integration Seam
The existing `GET /api/v1/incidents/{incident_id}/verifications` endpoint is
used. An empty list truthfully renders "Pending / Not Started" and blocks PR
approval.

**Next Steps for M5 Backend:**
1. M6 backend must persist verification output through the existing store and
   incident endpoint.
2. Ensure the response shape correctly matches `VerificationRun`:
```json
{
  "id": "verif-123",
  "patch_id": "patch-xyz",
  "passed": true,
  "checks": [
    { "name": "Lint", "passed": true, "detail": "Success" }
  ]
}
```
3. Add a real local-API browser scenario after the verification workflow
   progresses to `REVIEW_READY`. Current intercepted scenarios are frontend
   state tests and are not accepted as end-to-end backend proof.

## Verification
- Accessibility, layout, and non-color cues are preserved.
- Empty states correctly distinguish between "loading", "not found" (pending), and explicit failure states without mocking fake success scenarios.
