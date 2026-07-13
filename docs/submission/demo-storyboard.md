# Incident Commander AI — Submission Storyboard

This shot-by-shot storyboard is optimized for Devpost judging, demonstrating our technical novelty, safety boundaries, and the value of a deterministic, human-approved incident response workflow.

---

### Shot 1: The Incident Alert Room (Problem)
* **Visual Representation:**
  - A clean, modern dark-mode Incident Room dashboard.
  - A prominent red graph showing a sharp HTTP 500 error rate spike from 0.2% to 12.4% on the `checkout-api` service.
  - An active incident card labeled `#INC-2026-0713` marked as `CRITICAL`.
* **Narration Hook:** *"Small engineering teams lack 24/7 SRE coverage. Production failures cause panic, senior developer burnout, and hours spent digging through logs."*
* **Core Message:** Focus on the real-world operational pain point: time-to-resolution and SRE expertise shortage.

---

### Shot 2: Telemetry Ingestion & Security Boundary (Novelty)
* **Visual Representation:**
  - An interactive timeline displaying normalized incident telemetry.
  - A highlighted event for Deployment `version 2026.07.13.4` at 10:02 UTC and a correlated git commit `c7f2e9a`.
  - A log snippet view showing a stack trace pointing to `checkout.ts:L20`.
  - A visual callout highlighting the automatic regex-based redaction of an API credential within the log trace.
* **Narration Hook:** *"Incident Commander AI automatically ingests alerts and correlates them with recent deployments. Our security boundary redacts credentials and secrets in logs before they reach the model."*
* **Core Message:** Security-first data processing. Sensitive logs are sanitized before agent analysis.

---

### Shot 3: Evidence-Grounded Investigation (Diagnosis)
* **Visual Representation:**
  - The "Ranked Hypotheses" tab.
  - Top card: *"Unsafe direct property access on session.discount.code"* with **94% confidence**.
  - A clickable link icon next to the hypothesis that draws a connecting line back to the timeline log trace and commit.
* **Narration Hook:** *"Our investigation engine generates and ranks root-cause hypotheses using structured outputs. Hallucinations are prevented: every claim must cite exact timeline evidence. (The engine currently runs on a deterministic simulated-fixture gateway; final OpenAI-provider integration is pending)."*
* **Core Message:** Rationale over speculation. The system separates facts from inferences.

---

### Shot 4: Bounded Remediation Plan (Approval Gate 1)
* **Visual Representation:**
  - The Remediation Plan modal displaying target files (`checkout.ts`), allowed patch scopes (restore optional discount handling, maximum 40 lines), and a required regression test.
  - A prominent **Approve & Execute Patch** action button.
  - The button is locked until a human engineer reviews and clicks it.
* **Narration Hook:** *"Before changing a single line of code, the system proposes a bounded remediation plan. No edits run automatically. Explicit human approval is required, generating a single-use token to authorize sandbox writes."*
* **Core Message:** First safety gate. The system acts as a supervised operator, never an autonomous agent running wild.

---

### Shot 5: Isolated Candidate Workspace (Bounded Patching)
* **Visual Representation:**
  - An execution log showing the isolated temporary workspace initializing.
  - Demo logs explicitly label the fixture code-agent while it modifies `checkout.ts` and adds the no-discount regression test.
  - Visual boundaries showing denied paths (e.g., configurations, environment settings) blocked from modification.
* **Narration Hook:** *"In deterministic demo mode, an explicitly simulated fixture code-agent works in a temporary, isolated workspace. The live Codex adapter exists, but final live proof remains a Milestone 9 gate."*
* **Core Message:** Isolated side-effects. The patch is developed and verified in a safe zone.

---

### Shot 6: Six-Stage Quality Control (Deterministic Verification)
* **Visual Representation:**
  - A checklist of six deterministic checks turning green:
    1. **targeted_test:** Regression test fails in base code, passes with patch.
    2. **test:** All existing unit/integration tests pass.
    3. **lint:** Code style is verified (Ruff/ESLint).
    4. **typecheck:** TypeScript and Python type safety validated.
    5. **regression_test:** Bounded regression test scope check.
    6. **risk_review:** Bounded risk review verification.
* **Narration Hook:** *"The platform enforces six deterministic checks—targeted_test, test, lint, typecheck, regression_test, and risk_review—to decide whether this candidate can advance."*
* **Core Message:** Deterministic code quality. We do not rely on LLM self-grading; we compile and run actual tests.

---

### Shot 7: Risk Review Package (Verification & Rollback)
* **Visual Representation:**
  - A unified Review screen displaying a side-by-side git diff (2 files, under 40 lines changing `discount.code` to `discount?.code ?? null`).
  - Risk Audit Badge: **LOW RISK** (restricted scope, passing test suite).
  - The bounded rollback guidance: revert the candidate patch; once the regression test is retained, revert suspect commit `c7f2e9a` if needed.
* **Narration Hook:** *"The engineer reviews the review package: a side-by-side git diff showing only the minimal fix, automated risk review, and rollback instructions."*
* **Core Message:** Full inspectability. The human operator has all the context needed to authorize the fix.

---

### Shot 8: Pull Request Package (Approval Gate 2)
* **Visual Representation:**
  - A second approval action: **Approve & Create PR**.
  - A description explaining that demo mode creates a simulated offline draft-PR artifact.
* **Narration Hook:** *"A second artifact-bound approval prevents automatic repository writes. In deterministic demo mode, the approved action records a clearly labeled simulated draft-PR package."*
* **Core Message:** Honest provenance and human control. No branch write or hosted PR is implied by the fixture artifact.

---

### Shot 9: Incident Closure & Postmortem (Resolution Artifacts)
* **Visual Representation:**
  - The final incident state displaying **RESOLUTION_DRAFTED**.
  - Separate technical and stakeholder drafts plus an evidence-linked postmortem timeline.
* **Narration Hook:** *"The approved resolution package now includes audience-specific updates and one postmortem grounded in the same incident evidence and verification artifacts."*
* **Core Message:** Operational closure remains auditable and does not overstate simulated external actions.

---

### Shot 10: Technical Architecture Close (Architecture Close)
* **Visual Representation:**
  - A system context diagram showing Next.js, FastAPI, SQLAlchemy persistence, deterministic fixture gateways, and optional live OpenAI/Codex adapters pending final proof.
  - An engineering evidence badge: **149 Backend Tests | Ruff & Strict Mypy (44 Files) | 20 Web + 6 Contract Tests | 20 Playwright Scenarios | RESOLUTION_DRAFTED**.
* **Narration Hook:** *"Incident Commander AI turns a confusing production alert into a verified, human-approved fix and a complete audit trail—keeping the team in control every step of the way."*
* **Core Message:** Robust local validation and structured architecture.
