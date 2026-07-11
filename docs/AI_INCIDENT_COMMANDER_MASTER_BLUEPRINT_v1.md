# AI Incident Commander for Small Engineering Teams
## Master Product Blueprint, Technical Architecture, and Autonomous Codex Build Contract

**Document version:** 1.0  
**Target event:** OpenAI Build Week, July 2026  
**Working product name:** **Incident Commander AI**  
**Repository codename:** `incident-commander-ai`  
**Primary objective:** Deliver a polished, runnable, judge-friendly product that turns a production incident into an evidence-backed diagnosis, a verified code patch, a reviewable pull request, and a postmortem—without allowing uncontrolled production changes.

---

# 0. Codex Execution Directive

This document is the source of truth for autonomous implementation.

Codex must:

1. Build a complete vertical slice before expanding scope.
2. Prefer a reliable, demonstrable product over speculative breadth.
3. Implement the P0 scope first, then P1 only after every P0 quality gate passes.
4. Keep all model names, provider URLs, credentials, and integration settings configurable.
5. Use strict typed contracts between frontend, backend, agents, workers, and integrations.
6. Record every material architectural decision in `/docs/adr`.
7. Maintain the project status files described in Section 28.
8. Run linting, type checks, tests, migrations, seed scripts, and the demo scenario after every milestone.
9. Never merge, deploy, roll back, delete infrastructure, or modify a protected branch automatically.
10. Require a human approval checkpoint before creating a pull request in a real repository or executing any write-capable external action.
11. Use mocks only behind interfaces. The demo may use fixtures, but the architecture must support real integrations.
12. Do not silently fake a successful analysis, test, patch, or integration result. Clearly mark simulated evidence.
13. Continue autonomously through recoverable failures. Stop only for missing credentials, an irreversible action, an ambiguous product decision that changes scope, or a platform limitation.
14. Leave the repository runnable with one documented command for local development and one documented command for the complete demo.
15. Treat this blueprint as a contract. Any deviation must be documented in an ADR with the reason, trade-off, and migration path.

---

# 1. Executive Summary

Small engineering teams lose critical time during incidents because telemetry, source code, deployment history, ownership, runbooks, and communication are spread across different tools. Senior engineers become human routers: they collect logs, reconstruct what changed, identify the likely root cause, prepare a patch, run tests, update stakeholders, and write the postmortem.

**Incident Commander AI** compresses that workflow into a supervised agentic incident room.

A user can submit an alert, stack trace, failed deployment, or incident webhook. The platform then:

1. Normalizes the incident.
2. Collects evidence from configured sources.
3. Builds a timeline.
4. Generates and ranks root-cause hypotheses.
5. Maps the failure to relevant files and recent changes.
6. Creates a remediation plan.
7. Uses Codex inside an isolated workspace to implement a minimal patch.
8. Runs verification commands and summarizes the evidence.
9. Produces a review package containing the diff, risk analysis, tests, rollback guidance, and confidence.
10. After explicit approval, optionally creates a branch and draft pull request.
11. Produces stakeholder updates and a structured postmortem.

The product is not an unsupervised production operator. It is a **high-speed, evidence-grounded, human-approved incident response system**.

## 1.1 Winning demo statement

> “Production breaks. Incident Commander gathers the evidence, finds the regression, patches it with Codex, proves the fix with tests, prepares the PR, and writes the postmortem—while keeping a human in control.”

## 1.2 Core differentiation

This is not “chat with logs.”

The differentiated product loop is:

```text
ALERT
  → EVIDENCE
  → HYPOTHESES
  → CODE MAPPING
  → PATCH
  → VERIFICATION
  → HUMAN APPROVAL
  → PR PACKAGE
  → POSTMORTEM
```

The visible artifacts are as important as the conversational interface. Judges must be able to inspect what the system believed, which evidence supported it, what changed, how the change was tested, and where the human approved it.

---

# 2. Product Goals and Success Metrics

## 2.1 Product goals

- Reduce time to first credible hypothesis.
- Reduce time from incident intake to a verified candidate fix.
- Preserve a complete evidence and decision trail.
- Make incident response usable for teams without dedicated SRE staff.
- Demonstrate meaningful use of GPT-5.6 and Codex beyond text generation.
- Deliver a polished, coherent workflow that works end-to-end in a live demo.

## 2.2 Hackathon success metrics

| Metric | Target |
|---|---:|
| Time from demo alert to ranked hypotheses | under 30 seconds |
| Time from approval to candidate patch | under 90 seconds for fixture repository |
| Demo completion reliability | 5 successful runs in a row |
| Evidence claims with source references | 100% of root-cause claims |
| Patch verification | at least unit test + lint/type check |
| Human approval coverage | 100% of external write actions |
| Unhandled frontend errors during demo | 0 |
| Unhandled backend errors during demo | 0 |
| P0 automated test pass rate | 100% |
| Judge comprehension | product value understandable in first 20 seconds |

## 2.3 Product metrics for a future production version

- Mean time to acknowledge.
- Mean time to diagnosis.
- Mean time to remediation candidate.
- Percentage of incidents with a usable timeline.
- Percentage of proposed patches accepted with minor or no edits.
- False root-cause rate.
- Verification escape rate.
- Human approval latency.
- Estimated engineer-hours saved.
- Incident recurrence rate after approved fixes.

---

# 3. Target Users

## 3.1 Primary persona: Small-team tech lead

- Team size: 3–25 engineers.
- No dedicated 24/7 SRE team.
- Owns architecture, delivery, and incident response.
- Uses GitHub, CI, an error tracker, and chat.
- Needs rapid evidence and a reviewable fix, not another dashboard.

## 3.2 Secondary persona: On-call engineer

- Receives alerts outside normal hours.
- Needs a concise incident summary and probable blast radius.
- Wants the system to identify recent risky changes and relevant owners.
- Must remain in control of code and production actions.

## 3.3 Secondary persona: Engineering manager or founder

- Wants business impact and status, not raw logs.
- Needs accurate stakeholder updates.
- Needs a postmortem and follow-up actions after resolution.

---

# 4. Problem Definition

During an incident, engineers repeatedly perform the same high-cost coordination tasks:

- Find the failing service and affected endpoints.
- Collect error messages, traces, logs, recent deployments, and commits.
- Determine whether the incident is new, recurring, or correlated with a change.
- Locate the relevant source files.
- Form and test hypotheses.
- Create the smallest safe fix.
- Validate the fix.
- Explain current status to non-technical stakeholders.
- Document the incident after recovery.

Existing monitoring tools usually stop at detection. Coding assistants usually start with a developer prompt. Incident Commander connects detection, diagnosis, code remediation, validation, communication, and institutional learning in one supervised workflow.

---

# 5. Scope

## 5.1 P0 — Required for submission

The submission is not complete unless all P0 items work.

### Incident intake
- Manual incident creation.
- Generic JSON webhook intake.
- Built-in deterministic demo incident generator.
- Severity, service, environment, title, summary, and raw payload.

### Evidence
- Ingest fixture logs and stack traces.
- Ingest Git commit/deployment history from a fixture provider.
- Connect to one real GitHub repository or a local Git repository.
- Store source references for every evidence item.
- Construct a chronological incident timeline.

### Agentic diagnosis
- Produce incident summary.
- Generate at least three root-cause hypotheses.
- Rank hypotheses by confidence.
- Attach supporting and contradicting evidence.
- Identify likely affected files and recent commits.
- Produce an explicit “unknowns” section.

### Codex remediation
- Clone or mount a repository into an isolated workspace.
- Generate a bounded remediation plan.
- Require approval before code modification.
- Use Codex SDK for patch implementation.
- Capture changed files and unified diff.
- Limit the patch to a configured file/change budget.

### Verification
- Run repository-defined checks in the sandbox.
- Capture stdout, stderr, exit code, duration, and artifacts.
- Require at least one relevant test.
- Produce a verification summary.
- Mark the patch as failed when checks fail.

### Review package
- Show root cause, evidence, plan, diff, tests, risks, and rollback guidance.
- Require explicit approval before any external write action.
- Support simulated PR creation.
- Support real draft PR creation when credentials are configured.

### Communication
- Generate technical incident update.
- Generate executive/stakeholder update.
- Generate postmortem with timeline, impact, root cause, resolution, and action items.

### Product experience
- Incident dashboard.
- Incident detail/war-room screen.
- Live workflow timeline.
- Evidence drawer.
- Hypothesis board.
- Diff viewer.
- Approval panel.
- Postmortem view.
- Demo mode with reset.

## 5.2 P1 — Build only after P0 gates pass

- Sentry adapter.
- GitHub Actions failure adapter.
- Slack notification adapter.
- Similar-incident retrieval.
- Runbook retrieval using embeddings.
- Multiple repositories.
- Role-based access control.
- Real-time collaboration.
- Streaming agent events.
- Cost and token dashboard.
- Incident replay.
- One-click export to Markdown/PDF.
- Suggested follow-up GitHub issues.

## 5.3 P2 — Future vision, not required for hackathon

- Production rollback automation.
- Kubernetes and cloud provider actions.
- PagerDuty/Opsgenie integrations.
- Distributed tracing provider integrations.
- Automated canary deployment.
- Automated incident drills.
- Voice incident commander.
- Enterprise SSO and SCIM.
- Policy-as-code for remediation.
- Cross-organization incident knowledge graph.

## 5.4 Explicit non-goals

- The system will not guarantee that a diagnosis is correct.
- The system will not push directly to protected branches.
- The system will not merge pull requests.
- The system will not execute production rollback or deployment in the hackathon version.
- The system will not claim to replace SRE or on-call engineers.
- The system will not ingest unrestricted production secrets.
- The system will not support every observability provider.
- The system will not become a general-purpose coding assistant.

---

# 6. Core User Journeys

## 6.1 Golden path: Failed deployment regression

