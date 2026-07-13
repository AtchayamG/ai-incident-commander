# Incident Commander AI — Evidence Checklist

This checklist audits every product capability claimed in the **Demo Script** and **Storyboard**, mapping them directly to source code, tests, and API artifacts. This ensures absolute honesty and separates currently verified features from planned milestones.

---

## 1. Core Platform Capabilities & Verification Status

### 1.1 Incident Ingest & Normalization (M0–M1)
* **Claim:** HTTP 500 error rate spike detection (0.2% to 12.4% for `checkout-api`).
* **Technical Artifacts:**
  - Telemetry source file: [alerts.json](../../services/api/fixtures/checkout-api/telemetry/alerts.json)
  - Telemetry test: [test_incidents_api.py](../../services/api/tests/test_incidents_api.py)
* **Verification Status:** **CURRENTLY PROVEN**

### 1.2 Deployment & Commit Correlation (M2)
* **Claim:** Correlation of version `2026.07.13.4` at 10:02 UTC and commit `c7f2e9a` on the incident timeline.
* **Technical Artifacts:**
  - Deployment log: [deploys.json](../../services/api/fixtures/checkout-api/deploys/deploys.json)
  - Correlation logic test: [test_timeline_determinism.py](../../services/api/tests/test_timeline_determinism.py)
* **Verification Status:** **CURRENTLY PROVEN**

### 1.3 Boundary Data Redaction (M2)
* **Claim:** Automatic regex-based redaction of secrets, DB credentials, and tokens in ingested logs.
* **Technical Artifacts:**
  - Redaction service: [redaction.py](../../services/api/app/security/redaction.py)
  - Redaction unit tests: [test_redaction.py](../../services/api/tests/test_redaction.py)
* **Verification Status:** **CURRENTLY PROVEN**

### 1.4 Evidence-Grounded Hypothesis Generation (M3)
* **Claim:** Ranked root-cause hypotheses with confidence ratings and exact evidence citations to timeline facts (simulated-fixture gateway).
* **Technical Artifacts:**
  - Schema definition: [investigation.py](../../services/api/app/domain/investigation.py)
  - Unit tests: [test_investigation.py](../../services/api/tests/test_investigation.py)
* **Verification Status:** **CURRENTLY PROVEN** in deterministic fixture mode. The optional OpenAI Responses structured-output gateway is implemented, mock-tested, and separately proven by one bounded credentialed GPT-5.6 receipt using sparse synthetic input and `store=false`.

### 1.5 Approval Gate 1: Plan Approval (M4)
* **Claim:** Blocking workspace creation and patching until the human reviews and approves the remediation plan.
* **Technical Artifacts:**
  - State machine policy: [policy.py](../../services/api/app/workflow/policy.py)
  - Approval router: [approvals.py](../../services/api/app/api/routes/approvals.py)
  - E2E Playwright tests: [Playwright Scenarios](../../apps/web/e2e) (Chromium checks passing)
* **Verification Status:** **CURRENTLY PROVEN**

### 1.6 Bounded Codex Patching (M5)
* **Claim:** In deterministic demo mode, an explicitly simulated fixture code-agent operates in an isolated temporary workspace, applying the expected minimal patch and regression test. A live Codex adapter exists but final live proof remains pending M9.
* **Technical Artifacts:**
  - Sandbox executor: [executor.py](../../services/api/app/sandbox/executor.py)
  - Sandbox workspace: [workspace.py](../../services/api/app/sandbox/workspace.py)
  - Sandbox tests: [test_sandbox_executor.py](../../services/api/tests/test_sandbox_executor.py)
* **Verification Status:** **CURRENTLY PROVEN**

### 1.7 Deterministic Verification Checks (M6)
* **Claim:** Six automated verify checks (`targeted_test`, `test`, `lint`, `typecheck`, `regression_test`, and `risk_review`).
* **Technical Artifacts:**
  - Verifier engine: [verifier.py](../../services/api/app/sandbox/verifier.py)
  - Verification tests: [test_verification.py](../../services/api/tests/test_verification.py)
* **Verification Status:** **CURRENTLY PROVEN** (Passing verification advances to the separate PR-approval boundary).

### 1.8 Risk Review & Rollback Instructions (M6)
* **Claim:** Unified dashboard displaying git diff side-by-side, risk level audits, and git rollback commands.
* **Technical Artifacts:**
  - Risk analyzer: [risk.py](../../services/api/app/workflow/risk.py)
  - Frontend Risk UI components: [Review page E2E verification](../testing/m4-approval-ui.md)
* **Verification Status:** **CURRENTLY PROVEN**

### 1.9 Approval Gate 2: PR Action & Write API (M7)
* **Claim:** Secondary approval gate authorizes creation of one idempotent draft-PR artifact.
* **Technical Artifacts:**
  - Resolution API and mapping: [incidents.py](../../services/api/app/api/routes/incidents.py)
  - Approval and idempotency tests: [test_m7_pr_communications.py](../../services/api/tests/test_m7_pr_communications.py)
  - Real browser golden path: [m7-golden-resolution.spec.ts](../../apps/web/e2e/m7-golden-resolution.spec.ts)
* **Verification Status:** **CURRENTLY PROVEN** for the deterministic simulated provider. Optional GitHub behavior is mocked only; no live branch write or hosted PR is claimed.

### 1.10 Communications & Postmortem Compilation (M7)
* **Claim:** Compilation of technical/stakeholder drafts and exporting structured Postmortem Markdown.
* **Technical Artifacts:**
  - Typed contracts: [contracts.py](../../services/api/app/domain/contracts.py)
  - Persistence and generation: [pipeline.py](../../services/api/app/workflow/pipeline.py)
  - Browser contract coverage: [m7-resolution.spec.ts](../../apps/web/e2e/m7-resolution.spec.ts)
* **Verification Status:** **CURRENTLY PROVEN** for local drafts and one evidence-linked postmortem. Slack delivery is not implemented or claimed.

### 1.11 Product Polish (M8)
* **Claim:** Truthful onboarding, derived workflow metrics, explicit API health states, accessible empty states, and responsive layouts.
* **Technical Artifacts:**
  - Dashboard: [page.tsx](../../apps/web/app/page.tsx)
  - Product-polish browser tests: [m8-product-polish.spec.ts](../../apps/web/e2e/m8-product-polish.spec.ts)
* **Verification Status:** **CURRENTLY PROVEN**. The local Docker API/web images build and the real containerized browser path reaches `RESOLUTION_DRAFTED` with zero console errors. PostgreSQL and production deployment are not claimed.

### 1.12 Multi-Run Reliability, Secret Scan & Submission (M9)
* **Claim:** Safe execution across five consecutive E2E runs without latency spikes or flakiness, repo secret scanning, and final submission packaging.
* **Verification Status:** **CURRENTLY PROVEN** for five consecutive deterministic CLI runs, the full-history secret scan, and one complete containerized browser run. Final recording and credentialed OpenAI/Codex smoke proof remain pending.

---

## 2. Quantitative Verification Metrics

The following metrics are extracted directly from the verified test runs in the current workspace:

* **Backend Unit & Integration Tests:** 185 passing
* **Backend Coverage & Code Standards:** Ruff check pass, Strict `mypy` pass (46 app files)
* **Frontend Component Tests:** 20 passing
* **Shared contract tests:** 6 passing
* **End-to-End browser scenarios:** 20 passing (via Playwright/Chromium)
* **Database migrations:** Initial schema and evidence/patch fields applied via Alembic.
* **Verification phases verified:** 6/6 passing under `test_verification.py`.
