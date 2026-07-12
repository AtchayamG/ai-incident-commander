# M4 Approval UI Final Handoff

## Objective Achieved
Successfully completed the M4 remediation-plan and human-approval experience against the existing typed backend contracts, preserving the verified accessibility baseline.

## Implementation Details

### 1. Bounded Remediation Artifact Rendering
- **Location:** `apps/web/app/incidents/[id]/page.tsx`
- **Details:** The Approval Gate card was enriched to render the bounded remediation artifact securely. We correlate the pending `ApprovalRequest` with its underlying `RemediationPlan` and `PatchAttempt` to render:
  - **Exact Files and Intended Changes:** Displays the patch diff directly, reporting actual file/line changes against the `max_files_changed` and `max_lines_changed` budgets from the plan.
  - **Hash & Provenance:** Renders the specific artifact version from the `ApprovalRequest` alongside the unique Patch ID, clearly indicating its source as the Autonomous Incident Commander (M4).
  - **Regression Test & Verification Commands:** Fetches `falsification_tests` from the top-ranked hypothesis (generated during M3) and surfaces them as ready-to-run local CLI verification commands.
  - **Diagnosis Link:** Links back to the primary evidence item anchoring the hypothesis.
  - **Rollback:** Provides the git revert command targeting the originally identified suspect commit.

### 2. Deliberate Review Checkpoint
- The approval gate enforces that users must explicitly provide a justification reason in the text input before submitting an approval or rejection.
- The UI handles the `decision` mapping, injecting the user's rationale, and includes the `artifact_version` payload exactly as defined in `@incident-commander/contracts`.

### 3. Error Surface & State Management
- Stale, expired, or already-consumed errors returned by the API (e.g. HTTP 409 Conflict) are caught by the `api.ts` handler and surfaced directly in the Approval Gate via plain-text error alerts.
- This prevents the UI from incorrectly claiming mutation success, keeping authoritative server state in sync.

### 4. Tests Added
- **E2E (Playwright):** `apps/web/e2e/m4-approval.spec.ts` covers the full UI progression from triggering pipeline, reaching WAITING PATCH APPROVAL, intercepting deterministic backend error responses (stale simulation), submitting a successful approval, and submitting a rejection.
- **Contract Adherence (Vitest):** `apps/web/lib/api.test.ts` was extended with test cases verifying the `decideApproval` client wrapper formats requests properly and gracefully captures HTTP errors (409) without blowing up the client.
- **Docs:** `docs/testing/m4-approval-ui.md` provides execution instructions and scenario rationale.

## File Touched Summary
- `apps/web/app/incidents/[id]/page.tsx`: Injected Remediation Artifact UI block.
- `apps/web/lib/api.test.ts`: Added unit tests for the approval decision API contract.
- `apps/web/e2e/m4-approval.spec.ts`: New integration test.
- `docs/testing/m4-approval-ui.md`: Test documentation.
- `docs/project/agent-runs/M4_APPROVAL_UI_FINAL_HANDOFF.md`: This file.

## Accessibility
Ensured no new interactive focus traps were introduced and maintained standard visual hierarchy by utilizing existing design tokens (e.g., `var(--warning)`, `var(--primary-light)`). Screen reader structure remains intact due to properly labeled semantic inputs and `role="alert"` for error messages.

## Codex Integration Corrections

Codex rejected the initial browser-derived verification and rollback strings.
The accepted implementation adds a strict `RemediationPlanArtifact` contract,
fetches the immutable `/remediation-plan/artifact` resource, and renders only
its server-authored files, steps, verification commands, rollback, budgets,
network policy, version, and SHA-256 hash. Final independent verification:
`typecheck`, `lint`, 19 Vitest tests, production build, and all 7 Playwright
tests passed.
