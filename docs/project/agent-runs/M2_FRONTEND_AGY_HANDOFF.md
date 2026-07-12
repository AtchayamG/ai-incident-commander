# M2 Handoff: Evidence & Timeline Experience

## Accomplished Objectives
Completed the judge-facing M2 evidence and timeline experience using the integrated M2 API contracts and the deterministic golden incident. All quality gates, linting, type-checking, unit tests, and Playwright E2E tests pass.

---

## 1. Shared Contract TypeScript Parity
Updated the `@incident-commander/contracts` package ([index.ts](file:///D:/Work/Codex/Hackathon%20Projects/OpenAI%20Hackathon/.agent-worktrees/incident-m2-frontend/packages/contracts/src/index.ts)) to align the `EvidenceItem` type definitions with the backend FastAPI/Pydantic schemas:
- Added `provider` (string)
- Added `content_hash` (string)
- Added `display_ref` (string)
- Added `redaction_rules` (string[], optional)
- Added `captured_at` (string)

---

## 2. Complete Golden Evidence Bundle Rendering
Implemented high-fidelity rendering for all 8 deterministic golden evidence items in the Incident room page ([page.tsx](file:///D:/Work/Codex/Hackathon%20Projects/OpenAI%20Hackathon/.agent-worktrees/incident-m2-frontend/apps/web/app/incidents/%5Bid%5D/page.tsx)):
- **Visual Design**: Sleek high-density metadata grid showing Captured time, display reference (Ref), content SHA-256 hash, provider, and source.
- **Labels**: Render `🤖 SIMULATED` and `🔒 REDACTED` badges depending on the telemetry's provenance and redaction states.
- **Collapsible Content**: Clean code formatting for sanitized raw contents (`content`) alongside matching redaction rules and complete JSON provenance metadata when expanded.

---

## 3. Chronological Timeline & Scroll-Focus Links
- **Chronological Stability**: The timeline is sorted in strict chronological ascending order based on the `at` timestamp of the events, ensuring a logical narrative (commit -> deploy -> incident start).
- **Interactive Focus**: Clicking "View Supporting Evidence" in the timeline triggers `scrollToEvidence(evidenceId)` which automatically:
  1. Expands the corresponding evidence card.
  2. Scrolls the page smoothly to center the card.
  3. Sets keyboard focus (`tabIndex={-1}`).
  4. Temporarily highlights the card with a purple glow animation (`.evidence-highlighted`).

---

## 4. Demo Progress Control
Added a step-by-step progress panel when clicking **Start Diagnosing Pipeline** for a `RECEIVED` demo incident:
- Renders an interactive checklist displaying the active pipeline stage.
- Sequences through 8 visual phases (Initializing -> Normalizing -> Telemetry query -> Hypotheses -> Remediation formulation -> Approval Request registration) while executing the FastAPI pipeline in the background.
- Preserves approval boundaries: upon pipeline completion, the progress panel hides and the prominent **Human Approval Gate** action card automatically appears.

---

## 5. Robust Loading, Empty & Error States
- Added granular sub-resource error tracking for `evidenceError` and `timelineError` within [page.tsx](file:///D:/Work/Codex/Hackathon%20Projects/OpenAI%20Hackathon/.agent-worktrees/incident-m2-frontend/apps/web/app/incidents/%5Bid%5D/page.tsx).
- Failed API fetches are captured and rendered in high-visibility warning blocks instead of silently failing and displaying empty arrays.

---

## 6. E2E Validation (Playwright Chromium)
Created a new E2E test scenario: `apps/web/e2e/golden-evidence.spec.ts` that automates and asserts the M2 workflow:
- Performs a demo reset (seeding `inc-demo-0001` in `RECEIVED` state).
- Triggers the pipeline and asserts pipeline progress checklist.
- Waits for the `WAITING_PATCH_APPROVAL` transition.
- Asserts that all 8 golden evidence cards are present (metric alert, deploy, commit, log stack trace, runbook config, etc.).
- Verifies timeline chronology and focus-scroll behavior.
- Verifies simulated and redacted labels, redaction rules, display refs, hashes, and provenance objects.
- Ensures no `500 Internal Server Error` HTTP status codes are received.

---

## Test Verification Results

### Unit & Parity Tests
```bash
pnpm test
```
- `@incident-commander/contracts`: 6 tests passed (state machine transitions validation).
- `@incident-commander/web`: 15 tests passed (API client verification).

### Playwright E2E Tests
```bash
pnpm test:e2e
```
- Running 2 tests using 1 worker:
  - `e2e/golden-evidence.spec.ts` (10.3s) - **Passed**
  - `e2e/incident-creation.spec.ts` (2.0s) - **Passed**
- **Result**: `2 passed (20.3s)`

### Next.js Production Build
```bash
pnpm build
```
- **Result**: `Compiled successfully` without warning or error.