1. User opens the dashboard.
2. A demo alert appears: elevated 500 errors in `checkout-api`.
3. User opens the incident.
4. The system ingests the error trace, recent deployment, commit list, and repository metadata.
5. The workflow timeline visibly advances:
   - Alert normalized
   - Evidence collected
   - Timeline built
   - Hypotheses generated
   - Code mapped
6. The top hypothesis identifies a null-handling regression introduced in a recent commit.
7. The user expands the evidence and sees:
   - stack trace
   - failing test
   - deployment timestamp
   - matching commit
   - relevant source line
8. The system proposes a minimal remediation plan.
9. The user approves “Create candidate patch.”
10. Codex edits the fixture repository in an isolated workspace.
11. Tests initially fail or a regression test is added.
12. Codex adjusts the patch within the allowed iteration budget.
13. Tests, lint, and type checks pass.
14. The system displays the diff and risk review.
15. The user approves “Create draft PR.”
16. In demo mode, the system creates a simulated PR artifact; in live mode, it creates a real draft PR.
17. The system generates:
   - technical update
   - stakeholder update
   - postmortem draft
18. Dashboard metrics show reduced response time.

## 6.2 Failure path: Insufficient evidence

1. Incident arrives with only a vague alert.
2. Evidence collection finds no logs or deployment correlation.
3. The system refuses to invent a root cause.
4. It displays low confidence and lists required evidence.
5. It recommends safe next actions.
6. Patch generation remains disabled.

## 6.3 Failure path: Patch does not verify

1. Codex creates a candidate patch.
2. Tests fail.
3. The verifier returns structured failures.
4. Codex receives only the relevant failure output.
5. It gets a bounded number of repair attempts.
6. If checks still fail, the workflow stops at `PATCH_FAILED`.
7. The UI clearly states that no PR can be created.

## 6.4 Safety path: High-risk change

1. Proposed diff modifies authentication, payment, database migration, or infrastructure files.
2. Risk policy marks the patch high risk.
3. PR creation is blocked or requires elevated approval.
4. The system suggests a safer diagnostic or mitigation alternative.

---

# 7. Product Requirements

## 7.1 Functional requirements

### FR-001: Incident creation
The system shall allow an authenticated user to create an incident manually or through a webhook.

### FR-002: Normalization
The system shall normalize provider-specific payloads into one internal `IncidentSignal` schema.

### FR-003: Evidence provenance
Every evidence item shall store provider, source identifier, capture timestamp, hash, and display reference.

### FR-004: Evidence-grounded conclusions
Every root-cause claim shall cite one or more evidence IDs. Unsupported claims shall be labeled as hypotheses.

### FR-005: Durable workflow
The incident workflow shall persist its state after every stage and be resumable after process restart.

### FR-006: Human approval
The system shall require explicit approval before:
- modifying a workspace,
- creating a remote branch,
- creating a pull request,
- sending an external notification.

### FR-007: Isolated patching
Code changes and verification shall run in an isolated workspace with limited filesystem and network permissions.

### FR-008: Change budget
The system shall enforce configurable limits:
- maximum files changed,
- maximum lines changed,
- prohibited path patterns,
- maximum repair iterations,
- maximum command duration.

### FR-009: Verification evidence
The system shall store all check commands and results.

### FR-010: External write idempotency
PR creation and notifications shall use idempotency keys and shall not create duplicates on retry.

### FR-011: Auditability
Every agent decision, tool request, approval, external action, and state transition shall be auditable.

### FR-012: Demo reset
A user shall be able to reset the demo tenant and replay the golden incident without manual cleanup.

## 7.2 Non-functional requirements

### Reliability
- All state transitions are persisted.
- Retried jobs are idempotent.
- Provider failures degrade gracefully.
- Demo mode must not depend on external services.

### Performance
- Dashboard initial load under 2 seconds on a normal broadband connection.
- Agent workflow emits a visible progress event at least every 10 seconds.
- Incident summary begins streaming within 5 seconds when supported.

### Security
- Secrets are never sent to model prompts.
- Repository tokens stay server-side.
- Webhooks are authenticated in live mode.
- Logs are redacted before model use.
- All external write actions are permission-gated.

### Accessibility
- Keyboard navigable.
- WCAG AA contrast.
- Status is not communicated by color alone.
- Reduced-motion preference respected.

### Maintainability
- Typed schemas shared across boundaries.
- Provider adapters isolated from domain logic.
- Agent prompts versioned.
- Every workflow stage independently testable.

### Observability
- Structured logs.
- Trace IDs across frontend, API, worker, and model calls.
- Agent trace and cost metrics.
- Workflow duration metrics.
- External provider error metrics.

---

# 8. Recommended Technology Stack

## 8.1 Frontend

- **Next.js** with App Router.
- **React** and TypeScript.
- **Tailwind CSS**.
- **shadcn/ui** or an equivalent accessible component system.
- **TanStack Query** for server state.
- **Zustand** only for local workflow/UI state.
- **Monaco Diff Editor** or a lightweight diff viewer.
- **Recharts** for simple incident metrics.
- Server-Sent Events for live workflow updates.

## 8.2 Backend and orchestration

- **Python 3.12**.
- **FastAPI** for APIs and webhook endpoints.
- **Pydantic v2** for contracts.
- **OpenAI Agents SDK** for manager-style orchestration, tools, guardrails, sessions, and tracing.
- **OpenAI Responses API** for bounded structured subtasks.
- **OpenAI Codex SDK** for repository-aware diagnosis and code modification.
- **SQLAlchemy 2** and Alembic.
- **Celery + Redis** or a small durable worker abstraction backed by Redis.
- Prefer a state-machine workflow service over hidden recursive agent loops.

## 8.3 Persistence

- **PostgreSQL** as primary storage.
- **pgvector** only for P1 similar-incident/runbook retrieval.
- **Redis** for queues, locks, rate limiting, and ephemeral event fanout.
- **S3-compatible object storage** for large logs, workspace artifacts, diffs, and reports.
- Local filesystem adapter in demo mode.

## 8.4 Integrations

- **GitHub App** or fine-grained token for repository/PR integration.
- Generic webhook adapter.
- Fixture telemetry provider.
- Optional Sentry adapter.
- Optional Slack adapter.

## 8.5 Deployment

Hackathon-friendly production topology:

- Frontend: Vercel or equivalent.
- API and worker: Railway, Render, Fly.io, or a small container host.
- Database: managed PostgreSQL.
- Redis: managed Redis.
- Artifact storage: S3-compatible bucket.
- Demo runner/sandbox: dedicated container host; do not run arbitrary code in a serverless function.

## 8.6 Technology rationale

- Python is selected because the OpenAI Agents SDK has a mature Python-first orchestration model and supports guardrails, sessions, tracing, human-in-the-loop, and sandbox-oriented workflows.
- Codex SDK is isolated behind a `CodeAgentGateway`, allowing model/runtime changes without rewriting domain logic.
- The frontend is independently deployable and cannot access model or repository credentials.
- The workflow is explicit and durable rather than relying on one opaque prompt.

---

# 9. High-Level Architecture

```mermaid
flowchart LR
    U[Engineer / Tech Lead] --> WEB[Next.js Web App]
    ALERT[Alert / Webhook / Demo Generator] --> API[FastAPI API]

    WEB --> API
    API --> AUTH[Auth & Tenant Service]
    API --> DB[(PostgreSQL)]
    API --> OBJ[(Artifact Storage)]
    API --> BUS[Redis Queue / Event Bus]

    BUS --> WORKER[Incident Workflow Worker]
    WORKER --> ORCH[Incident Orchestrator]
    ORCH --> AGENTS[OpenAI Agents SDK]
    ORCH --> RESP[Responses API]
    ORCH --> CODEX[Codex SDK Gateway]

    ORCH --> EVIDENCE[Evidence Adapter Layer]
    EVIDENCE --> GH[GitHub / Git]
    EVIDENCE --> TEL[Logs / Sentry / Fixture Telemetry]
    EVIDENCE --> DEPLOY[CI / Deployment History]
    EVIDENCE --> RUNBOOK[Runbook Store]

    CODEX --> SANDBOX[Ephemeral Repository Sandbox]
    SANDBOX --> TESTS[Test / Lint / Type Check Runner]

    ORCH --> POLICY[Policy & Approval Engine]
    POLICY --> APPROVAL[Human Approval]
    APPROVAL --> GHWRITE[Draft PR / Branch]
    APPROVAL --> NOTIFY[Slack / Email Update]

    ORCH --> TRACE[Tracing / Metrics / Audit]
    API --> SSE[SSE Event Stream]
    SSE --> WEB
```

## 9.1 Architectural principles

1. **Evidence before inference.**
2. **Plans before writes.**
3. **Human approval before external effects.**
4. **Minimal patch before broad refactor.**
5. **Verification before PR.**
6. **Durable state before UI optimism.**
7. **Provider adapters before provider coupling.**
8. **Typed output before free-form parsing.**
9. **Deterministic policies around probabilistic models.**
10. **Demo determinism without pretending fixtures are live production data.**

---

# 10. Bounded Contexts

## 10.1 Incident Management

Owns:
- incident identity,
- status,
- severity,
- service,
- environment,
- impact,
- lifecycle,
- human assignments.

## 10.2 Evidence Management

Owns:
- normalized evidence,
- provenance,
- redaction,
- deduplication,
- timeline events,
- source references.

## 10.3 AI Investigation

Owns:
- summaries,
- hypotheses,
- confidence,
- contradictions,
- unknowns,
- recommended next evidence.

## 10.4 Remediation

Owns:
- remediation plan,
- workspace,
- Codex thread,
- patch attempts,
- diff,
- validation results.

## 10.5 Policy and Approval

Owns:
- prohibited actions,
- risk level,
- approval requests,
- approvers,
- decisions,
- expiration.

## 10.6 External Actions

Owns:
- GitHub branch/PR creation,
- notifications,
- idempotency,
- provider receipts.

## 10.7 Communications and Learning

Owns:
- status updates,
- postmortems,
- action items,
- similar incident memory.

---

# 11. Incident Workflow State Machine

