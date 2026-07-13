# Incident Commander AI — Demo Script

**Target Duration:** 2 minutes 30 seconds  
**Objective:** Guide a Devpost judge through a step-by-step walkthrough of Incident Commander AI resolving a production regression in the `checkout-api` service.

> [!IMPORTANT]
> **Simulated vs. Live Honesty Policy:** The golden workflow is verified locally through `RESOLUTION_DRAFTED` and uses explicitly simulated fixtures for investigation, code generation, and the draft PR. A separate credentialed GPT-5.6 Responses proof passed; Codex CLI repository-work proof, final PostgreSQL/worker validation, and external submission actions are never implied by the offline demo.

---

## Demo Walkthrough Table

| Timestamp | Visual / Screen Shown | Operator Action | Narration Script | Technical Evidence / Status |
| :--- | :--- | :--- | :--- | :--- |
| **0:00–0:15** | **Dashboard & Alert Room**<br>- Service: `checkout-api`<br>- Active incident listed<br>- Graph showing 500 error rate spike (0.2% to 12.4%) | Click on active incident `#INC-2026-0713`. | *"When production breaks for a small engineering team, senior developers waste crucial time chasing logs and checking recent changes. Incident Commander AI turns this chaos into a structured, evidence-backed resolution flow."* | **[PROVEN (M0-M1)]**<br>Telemetry intake captures 500 error spike. |
| **0:15–0:35** | **Evidence Timeline**<br>- Deployment correlation widget<br>- Stack trace points to `checkout.ts`<br>- Git commit correlation showing commit `c7f2e9a` | Scroll through timeline; click on commit `c7f2e9a` and log snippet. | *"Our platform immediately normalizes the alert, correlates it with version `2026.07.13.4` deployed minutes earlier, and isolates the stack trace. Every log line is filtered at the ingestion boundary to ensure no sensitive credentials or secrets escape."* | **[PROVEN (M2)]**<br>Redacted log samples and deployment timestamps correlated. |
| **0:35–0:55** | **Hypotheses & Diagnosis**<br>- Ranked hypothesis card (94% confidence)<br>- Unsafe access to `discount.code`<br>- Inspectable evidence citations | Click on the timeline citation link under the top hypothesis. | *"Using structured outputs from our investigation engine, the system ranks the most likely root causes. It separates raw facts from logical inferences, and every claim points to inspectable evidence on the timeline to reduce unsupported conclusions."* | **[PROVEN (M3 FIXTURE PATH)]**<br>Deterministic hypothesis generation with exact evidence provenance. Final OpenAI-provider proof remains pending M9. |
| **0:55–1:15** | **Remediation Plan & Gate 1**<br>- Proposed patch scope (restore optional chaining)<br>- Automated regression test plan<br>- Prominent 'Approve & Run Patch' button | Review the plan and click **Approve & Execute Patch**. | *"Before changing a single line of code, the system proposes a bounded remediation plan. No edits run automatically. Human approval is strictly required, generating a single-use token to authorize the sandbox workspace."* | **[PROVEN (M4)]**<br>Approval Gate 1 blocks workspace mutation until authorized. |
| **1:15–1:45** | **Sandbox & Verification**<br>- Sandbox execution log<br>- 6 passing verification phases:<br>  1. `targeted_test`<br>  2. `test`<br>  3. `lint`<br>  4. `typecheck`<br>  5. `regression_test`<br>  6. `risk_review` | Watch the demo execution complete; click **View Review Package** when finished. | *"Incident Commander spins up an isolated workspace. In deterministic demo mode, a fixture code-agent applies the minimal candidate fix and regression test. The platform then runs six checks—targeted_test, test, lint, typecheck, regression_test, and risk_review—to prove the candidate."* | **[PROVEN (M5-M6 FIXTURE PATH)]**<br>Explicitly simulated candidate patching and real offline verification; final live Codex proof remains pending M9. |
| **1:45–2:05** | **Risk Review & Gate 2**<br>- Side-by-side diff<br>- Rollback commands<br>- **Approve & Create PR** action | Review the diff, then grant the separate PR approval. | *"The engineer reviews the minimal diff, automated risk review, and rollback instructions. A second artifact-bound approval is required before any resolution action. In this offline demo, that action creates a clearly labeled simulated draft-PR artifact—never a hidden repository write."* | **[PROVEN (M7 SIMULATED PATH)]**<br>Separate approval, stale-binding rejection, risk blocking, idempotency, and simulated provenance are tested. Optional GitHub behavior is mocked only. |
| **2:05–2:25** | **Closure & Postmortem**<br>- Technical and stakeholder drafts<br>- Evidence-linked postmortem timeline | Review the generated resolution artifacts. | *"After the approved resolution artifact is recorded, the platform prepares separate technical and stakeholder updates plus one evidence-linked postmortem, keeping every conclusion auditable."* | **[PROVEN (M7 LOCAL PATH)]**<br>Typed artifacts persist and render; the real local-API browser path reaches `RESOLUTION_DRAFTED`. |
| **2:25–2:30** | **Outro / Pitch Close**<br>- Main dashboard showing `#INC-2026-0713` marked as `RESOLUTION_DRAFTED` | Return to the dashboard. | *"Incident Commander AI turns a confusing production alert into a verified, human-approved resolution package and complete audit trail—keeping the team in control every step of the way."* | **[PROVEN (M1-M8)]**<br>Local API browser scenario: alert -> plan approval -> patch -> six checks -> PR approval -> simulated resolution artifacts. |

---

## Presenter Action Checklist & Backup Plan

### If Live Demo Environment is Available:
1. Run `pnpm dev` and `uv run uvicorn app.main:app` (or use local aliases).
2. Reset the demo database by hitting the `POST /api/v1/incidents/reset-demo` endpoint.
3. Follow the operator actions in the table above exactly, allowing up to 10 seconds for the simulated investigation and fixture code-agent responses in Demo Mode.
4. Grant the second approval, show the explicitly simulated draft-PR artifact, communications, postmortem, and final `RESOLUTION_DRAFTED` state.

### If Live Demo fails (or for judge offline viewing):
- Use the recorded backup screen capture representing the local-API browser scenario.
- Point to the verified test outputs (`185 backend tests pass`, `20 frontend tests pass`, `6 contract tests pass`, `22 Chromium Playwright scenarios`, five complete demo runs, and a clean full-history Gitleaks scan).
- Navigate the judge to the verified logs under `docs/project/agent-runs/` to inspect the actual test runs and diff outputs, or mark the final recording/evidence bundle pending.