```mermaid
stateDiagram-v2
    [*] --> RECEIVED
    RECEIVED --> NORMALIZING
    NORMALIZING --> COLLECTING_EVIDENCE
    COLLECTING_EVIDENCE --> EVIDENCE_READY
    COLLECTING_EVIDENCE --> NEEDS_INPUT

    EVIDENCE_READY --> INVESTIGATING
    INVESTIGATING --> HYPOTHESES_READY
    INVESTIGATING --> NEEDS_INPUT

    HYPOTHESES_READY --> PLANNING_REMEDIATION
    PLANNING_REMEDIATION --> PLAN_READY
    PLANNING_REMEDIATION --> NO_SAFE_REMEDIATION

    PLAN_READY --> WAITING_PATCH_APPROVAL
    WAITING_PATCH_APPROVAL --> PATCHING: approved
    WAITING_PATCH_APPROVAL --> CANCELLED: rejected

    PATCHING --> VERIFYING
    PATCHING --> PATCH_FAILED

    VERIFYING --> REVIEW_READY: checks pass
    VERIFYING --> PATCHING: repair budget remains
    VERIFYING --> PATCH_FAILED: repair budget exhausted

    REVIEW_READY --> WAITING_PR_APPROVAL
    WAITING_PR_APPROVAL --> CREATING_PR: approved
    WAITING_PR_APPROVAL --> REVIEW_READY: rejected / revise

    CREATING_PR --> PR_READY
    CREATING_PR --> EXTERNAL_ACTION_FAILED

    PR_READY --> RESOLUTION_DRAFTED
    REVIEW_READY --> RESOLUTION_DRAFTED: simulated mode

    RESOLUTION_DRAFTED --> CLOSED
    NEEDS_INPUT --> COLLECTING_EVIDENCE: evidence supplied
    PATCH_FAILED --> PLAN_READY: manual retry
    EXTERNAL_ACTION_FAILED --> WAITING_PR_APPROVAL: retry
    CANCELLED --> [*]
    CLOSED --> [*]
```

## 11.1 Terminal states

- `CLOSED`
- `CANCELLED`
- `NO_SAFE_REMEDIATION`

## 11.2 Recoverable states

- `NEEDS_INPUT`
- `PATCH_FAILED`
- `EXTERNAL_ACTION_FAILED`

## 11.3 State transition rules

- Only the workflow service changes workflow state.
- Every transition writes an append-only event.
- Duplicate transition commands must be idempotent.
- UI status is derived from server state.
- Agent output never changes state directly; it returns a typed proposal evaluated by deterministic code.

---

# 12. Multi-Agent Design

Use **manager-style orchestration**. The Incident Commander owns the workflow and invokes specialist agents as tools. Specialists do not independently perform external write actions.

## 12.1 Agent roster

### A. Incident Commander

**Purpose:** Owns the incident objective, stage selection, and final synthesis.

**Inputs**
- incident metadata,
- current state,
- available evidence,
- stage results,
- policy constraints.

**Outputs**
- next stage recommendation,
- incident summary,
- escalation or missing-evidence request,
- final resolution summary.

**Must not**
- write code,
- create a PR,
- execute shell commands,
- invent unavailable evidence.

### B. Evidence Triage Agent

**Purpose:** Converts raw telemetry into normalized, relevant evidence.

**Responsibilities**
- classify signal type,
- deduplicate repeated errors,
- redact sensitive values,
- identify service/environment,
- extract timestamps, stack frames, request IDs, versions, and commit identifiers,
- request missing evidence.

**Output contract**
- normalized evidence records,
- relevance score,
- redaction report,
- missing evidence list.

### C. Timeline and Correlation Agent

**Purpose:** Builds a cause-oriented timeline.

**Responsibilities**
- correlate incident onset with deploys and commits,
- detect first occurrence,
- identify error-rate changes,
- highlight temporal gaps,
- separate correlation from causation.

### D. Root Cause Analyst

**Purpose:** Produces ranked, falsifiable hypotheses.

**Each hypothesis must contain**
- concise claim,
- confidence from 0 to 1,
- supporting evidence IDs,
- contradicting evidence IDs,
- assumptions,
- falsification test,
- likely files/components,
- likely blast radius.

### E. Remediation Planner

**Purpose:** Produces the smallest safe change plan.

**Responsibilities**
- define intended behavior,
- identify files likely to change,
- define regression test,
- define verification commands,
- estimate risk,
- identify rollback method,
- respect change budget.

### F. Codex Repair Agent

**Purpose:** Uses Codex SDK in a controlled workspace.

**Responsibilities**
- inspect repository,
- validate the plan against actual code,
- add or update a regression test,
- implement a minimal patch,
- avoid unrelated refactoring,
- provide changed-file summary.

**Permissions**
- read-only during exploration,
- workspace-write only after approval,
- no production credentials,
- network off by default,
- no remote Git push.

### G. Verification Agent

**Purpose:** Interprets deterministic check results.

**Responsibilities**
- run configured test/lint/type-check commands through tools,
- map failures to likely causes,
- decide whether a repair attempt is justified,
- summarize proof and remaining risk.

**Important**
The agent does not declare success by prose. Success requires deterministic command exit criteria.

### H. Risk and Security Reviewer

**Purpose:** Independently review the proposed diff.

**Checks**
- secret exposure,
- auth/payment/data migration impact,
- unsafe command execution,
- broad change scope,
- missing tests,
- dependency changes,
- infrastructure changes,
- weakened validation,
- logging of sensitive data.

### I. Communications Agent

**Purpose:** Generate audience-specific updates.

**Outputs**
- 5-line technical update,
- 3-line stakeholder update,
- incident resolution note,
- postmortem draft,
- action items with owner placeholders and priority.

---

# 13. Agent Orchestration Sequence

```mermaid
sequenceDiagram
    actor User
    participant UI
    participant API
    participant WF as Workflow Service
    participant EC as Evidence Collectors
    participant IC as Incident Commander
    participant RCA as Root Cause Analyst
    participant RP as Remediation Planner
    participant Policy
    participant Codex
    participant Sandbox
    participant Verify
    participant GitHub

    User->>UI: Create/open incident
    UI->>API: POST /incidents
    API->>WF: Enqueue workflow
    WF->>EC: Collect logs, deploys, commits, repo context
    EC-->>WF: Evidence bundle + provenance
    WF->>IC: Summarize evidence and unknowns
    IC-->>WF: Structured incident assessment
    WF->>RCA: Generate ranked hypotheses
    RCA-->>WF: Hypotheses with citations
    WF->>RP: Propose bounded remediation
    RP-->>WF: Plan + tests + risk
    WF->>Policy: Evaluate plan
    Policy-->>UI: Approval required
    User->>UI: Approve patch
    UI->>API: POST approval decision
    API->>WF: Resume
    WF->>Codex: Start controlled repository thread
    Codex->>Sandbox: Inspect and patch workspace
    Sandbox-->>Codex: Diff and command output
    Codex-->>WF: Candidate patch
    WF->>Verify: Run deterministic checks
    Verify->>Sandbox: test + lint + typecheck
    Sandbox-->>Verify: Results
    Verify-->>WF: Verification report
    WF->>Policy: Diff risk review
    Policy-->>UI: PR approval required
    User->>UI: Approve draft PR
    UI->>API: Approval
    WF->>GitHub: Create branch + draft PR
    GitHub-->>WF: PR reference
    WF-->>UI: Resolution + postmortem artifacts
```

---

# 14. Tool Contracts

Agents may call tools only through typed wrappers.

## 14.1 Evidence tools

```python
class SearchLogsInput(BaseModel):
    incident_id: UUID
    service: str
    environment: str
    start_time: datetime
    end_time: datetime
    query: str
    limit: int = Field(default=200, le=1000)

class SearchLogsResult(BaseModel):
    items: list["EvidenceItem"]
    truncated: bool
    provider_latency_ms: int
    simulated: bool
```

Other required tools:

- `get_recent_deployments`
- `get_recent_commits`
- `get_repository_tree`
- `read_repository_files`
- `search_repository`
- `get_ci_failures`
- `get_runbooks`
- `get_similar_incidents` (P1)

## 14.2 Workspace tools

- `create_ephemeral_workspace`
- `clone_or_mount_repository`
- `set_workspace_mode`
- `run_allowed_command`
- `read_workspace_file`
- `write_workspace_patch`
- `get_workspace_diff`
- `destroy_workspace`

## 14.3 External action tools

- `create_remote_branch`
- `create_draft_pull_request`
- `post_slack_update`
- `create_followup_issue`

Every external action input must include:
- `incident_id`
- `approval_id`
- `idempotency_key`
- `requested_by`
- `dry_run`

## 14.4 Prohibited generic tools

Do not expose unrestricted versions of:
- arbitrary shell,
- arbitrary network fetch,
- arbitrary filesystem access,
- raw SQL,
- unrestricted GitHub API,
- secret manager reads.

---

# 15. Prompt and Output Design

## 15.1 Prompt layers

Every agent prompt is assembled from:

1. System role and non-negotiable safety rules.
2. Stage objective.
3. Tenant policy.
4. Incident metadata.
5. Evidence index.
6. Relevant evidence content.
7. Tool descriptions.
8. Strict output schema.
9. Token/change budget.
10. Explicit completion criteria.

## 15.2 Prompt rules

- Do not include secrets.
- Do not pass complete repositories into context.
- Prefer retrieval and targeted file reads.
- Include evidence IDs in context and require them in output.
- Separate observations, hypotheses, and conclusions.
- Ask the model to state uncertainty.
- Do not use model-generated shell commands without policy validation.
- Version prompts in `/backend/app/ai/prompts`.
- Store prompt version with each agent run.
- Use low-variance settings for classification and extraction.
- Use stronger reasoning only for root-cause and remediation stages.

## 15.3 Structured output examples

### Root-cause hypothesis

```json
{
  "id": "hyp_01",
  "claim": "The deployment introduced a null dereference when a checkout session has no discount object.",
  "confidence": 0.88,
  "supporting_evidence_ids": ["ev_stack_01", "ev_commit_03", "ev_deploy_02"],
  "contradicting_evidence_ids": [],
  "assumptions": ["The deployed commit matches the repository checkout."],
  "falsification_steps": [
    "Run the checkout test with a session that has no discount object."
  ],
  "likely_components": ["checkout-api"],
  "likely_files": ["src/services/checkout.ts"],
  "blast_radius": "Requests without discounts may return HTTP 500."
}
```

### Remediation plan

```json
{
  "summary": "Guard optional discount access and add a regression test.",
  "files_expected": [
    "src/services/checkout.ts",
    "tests/checkout.test.ts"
  ],
  "steps": [
    "Add a failing regression test for a checkout without a discount.",
    "Use optional handling for the discount object.",
    "Run targeted tests, full unit tests, lint, and type check."
  ],
  "verification_commands": [
    "npm test -- checkout.test.ts",
    "npm test",
    "npm run lint",
    "npm run typecheck"
  ],
  "risk_level": "low",
  "rollback": "Revert the candidate commit.",
  "max_files_changed": 4,
  "max_lines_changed": 120
}
```

---

# 16. Data Model

## 16.1 Core entities

```mermaid
erDiagram
    TENANT ||--o{ USER : has
    TENANT ||--o{ INTEGRATION : configures
    TENANT ||--o{ INCIDENT : owns

    INCIDENT ||--o{ INCIDENT_SIGNAL : receives
    INCIDENT ||--o{ EVIDENCE_ITEM : contains
    INCIDENT ||--o{ TIMELINE_EVENT : builds
    INCIDENT ||--o{ HYPOTHESIS : evaluates
    INCIDENT ||--o{ WORKFLOW_RUN : executes
    INCIDENT ||--o{ APPROVAL_REQUEST : requires
    INCIDENT ||--o{ COMMUNICATION_ARTIFACT : generates
    INCIDENT ||--o| POSTMORTEM : produces

    WORKFLOW_RUN ||--o{ WORKFLOW_EVENT : emits
    WORKFLOW_RUN ||--o{ AGENT_RUN : contains
    AGENT_RUN ||--o{ TOOL_INVOCATION : calls

    INCIDENT ||--o{ REMEDIATION_PLAN : proposes
    REMEDIATION_PLAN ||--o{ PATCH_ATTEMPT : creates
    PATCH_ATTEMPT ||--o{ VERIFICATION_RUN : validates
    PATCH_ATTEMPT ||--o{ CODE_ARTIFACT : stores
    PATCH_ATTEMPT ||--o{ EXTERNAL_ACTION : triggers

    APPROVAL_REQUEST ||--o| APPROVAL_DECISION : receives
```

## 16.2 Table outline

### `tenants`
- `id`
- `name`
- `slug`
- `settings_json`
- `created_at`
- `updated_at`

### `users`
- `id`
- `tenant_id`
- `email`
- `display_name`
- `role`
- `created_at`

### `incidents`
- `id`
- `tenant_id`
- `external_key`
- `title`
- `summary`
- `service`
- `environment`
- `severity`
- `status`
- `workflow_state`
- `started_at`
- `detected_at`
- `resolved_at`
- `created_by`
- `created_at`
- `updated_at`
- `version` for optimistic concurrency

### `incident_signals`
- `id`
- `incident_id`
- `provider`
- `signal_type`
- `raw_payload_uri`
- `normalized_payload_json`
- `received_at`
- `payload_hash`
- `simulated`

### `evidence_items`
- `id`
- `incident_id`
- `kind`
- `provider`
- `source_ref`
- `title`
- `content_text`
- `content_uri`
- `captured_at`
- `relevance_score`
- `redaction_status`
- `sha256`
- `metadata_json`
- `simulated`

### `timeline_events`
- `id`
- `incident_id`
- `event_type`
- `timestamp`
- `title`
- `description`
- `evidence_ids_json`
- `confidence`

### `hypotheses`
- `id`
- `incident_id`
- `rank`
- `claim`
- `confidence`
- `supporting_evidence_ids_json`
- `contradicting_evidence_ids_json`
- `assumptions_json`
- `falsification_steps_json`
- `likely_files_json`
- `blast_radius`
- `status`

### `workflow_runs`
- `id`
- `incident_id`
- `workflow_version`
- `state`
- `current_stage`
- `started_at`
- `completed_at`
- `error_code`
- `error_message`
- `correlation_id`

### `workflow_events`
- `id`
- `workflow_run_id`
- `sequence`
- `event_type`
- `stage`
- `status`
- `payload_json`
- `created_at`

### `agent_runs`
- `id`
- `workflow_run_id`
- `agent_name`
- `prompt_version`
- `model`
- `status`
- `input_hash`
- `output_json`
- `started_at`
- `completed_at`
- `input_tokens`
- `output_tokens`
- `estimated_cost`
- `trace_ref`

### `tool_invocations`
- `id`
- `agent_run_id`
- `tool_name`
- `input_redacted_json`
- `output_ref`
- `status`
- `duration_ms`
- `created_at`

### `remediation_plans`
- `id`
- `incident_id`
- `version`
- `summary`
- `steps_json`
- `files_expected_json`
- `verification_commands_json`
- `risk_level`
- `rollback`
- `change_budget_json`
- `status`
- `created_at`

### `patch_attempts`
- `id`
- `remediation_plan_id`
- `attempt_number`
- `workspace_id`
- `codex_thread_id`
- `status`
- `base_commit_sha`
- `result_commit_sha`
- `diff_uri`
- `changed_files_json`
- `lines_added`
- `lines_removed`
- `created_at`
- `completed_at`

### `verification_runs`
- `id`
- `patch_attempt_id`
- `command`
- `category`
- `exit_code`
- `stdout_uri`
- `stderr_uri`
- `duration_ms`
- `passed`
- `created_at`

### `approval_requests`
- `id`
- `incident_id`
- `action_type`
- `risk_level`
- `summary`
- `artifact_refs_json`
- `status`
- `expires_at`
- `created_at`

### `approval_decisions`
- `id`
- `approval_request_id`
- `decision`
- `decided_by`
- `reason`
- `created_at`

### `external_actions`
- `id`
- `incident_id`
- `action_type`
- `provider`
- `idempotency_key`
- `approval_request_id`
- `status`
- `request_json`
- `provider_receipt_json`
- `created_at`
- `completed_at`

### `postmortems`
- `id`
- `incident_id`
- `summary`
- `impact`
- `root_cause`
- `resolution`
- `timeline_json`
- `action_items_json`
- `markdown_uri`
- `created_at`

### `audit_events`
- `id`
- `tenant_id`
- `actor_type`
- `actor_id`
- `action`
- `resource_type`
- `resource_id`
- `payload_json`
- `created_at`

---

# 17. API Contract

Base path: `/api/v1`

## 17.1 Incidents

### `POST /incidents`

Creates an incident.

```json
{
  "title": "Checkout API elevated 500 errors",
  "service": "checkout-api",
  "environment": "production",
  "severity": "SEV2",
  "summary": "HTTP 500 rate exceeded 12% after deployment.",
  "signal": {
    "provider": "demo",
    "signal_type": "error_rate",
    "payload": {}
  }
}
```

Returns `201` with incident summary.

### `GET /incidents`

Filters:
- `status`
- `severity`
- `service`
- `environment`
- `cursor`
- `limit`

### `GET /incidents/{incident_id}`

Returns incident aggregate summary.

### `POST /incidents/{incident_id}/start`

Starts or resumes the workflow.

### `POST /incidents/{incident_id}/cancel`

Cancels a non-terminal workflow.

### `POST /incidents/{incident_id}/reset-demo`

Demo tenant only.

## 17.2 Evidence

### `GET /incidents/{incident_id}/evidence`

### `GET /incidents/{incident_id}/timeline`

### `POST /incidents/{incident_id}/evidence`

Allows manual evidence attachment.

## 17.3 Hypotheses and plans

### `GET /incidents/{incident_id}/hypotheses`

### `POST /incidents/{incident_id}/hypotheses/{hypothesis_id}/feedback`

Feedback:
- `confirmed`
- `rejected`
- `needs_more_evidence`

### `GET /incidents/{incident_id}/remediation-plan`

### `POST /incidents/{incident_id}/remediation-plan/revise`

## 17.4 Approvals

### `GET /incidents/{incident_id}/approvals`

### `POST /approvals/{approval_id}/decision`

```json
{
  "decision": "approved",
  "reason": "Proceed with the bounded workspace patch."
}
```

Server must verify:
- user permission,
- approval not expired,
- artifact version has not changed,
- action not already executed.

## 17.5 Patches and verification

### `GET /incidents/{incident_id}/patches`

### `GET /patches/{patch_id}/diff`

### `GET /patches/{patch_id}/verification`

### `POST /patches/{patch_id}/retry`

Requires policy validation and remaining retry budget.

## 17.6 Pull request

### `POST /incidents/{incident_id}/draft-pr`

Requires an approved `CREATE_DRAFT_PR` approval.

### `GET /incidents/{incident_id}/draft-pr`

## 17.7 Communications

### `GET /incidents/{incident_id}/communications`

### `POST /incidents/{incident_id}/communications/regenerate`

### `GET /incidents/{incident_id}/postmortem`

## 17.8 Integrations

### `POST /webhooks/{provider}`

Must verify signature in live mode.

### `GET /integrations`

### `POST /integrations/{provider}/test`

Never return credentials.

## 17.9 Live events

### `GET /incidents/{incident_id}/events`

SSE event types:
- `workflow.state.changed`
- `workflow.stage.started`
- `workflow.stage.progress`
- `workflow.stage.completed`
- `workflow.stage.failed`
- `evidence.added`
- `hypotheses.ready`
- `approval.requested`
- `approval.decided`
- `patch.diff.ready`
- `verification.updated`
- `external_action.updated`
- `incident.updated`

Every event contains:
- event ID,
- incident ID,
- workflow run ID,
- sequence,
- timestamp,
- payload.

---

# 18. Frontend Information Architecture

## 18.1 Routes

```text
/
  /login
  /dashboard
  /incidents
  /incidents/[incidentId]
  /incidents/[incidentId]/postmortem
  /integrations
  /settings
  /demo
```

## 18.2 Dashboard

### Header
- product name,
- “Trigger demo incident” CTA,
- environment indicator,
- user menu.

### KPI cards
- active incidents,
- average diagnosis time,
- candidate fixes generated,
- verification pass rate.

### Active incidents table
- severity,
- incident,
- service,
- state,
- elapsed time,
- confidence,
- owner.

### Recent activity
- workflow events,
- approvals awaiting action,
- completed PR packages.

## 18.3 Incident war room

Use a dense but legible three-zone layout.

### Left: Incident and timeline
- severity/status,
- service/environment,
- elapsed timer,
- incident summary,
- chronological evidence timeline.

### Center: Investigation workspace
Tabs:
- Overview
- Evidence
- Hypotheses
- Remediation
- Verification
- Postmortem

### Right: Command rail
- current stage,
- agent activity,
- approval card,
- risk level,
- next action,
- safe stop/cancel.

## 18.4 Critical components

- `IncidentStatusHeader`
- `WorkflowStepper`
- `LiveAgentActivity`
- `EvidenceCard`
- `EvidenceSourceBadge`
- `HypothesisCard`
- `ConfidenceMeter`
- `ContradictionList`
- `RemediationPlanCard`
- `ApprovalGate`
- `DiffViewer`
- `VerificationCommandList`
- `RiskReviewPanel`
- `PullRequestCard`
- `PostmortemEditor`
- `DemoControlPanel`

## 18.5 Visual direction

- Dark-first operational interface with optional light mode.
- High-information density without cyberpunk clutter.
- Red reserved for actual failure or SEV1/SEV2 state.
- Amber for approvals and uncertainty.
- Green only for deterministic passed checks.
- Monospace only for code, IDs, and logs.
- Animations communicate progress, not decoration.
- Always show whether evidence is `LIVE`, `FIXTURE`, or `SIMULATED`.

## 18.6 UX rules

- The user must understand the current state and next required action without opening chat.
- Agent prose never hides deterministic status.
- Every confidence value has an explanation.
- Every irreversible or external action has a review modal.
- Empty/error states are designed, not left as generic alerts.
- The demo path must fit within a 3-minute video.

---

# 19. Repository and Sandbox Architecture

## 19.1 Workspace lifecycle

1. Create unique workspace ID.
2. Clone repository at an immutable base commit or mount the fixture repository.
3. Verify repository checksum and branch.
4. Start in read-only mode.
5. Inspect repository and validate remediation plan.
6. Request patch approval.
7. Switch to workspace-write mode.
8. Run Codex patch turn.
9. Enforce changed-path and change-size policy.
10. Run verification commands.
11. Repeat within repair budget if allowed.
12. Store diff and check results.
13. Destroy workspace after artifact capture.

## 19.2 Sandbox policy

Default:
- network disabled,
- repository-local filesystem only,
- CPU and memory limits,
- process timeout,
- no host Docker socket,
- no cloud metadata access,
- sanitized environment,
- allowlisted commands,
- no SSH keys,
- no repository write token.

Allowed commands are derived from repository configuration plus a safe baseline.

Example baseline:
- `git status`
- `git diff`
- `git log`
- `npm test`
- `npm run lint`
- `npm run typecheck`
- `pytest`
- `ruff check`
- `mypy`

Do not allow:
- `curl`
- `wget`
- `ssh`
- `scp`
- package publishing,
- cloud CLIs,
- destructive filesystem commands,
- nested Docker,
- arbitrary shell pipes unless explicitly parsed and allowed.

## 19.3 Repository manifest

Each connected repository may contain:

```yaml
# .incident-commander.yml
version: 1
service: checkout-api

commands:
  install: npm ci
  targeted_test: npm test -- checkout.test.ts
  test: npm test
  lint: npm run lint
  typecheck: npm run typecheck

change_policy:
  max_files: 5
  max_lines: 200
  denied_paths:
    - ".github/workflows/**"
    - "infra/**"
    - "migrations/**"
    - "**/*.pem"
    - "**/.env*"

risk_paths:
  - "src/auth/**"
  - "src/payments/**"

context:
  entrypoints:
    - "src/index.ts"
  runbooks:
    - "docs/runbooks/checkout.md"
```

## 19.4 Patch repair loop

Maximum default attempts: 2.

```text
Attempt 1:
  plan → test reproduction → patch → checks

If checks fail:
  summarize deterministic failures
  classify as patch issue / environment issue / pre-existing failure

Attempt 2 only when:
  failure is relevant,
  budget remains,
  policy allows,
  base state is known.

After attempt 2:
  pass → review
  fail → stop and show evidence
```

---

# 20. Integration Adapter Architecture

## 20.1 Adapter interface

```python
class EvidenceProvider(Protocol):
    provider_name: str

    async def healthcheck(self) -> ProviderHealth: ...
    async def collect(self, request: EvidenceRequest) -> EvidenceBatch: ...
    async def normalize_webhook(self, payload: bytes, headers: Mapping[str, str]) -> IncidentSignal: ...
```

## 20.2 Required adapters

### Fixture telemetry adapter
- deterministic,
- no network,
- used by tests and demo,
- includes logs, stack traces, metrics, deploy event, and commit metadata.

### Git repository adapter
Modes:
- local fixture Git repository,
- GitHub read-only integration.

### Pull request adapter
Modes:
- simulated artifact,
- GitHub draft PR.

## 20.3 P1 adapters

- Sentry.
- GitHub Actions.
- Slack.
- Generic OpenTelemetry export import.
- Runbook document storage.

## 20.4 Adapter rules

- Domain services never import provider SDKs directly.
- Adapters return normalized schemas.
- Provider errors map to internal error codes.
- Timeouts and retries configured per provider.
- Provider results include `simulated` and `freshness`.
- Credentials are resolved outside model context.

---

# 21. Security, Safety, and Trust Architecture

## 21.1 Security boundaries

### Browser
- no provider tokens,
- no OpenAI API key,
- no repository write token,
- short-lived session only.

### API
- authentication,
- authorization,
- tenant isolation,
- input validation,
- webhook verification,
- approval enforcement.

### Worker
- model calls,
- provider reads,
- workflow execution,
- no direct frontend trust.

### Sandbox
- untrusted repository code,
- strict resource limits,
- temporary credentials only when absolutely required,
- network disabled by default.

## 21.2 Threat model

| Threat | Mitigation |
|---|---|
| Prompt injection inside logs or repository | Treat external text as data; system rules remain separate; tool permissions are deterministic |
| Malicious repository script | Isolated sandbox, resource limits, network off, command allowlist |
| Secret leakage to model | Redaction pipeline, secret scanners, field allowlist |
| Cross-tenant evidence access | Tenant-scoped queries and row-level authorization |
| Duplicate PRs on retry | Idempotency keys and provider receipt persistence |
| Model invents test success | Only deterministic process result can mark a check passed |
| Model proposes broad refactor | Change budget and path policy |
| Unauthorized approval | RBAC, artifact version check, signed audit event |
| Webhook spoofing | Provider signature verification and replay protection |
| Supply-chain installation risk | Locked dependencies; optional install step isolated and network-controlled |
| Sensitive diff exposure | Tenant authorization and encrypted artifact storage |
| UI shows stale approval | Optimistic concurrency and approval artifact hash |

## 21.3 Risk policy

### Low risk
- small local logic fix,
- regression test,
- no dependency or schema changes.

### Medium risk
- cross-module behavior,
- configuration change,
- dependency update,
- more than configured line threshold.

### High risk
- authentication,
- payments,
- authorization,
- database schema or migration,
- infrastructure,
- cryptography,
- secrets,
- deletion,
- public API contract change.

P0 behavior:
- Low: patch and PR approval required.
- Medium: patch and PR approval required, strong warning.
- High: patch generation may be allowed in sandbox, but real PR creation blocked by default.

## 21.4 Redaction

Detect and remove:
- API keys,
- bearer tokens,
- passwords,
- cookies,
- private keys,
- connection strings,
- email addresses when unnecessary,
- payment data,
- personal identifiers.

Keep:
- stable redaction placeholders for correlation,
- redaction audit count,
- original content only in protected raw artifact storage where configured.

## 21.5 Trust UX

Always display:
- confidence,
- evidence provenance,
- simulated/live status,
- model-generated vs deterministic output,
- approval owner,
- remaining uncertainty,
- commands actually run,
- exact changed files.

---

# 22. Observability

## 22.1 Correlation

Use:
- `request_id`
- `correlation_id`
- `incident_id`
- `workflow_run_id`
- `agent_run_id`
- `workspace_id`
- `external_action_id`

## 22.2 Logs

Structured JSON fields:
- timestamp,
- level,
- component,
- action,
- IDs,
- duration,
- status,
- error code,
- provider,
- simulated.

Never log:
- access tokens,
- full prompts with secrets,
- raw unredacted evidence,
- user session tokens.

## 22.3 Metrics

- API latency/error rate.
- Queue depth.
- Stage duration.
- Workflow completion rate.
- Agent run latency.
- Token usage and estimated cost.
- Tool failure rate.
- Sandbox creation duration.
- Verification pass rate.
- Approval wait time.
- PR creation success rate.
- Demo scenario success rate.

## 22.4 Traces

- One trace per workflow run.
- Span per stage.
- Child span per agent run.
- Child span per tool invocation.
- Link sandbox and external action logs by correlation ID.
- Store only redacted trace attributes.

## 22.5 Product-facing telemetry

A small “How the AI worked” panel should show:
- evidence sources inspected,
- agent stages completed,
- model calls,
- tools used,
- tests executed,
- elapsed time,
- confidence progression.

This demonstrates technical implementation to judges without exposing hidden reasoning.

---

# 23. Evaluation Framework

## 23.1 Evaluation dataset

Create `/evals/fixtures` with at least eight incidents:

1. Null dereference after deployment — clear root cause.
2. Environment variable missing — no code patch needed.
3. Dependency timeout — mitigation, not code fix.
4. Pre-existing failing test — avoid false success.
5. Misleading correlation — recent deployment is unrelated.
6. Secret embedded in log — verify redaction.
7. Prompt injection in log text — verify tool safety.
8. High-risk auth regression — verify policy block.

## 23.2 Evaluation dimensions

### Diagnosis quality
- top hypothesis correctness,
- evidence citation precision,
- unsupported claim rate,
- uncertainty calibration.

### Remediation quality
- patch correctness,
- patch minimality,
- regression test quality,
- change budget compliance.

### Safety
- secret leakage,
- prompt-injection resistance,
- high-risk policy compliance,
- approval bypass attempts.

### Product reliability
- workflow completion,
- retry behavior,
- state recovery,
- idempotency.

## 23.3 Automated graders

Use deterministic graders where possible:
- expected top hypothesis component/file,
- required evidence IDs present,
- prohibited claim absent,
- required test added,
- diff size within threshold,
- commands pass,
- no prohibited paths changed.

Model-based graders may evaluate:
- clarity of stakeholder update,
- postmortem completeness,
- plan quality.

Model graders must not be the only quality gate.

## 23.4 Golden demo gate

The build is demo-ready only when:

```text
make demo-reset
make demo-run
make demo-assert
```

passes five consecutive times with:
- same expected top hypothesis,
- valid patch,
- all required checks passed,
- approval gates observed,
- PR artifact created,
- postmortem generated.

---

# 24. Testing Strategy

## 24.1 Unit tests

- normalization,
- redaction,
- evidence deduplication,
- timeline sorting,
- confidence validation,
- state transition rules,
- approval policy,
- change budget,
- command allowlist,
- adapter error mapping,
- idempotency key generation.

## 24.2 Contract tests

- frontend API client vs OpenAPI schema.
- provider adapters vs normalized contracts.
- agent structured output schemas.
- SSE event schemas.
- GitHub simulated and live adapter parity.

## 24.3 Integration tests

- API + database.
- worker + Redis.
- workflow resume.
- fixture repository + sandbox.
- Codex gateway mocked and live smoke test.
- simulated PR creation.

## 24.4 End-to-end tests

Use Playwright.

Required:
1. Create demo incident.
2. Observe evidence and hypotheses.
3. Approve patch.
4. Inspect diff.
5. Verify tests.
6. Approve simulated PR.
7. Open postmortem.
8. Reset demo.

## 24.5 Security tests

- webhook replay,
- invalid signature,
- cross-tenant ID access,
- approval replay,
- path traversal,
- command injection,
- prompt injection fixture,
- secret redaction,
- oversized payload,
- malicious archive/repository file names.

## 24.6 Performance tests

- 50 concurrent incident reads.
- 10 simultaneous demo workflows.
- large log payload ingestion.
- SSE reconnect and replay.
- sandbox timeout handling.

---

# 25. Error Handling and Recovery

## 25.1 Error taxonomy

- `VALIDATION_ERROR`
- `AUTHENTICATION_ERROR`
- `AUTHORIZATION_ERROR`
- `PROVIDER_UNAVAILABLE`
- `PROVIDER_RATE_LIMITED`
- `EVIDENCE_INSUFFICIENT`
- `MODEL_SCHEMA_ERROR`
- `MODEL_TIMEOUT`
- `SANDBOX_CREATE_FAILED`
- `COMMAND_DENIED`
- `COMMAND_TIMEOUT`
- `PATCH_POLICY_VIOLATION`
- `PATCH_VERIFICATION_FAILED`
- `APPROVAL_REQUIRED`
- `APPROVAL_EXPIRED`
- `EXTERNAL_ACTION_FAILED`
- `WORKFLOW_CONFLICT`
- `INTERNAL_ERROR`

## 25.2 Retry policy

Retry:
- transient provider errors,
- model 429/5xx,
- queue delivery,
- object storage transient error.

Do not automatically retry:
- invalid schema after configured repair attempt,
- denied command,
- policy violation,
- rejected approval,
- failing deterministic test without a planned repair turn,
- authentication failure.

## 25.3 Workflow recovery

- Persist stage start and completion.
- Re-run only idempotent stages.
- Artifact-producing stages use content hashes.
- On restart, reconcile `RUNNING` jobs with queue state.
- External writes check existing provider receipts before retry.

---

# 26. Deployment Architecture

```mermaid
flowchart TB
    CDN[CDN / Edge] --> FRONT[Next.js Frontend]
    FRONT --> API[FastAPI API Container]
    API --> PG[(Managed PostgreSQL)]
    API --> REDIS[(Managed Redis)]
    API --> S3[(Object Storage)]
    API --> WORKER[Workflow Worker Container]
    WORKER --> PG
    WORKER --> REDIS
    WORKER --> S3
    WORKER --> OPENAI[OpenAI APIs]
    WORKER --> GH[GitHub]
    WORKER --> RUNNER[Isolated Sandbox Runner]
    RUNNER --> ART[Workspace Artifacts]
```

## 26.1 Environments

- `local`
- `test`
- `demo`
- `production`

## 26.2 Demo environment characteristics

- fixture telemetry,
- fixture repository,
- deterministic incident seed,
- simulated PR by default,
- optional real GitHub integration,
- reset endpoint protected by demo admin key,
- no dependency on Sentry or Slack.

## 26.3 Health endpoints

- `/health/live`
- `/health/ready`
- `/health/dependencies`
- `/health/workers`

## 26.4 Database migrations

- Alembic.
- Migration applied in a release job.
- Never auto-generate destructive migrations in production.
- Demo reset uses seed routines, not schema drops.

---

# 27. Monorepo Structure

```text
incident-commander-ai/
├── AGENTS.md
├── README.md
├── LICENSE
├── Makefile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── .editorconfig
├── docs/
│   ├── AI_INCIDENT_COMMANDER_MASTER_BLUEPRINT_v1.md
│   ├── architecture/
│   │   ├── system-context.md
│   │   ├── workflow-state-machine.md
│   │   ├── security-model.md
│   │   └── demo-architecture.md
│   ├── adr/
│   │   ├── ADR-001-monorepo.md
│   │   ├── ADR-002-agent-orchestration.md
│   │   ├── ADR-003-sandbox-boundary.md
│   │   └── ADR-004-human-approval.md
│   ├── api/
│   │   └── openapi.yaml
│   ├── demo/
│   │   ├── demo-script.md
│   │   └── troubleshooting.md
│   └── submission/
│       ├── devpost-description.md
│       ├── video-script.md
│       └── judging-map.md
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── lib/
│   ├── public/
│   ├── tests/
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── domain/
│   │   ├── workflows/
│   │   ├── ai/
│   │   │   ├── agents/
│   │   │   ├── prompts/
│   │   │   ├── schemas/
│   │   │   ├── guardrails/
│   │   │   └── gateways/
│   │   ├── integrations/
│   │   │   ├── github/
│   │   │   ├── telemetry/
│   │   │   ├── sentry/
│   │   │   └── slack/
│   │   ├── sandbox/
│   │   ├── policies/
│   │   ├── persistence/
│   │   ├── observability/
│   │   └── config.py
│   ├── migrations/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── worker/
│   └── entrypoint.py
├── sandbox-runner/
│   ├── Dockerfile
│   ├── policies/
│   └── runner/
├── packages/
│   └── contracts/
│       ├── generated-typescript/
│       └── schemas/
├── demo/
│   ├── fixture-repo/
│   ├── telemetry/
│   ├── seeds/
│   └── expected/
├── evals/
│   ├── fixtures/
│   ├── graders/
│   └── run_evals.py
├── scripts/
│   ├── bootstrap.sh
│   ├── seed_demo.py
│   ├── run_demo.py
│   └── assert_demo.py
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── security.yml
├── taskstatus.md
├── handover.md
├── Implementation_Changelog.md
├── Debugging_Log.md
└── BUILD_STATUS.json
```

---

# 28. Autonomous Development Governance

Codex must maintain these files from the first commit.

## 28.1 `taskstatus.md`

Contains:
- current milestone,
- completed tasks,
- in-progress task,
- blocked tasks,
- next three tasks,
- quality gate status.

## 28.2 `handover.md`

Contains:
- how to run the project,
- current architecture,
- current known limitations,
- credentials still needed,
- exact continuation point.

## 28.3 `Implementation_Changelog.md`

Append-only:
- timestamp,
- change,
- files,
- rationale,
- validation performed.

## 28.4 `Debugging_Log.md`

Append-only:
- symptom,
- reproduction,
- root cause,
- fix,
- prevention,
- affected tests.

## 28.5 `BUILD_STATUS.json`

Machine-readable:

```json
{
  "version": 1,
  "milestone": "M0",
  "status": "in_progress",
  "p0_complete": false,
  "demo_ready": false,
  "quality_gates": {
    "frontend_lint": false,
    "frontend_typecheck": false,
    "backend_lint": false,
    "backend_typecheck": false,
    "unit_tests": false,
    "integration_tests": false,
    "e2e_tests": false,
    "demo_assertion": false
  },
  "last_verified_at": null,
  "known_blockers": []
}
```

## 28.6 Branch and commit discipline

Suggested branches:
- `main`
- `develop`
- `feature/<scope>`
- `fix/<scope>`

Commit examples:
- `feat(incidents): add incident intake and normalization`
- `feat(workflow): implement durable incident state machine`
- `feat(codex): add isolated patch gateway`
- `test(demo): add golden incident assertion`

Do not combine unrelated changes.

---

# 29. Build Milestones

## M0 — Foundation

Deliver:
- monorepo,
- local Docker Compose,
- frontend shell,
- FastAPI shell,
- PostgreSQL/Redis connectivity,
- CI,
- environment configuration,
- status documents.

Gate:
- one-command startup,
- health endpoints pass,
- lint/typecheck/test skeleton passes.

## M1 — Incident intake and dashboard

Deliver:
- incident schema,
- migrations,
- manual creation,
- generic webhook,
- fixture incident generator,
- dashboard and incident page shell.

Gate:
- incident created through UI,
- data persists,
- E2E test passes.

## M2 — Evidence pipeline

Deliver:
- evidence adapter interface,
- fixture telemetry,
- Git fixture adapter,
- redaction,
- timeline,
- evidence UI.

Gate:
- golden incident displays source-linked evidence and timeline.
- secret fixture is redacted.

## M3 — Investigation agents

Deliver:
- Incident Commander,
- triage,
- timeline correlation,
- root-cause hypotheses,
- typed outputs,
- guardrails,
- tracing.

Gate:
- expected top hypothesis returned for golden fixture.
- no unsupported conclusion.
- insufficient-evidence fixture stops safely.

## M4 — Remediation planning and approval

Deliver:
- remediation planner,
- policy engine,
- approval model/API/UI,
- change budget.

Gate:
- no workspace write before approval.
- rejected approval halts workflow.

## M5 — Codex sandbox patch

Deliver:
- sandbox lifecycle,
- Codex gateway,
- fixture repo,
- patch generation,
- diff capture.

Gate:
- candidate patch modifies only allowed files.
- workspace destroyed after artifact capture.
- patch cannot access network or secrets.

## M6 — Verification and review

Deliver:
- command runner,
- test/lint/typecheck results,
- bounded repair loop,
- risk reviewer,
- review UI.

Gate:
- deterministic checks drive pass/fail.
- failed checks block PR.
- high-risk path triggers block.

## M7 — Draft PR and communications

Deliver:
- simulated PR adapter,
- optional GitHub draft PR,
- technical/stakeholder updates,
- postmortem.

Gate:
- PR action requires second approval.
- retries do not duplicate PR.
- postmortem includes evidence-based timeline.

## M8 — Product polish

Deliver:
- responsive UI,
- loading/empty/error states,
- accessibility,
- demo reset,
- metrics,
- onboarding,
- integration health.

Gate:
- full demo passes five times.
- no console errors.
- no broken links.
- Lighthouse and accessibility checks acceptable.

## M9 — Submission package

Deliver:
- public README,
- architecture diagram,
- Devpost text,
- 2–3 minute video,
- screenshots,
- demo credentials,
- judging criteria mapping.

Gate:
- fresh reviewer can run locally from README.
- video shows one complete workflow.
- repository contains no secrets.

---

# 30. Eight-Day Hackathon Execution Plan

Adjust to the official schedule, but preserve the dependency order.

## Day 0 — Before build window

- Finalize product name and pitch.
- Prepare this blueprint.
- Create private repository.
- Prepare fixture incident and fixture repository.
- Confirm eligibility and submission requirements.
- Prepare environment accounts and credentials.

## Day 1 — Foundation + intake

- M0.
- M1 backend and basic UI.
- Demo seed.
- Deploy skeleton.

## Day 2 — Evidence + timeline

- M2.
- Redaction.
- Timeline UI.
- Start evaluation fixtures.

## Day 3 — Investigation

- M3.
- Tune structured outputs.
- Add confidence and evidence citation UX.

## Day 4 — Approval + Codex patching

- M4 and M5.
- Get one patch working before adding integrations.

## Day 5 — Verification + risk

- M6.
- Failure and retry paths.
- High-risk policy fixture.

## Day 6 — PR + postmortem + polish

- M7.
- Simulated PR first.
- Optional live GitHub PR second.
- UI polish.

## Day 7 — Reliability

- M8.
- Run full demo repeatedly.
- Fix latency and flaky behavior.
- Record backup demo.

## Day 8 — Submission

- M9.
- Video, screenshots, README, Devpost copy.
- Final rule and eligibility check.
- Submit several hours before deadline.

---

# 31. P0 Backlog and Acceptance Criteria

## Epic A — Incident intake

### A1 Manual incident
**Accepted when**
- user can create incident,
- validation errors are clear,
- record persists,
- workflow can start.

### A2 Demo incident
**Accepted when**
- one click creates exact golden fixture,
- reset is idempotent,
- fixture is labeled simulated.

## Epic B — Evidence

### B1 Logs
**Accepted when**
- stack trace and request context appear,
- secrets are redacted,
- evidence can be opened from a hypothesis.

### B2 Git correlation
**Accepted when**
- recent deployment and commit are visible,
- likely source file is identified,
- commit evidence has provenance.

## Epic C — Diagnosis

### C1 Hypotheses
**Accepted when**
- at least three ranked hypotheses,
- each has evidence,
- top hypothesis matches expected fixture,
- unknowns shown.

## Epic D — Remediation

### D1 Plan
**Accepted when**
- plan names expected files,
- regression test included,
- risk and rollback included,
- change budget included.

### D2 Approval
**Accepted when**
- patch does not start without approval,
- approval decision is audited,
- stale approval cannot be reused.

## Epic E — Patch

### E1 Codex
**Accepted when**
- Codex operates in isolated workspace,
- minimal patch produced,
- diff stored,
- no denied paths modified.

## Epic F — Verification

### F1 Checks
**Accepted when**
- targeted test, full test, lint, and typecheck captured,
- UI displays command evidence,
- failed command blocks PR.

## Epic G — Review and PR

### G1 Review
**Accepted when**
- diff, risk, tests, and rollback visible on one screen.

### G2 Draft PR
**Accepted when**
- second approval required,
- simulated adapter works offline,
- live adapter creates a draft PR when configured.

## Epic H — Closure

### H1 Communications
**Accepted when**
- technical and executive updates differ appropriately.

### H2 Postmortem
**Accepted when**
- timeline, impact, cause, resolution, and actions present,
- Markdown export works.

---

# 32. Demo Fixture Specification

## 32.1 Service

`checkout-api`, Node.js/TypeScript.

## 32.2 Defect

A commit changes safe optional discount handling into an unsafe direct property access.

Before regression:

```ts
const code = session.discount?.code ?? null;
```

Regression:

```ts
const code = session.discount.code;
```

Requests without a discount throw a runtime error.

## 32.3 Evidence bundle

- Alert: HTTP 500 rate increased from 0.2% to 12.4%.
- Deployment: version `2026.07.13.4` at 10:02 UTC.
- Incident start: 10:05 UTC.
- Stack trace points to `checkout.ts`.
- Commit at 09:48 UTC modified discount handling.
- Error samples only affect sessions without a discount.
- Existing tests cover discounted sessions but not no-discount sessions.
- Runbook says to check deployment correlation and reproduce locally.

## 32.4 Expected diagnosis

Top hypothesis:
- unsafe access to `session.discount.code` after the latest deployment.

## 32.5 Expected remediation

- add a regression test for a session without discount,
- restore optional handling,
- no unrelated refactor,
- run targeted and complete checks.

## 32.6 Expected diff

Maximum:
- 2 files,
- under 40 changed lines.

---

# 33. Demo Script

Target duration: 2 minutes 30 seconds.

## 0:00–0:15 — Problem

Show alert and say:

> “Small teams lose the first hour of an incident collecting evidence and finding the change that caused it.”

## 0:15–0:35 — Intake and evidence

Trigger the demo incident.

Show:
- 500 error spike,
- deployment correlation,
- stack trace,
- recent commit.

Say:

> “Incident Commander normalizes the alert, gathers evidence, and builds a timeline.”

## 0:35–0:55 — Root cause

Open hypotheses.

Show:
- top hypothesis,
- confidence,
- evidence citations,
- falsification test.

Say:

> “It separates evidence from inference and shows exactly why this is the leading hypothesis.”

## 0:55–1:15 — Plan and approval

Show remediation plan and approval gate.

Say:

> “Before changing code, it proposes a bounded plan and requires a human approval.”

Approve.

## 1:15–1:45 — Codex patch and verification

Show live activity:
- workspace created,
- test added,
- patch applied,
- targeted test,
- full tests,
- lint,
- type check.

Open diff.

Say:

> “Codex works in an isolated repository, creates the minimal patch, and the platform verifies it with deterministic checks.”

## 1:45–2:05 — Risk and PR

Show risk review and second approval.

Create simulated or real draft PR.

Say:

> “No production action is automatic. A human approves the review package before the draft PR is created.”

## 2:05–2:25 — Communication and impact

Show technical update, stakeholder update, postmortem.

Say:

> “The same evidence becomes an accurate status update and postmortem, preserving the incident knowledge for the team.”

## 2:25–2:30 — Close

> “Incident Commander turns an alert into an evidence-backed, verified, human-approved fix.”

---

# 34. Submission Story

## 34.1 One-line pitch

**Incident Commander AI helps small engineering teams diagnose production failures, generate and verify a minimal Codex patch, prepare a human-approved draft PR, and write the postmortem from one evidence-grounded incident room.**

## 34.2 Two-to-three sentence application pitch

Small engineering teams often lack dedicated SRE coverage, so production incidents force senior developers to manually collect logs, correlate deployments, locate the regression, patch code, verify it, and update stakeholders. Incident Commander AI uses GPT-5.6 for evidence-grounded investigation and Codex in an isolated workspace to create and verify a minimal candidate fix. Every external write is human-approved, and the full evidence, diff, tests, risk review, draft PR, and postmortem remain auditable.

## 34.3 Judging criteria mapping

### Technological implementation
- multi-agent orchestration,
- structured outputs,
- evidence provenance,
- Codex repository workflow,
- isolated workspace,
- deterministic verification,
- tracing,
- approval engine.

### Design
- coherent incident room,
- live stage progression,
- inspectable evidence,
- clear confidence and risk,
- polished diff and approval UX.

### Potential impact
- smaller teams gain SRE-like response leverage,
- faster diagnosis,
- less interruption,
- better incident documentation.

### Quality of idea
- connects observability and coding into one bounded workflow,
- emphasizes evidence and control rather than generic chat,
- generates operational artifacts, not only text.

---

# 35. Environment Variables

```bash
# App
APP_ENV=local
APP_BASE_URL=http://localhost:3000
API_BASE_URL=http://localhost:8000
LOG_LEVEL=INFO
DEMO_MODE=true
DEMO_ADMIN_KEY=

# Database
DATABASE_URL=postgresql+asyncpg://incident:incident@localhost:5432/incident
REDIS_URL=redis://localhost:6379/0

# Storage
ARTIFACT_STORAGE_DRIVER=local
ARTIFACT_STORAGE_PATH=./.artifacts
S3_ENDPOINT=
S3_BUCKET=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=

# OpenAI
OPENAI_API_KEY=
OPENAI_REASONING_MODEL=gpt-5.6
OPENAI_FAST_MODEL=
OPENAI_AGENT_TRACING_ENABLED=true
CODEX_MODEL=
CODEX_SANDBOX_MODE=workspace_write
MODEL_MAX_RETRIES=2

# GitHub
GITHUB_MODE=simulated
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_INSTALLATION_ID=
GITHUB_REPOSITORY=
GITHUB_BASE_BRANCH=main

# Auth
AUTH_MODE=demo
AUTH_SECRET=
SESSION_COOKIE_SECURE=false

# Workflow limits
MAX_PATCH_ATTEMPTS=2
MAX_FILES_CHANGED=5
MAX_LINES_CHANGED=200
COMMAND_TIMEOUT_SECONDS=300
WORKSPACE_TTL_MINUTES=30
MODEL_STAGE_TIMEOUT_SECONDS=180

# Optional integrations
SENTRY_AUTH_TOKEN=
SENTRY_ORG=
SENTRY_PROJECT=
SLACK_BOT_TOKEN=
SLACK_CHANNEL_ID=
```

Rules:
- `.env.example` contains no real secrets.
- Startup validates required values by environment.
- Demo mode runs without GitHub/Sentry/Slack credentials.
- Exact model IDs remain configurable because account availability may vary.

---

# 36. Local Development Contract

Required commands:

```bash
make bootstrap
make dev
make test
make lint
make typecheck
make demo-reset
make demo-run
make demo-assert
```

`make dev` must start:
- frontend,
- API,
- worker,
- PostgreSQL,
- Redis.

`make demo-run` must:
- seed/reset demo,
- create golden incident,
- execute workflow through review-ready state,
- pause at approval gates when interactive,
- support `DEMO_AUTO_APPROVE=true` only for automated E2E tests,
- never perform live external actions during automated tests.

---

# 37. CI/CD Gates

Pull requests must run:

1. Secret scan.
2. Frontend formatting/lint.
3. Frontend type check.
4. Frontend unit tests.
5. Backend formatting/lint.
6. Backend type check.
7. Backend unit tests.
8. Contract tests.
9. Integration tests using services.
10. Build frontend and backend images.
11. Dependency vulnerability scan.
12. Demo smoke test with mocked model gateway.

Nightly or manually:
- live OpenAI smoke test,
- Codex SDK fixture patch test,
- evaluation suite,
- full Playwright demo.

No deployment when required checks fail.

---

# 38. Cost and Latency Controls

## 38.1 Context control

- summarize and hash repeated logs,
- retrieve only relevant code files,
- cap evidence content per stage,
- preserve raw evidence in storage, not prompts,
- use structured extraction before reasoning,
- reuse stage outputs,
- cache identical fixture calls in demo test mode.

## 38.2 Model routing

Use a configurable strategy:
- fast model for extraction/classification,
- GPT-5.6 for correlation, root cause, remediation, and risk review,
- Codex SDK for repository-aware code work.

Do not hardcode a model in domain logic.

## 38.3 Limits

Per workflow:
- maximum model calls per stage,
- maximum total model calls,
- maximum repair attempts,
- stage timeout,
- maximum tool result size,
- maximum code files read,
- maximum diff size.

Display estimated workflow cost in admin/debug view, not as the primary judge-facing metric.

---

# 39. Architectural Decision Records to Create

## ADR-001: Manager-style orchestration
Decision:
- one Incident Commander invokes bounded specialists.
Reason:
- easier auditability and deterministic stage control.

## ADR-002: Explicit durable state machine
Decision:
- state machine persists every stage.
Reason:
- agent runs may be long and recoverable.

## ADR-003: Python orchestration with FastAPI
Decision:
- Python backend for Agents SDK and Codex integration.
Reason:
- agent ecosystem and typed orchestration.

## ADR-004: Isolated workspace
Decision:
- code execution is never performed in API container.
Reason:
- repository code is untrusted.

## ADR-005: Two human approvals
Decision:
- approval before workspace write and before external PR creation.
Reason:
- meaningful human control.

## ADR-006: Simulated-first provider strategy
Decision:
- deterministic fixture providers are first-class adapters.
Reason:
- reliable demo and repeatable tests.

## ADR-007: Deterministic verification
Decision:
- process exit results, not model prose, determine pass/fail.
Reason:
- trust and correctness.

---

# 40. Common Failure Modes to Prevent

- Building six integrations before the golden path works.
- Making chat the whole interface.
- Hiding evidence behind an AI summary.
- Allowing the model to claim a test passed.
- Running arbitrary repository commands.
- Creating a patch without a regression test.
- Failing to show uncertainty.
- No distinction between simulated and live evidence.
- Making the demo depend on an external alert provider.
- Long model wait with no progress UI.
- Hardcoded credentials or repository.
- Huge patch that looks unsafe.
- Automatic PR creation without approval.
- No failure path.
- Recording the demo before five clean runs.
- Submission README that cannot reproduce the app.

---

# 41. Definition of Done

The project is done when all conditions below are true.

## Product
- The golden incident completes end-to-end.
- Evidence, hypotheses, plan, diff, checks, approval, PR artifact, and postmortem are visible.
- Demo reset works.
- Failure and insufficient-evidence states are clear.

## AI
- Structured outputs validate.
- Root-cause claims cite evidence.
- Codex performs actual repository work.
- Agent traces are available.
- No hidden chain-of-thought is displayed; only concise rationale, evidence, and actions.

## Safety
- Secrets are redacted.
- Sandbox restrictions work.
- Patch and PR actions require approval.
- High-risk paths are blocked.
- Failed verification blocks PR.

## Engineering
- Lint/type checks pass.
- Unit, integration, contract, and E2E tests pass.
- Migrations and seeds work on a fresh environment.
- CI is green.
- No secrets in Git history.
- Status documents are current.

## Submission
- README is complete.
- Architecture diagram is present.
- Video is under the official limit.
- Devpost copy is prepared.
- Demo URL and credentials work.
- Submission is completed before the deadline.

---

# 42. Initial Codex Autonomous Build Prompt

Copy the block below into Codex after placing this document in the repository.

```text
You are the autonomous principal engineer, product engineer, AI systems architect,
security reviewer, QA lead, and release manager for this repository.

Your source of truth is:
docs/AI_INCIDENT_COMMANDER_MASTER_BLUEPRINT_v1.md

MISSION
Build the production-grade, hackathon-ready Incident Commander AI application described
in the blueprint. Complete the P0 vertical slice end-to-end before attempting P1.
The application must be runnable locally, deployable, testable, safe, visually polished,
and reliable for a live judging demo.

EXECUTION RULES
1. Read the entire blueprint and inspect the repository before changing files.
2. Create or update AGENTS.md with repository-specific commands, conventions, security
   restrictions, and quality gates.
3. Create and maintain:
   - taskstatus.md
   - handover.md
   - Implementation_Changelog.md
   - Debugging_Log.md
   - BUILD_STATUS.json
4. Work milestone by milestone in the exact dependency order M0 through M9.
5. For every milestone:
   a. write a short implementation plan,
   b. implement the smallest complete vertical slice,
   c. run relevant lint, type checks, tests, migrations, and demo checks,
   d. fix failures,
   e. update documentation and BUILD_STATUS.json,
   f. commit a coherent checkpoint when Git access is available.
6. Use typed interfaces and strict schemas. Do not parse critical model output with
   fragile string logic.
7. Keep OpenAI model IDs configurable. Use GPT-5.6 for reasoning stages when available
   and the Codex SDK for repository-aware patching.
8. Build deterministic fixture providers and the golden demo before optional real
   integrations.
9. Do not fake model, test, patch, or provider success. Simulated artifacts must be
   labeled simulated.
10. Implement a durable incident state machine and persist every transition.
11. Implement human approval gates before workspace writes and before external PR
    creation.
12. Run untrusted repository commands only inside the isolated sandbox runner with an
    allowlist, resource limits, timeouts, and no network by default.
13. Never expose credentials to the browser, prompts, logs, fixtures, or Git.
14. Do not merge, deploy, push to protected branches, or execute production actions.
15. Do not stop for ordinary implementation decisions. Choose the safest, simplest
    option consistent with the blueprint and document material deviations in ADRs.
16. Stop only when credentials are required for a live external integration, an
    irreversible action is requested, or a platform limitation prevents completion.
    In those cases, leave a fully functioning simulated/demo path and document the
    exact manual step.
17. Preserve existing good work. Do not replace functional modules without evidence.
18. Keep the UI judge-friendly: the value proposition must be obvious in 20 seconds,
    and the complete demo must fit within 2.5 minutes.
19. Finish with a fresh-environment validation and five consecutive golden demo runs.
20. Do not declare completion unless every Definition of Done item is either passed or
    explicitly documented as blocked by an external credential/platform requirement.

FIRST ACTIONS
- Read the blueprint.
- Inventory the repository.
- Create the governance/status files.
- Produce the M0 plan.
- Begin implementation immediately.
```

---

# 43. Final Product Principle

The winning version is not the one with the most agents, integrations, or screens.

The winning version is the one that makes this transformation undeniable:

```text
A confusing production alert
became
an evidence-backed explanation,
a minimal verified patch,
a human-approved draft PR,
and a credible postmortem.
```

Build that loop first. Make it trustworthy. Make it visible. Make it work every time.
