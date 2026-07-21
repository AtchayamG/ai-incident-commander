# Devpost Submission Draft

Last refreshed: 2026-07-14 (IST). The live Devpost schedule says submissions
open July 13 at 9:00 a.m. PDT and close July 21 at 5:00 p.m. PDT. The official
rules are now published and were reviewed through the authenticated Devpost
plugin. India is supported, subject to the entrant's personal eligibility and
conflict-of-interest certifications. Recheck the live form before submission.

Live Devpost project `1326935` was updated on 2026-07-14 with the complete
story and technology stack. Primary category: **Developer Tools**.

## Project name

Incident Commander AI

## Tagline

Turn a production alert into an evidence-backed, human-approved resolution
package—with a verified patch, safe draft PR, and auditable postmortem.

## 2–3 sentence application pitch

Incident Commander AI helps small engineering teams respond to production
regressions without losing control to opaque automation. It correlates alerts,
deployments, code, tests, and runbooks; ranks cited hypotheses; proposes and
verifies a minimal patch in an isolated workspace; and requires separate human
approvals before patching and before drafting the resolution package. The
deterministic demo is fully offline and explicitly simulated, while optional
OpenAI Responses, Codex CLI, and GitHub adapters are isolated behind fail-closed
provider contracts.

## Inspiration

Small teams rarely have a dedicated incident commander or SRE on every shift.
When checkout starts returning errors, a senior engineer becomes the human
integration layer: gathering logs, finding the deployment, reading the diff,
reproducing the bug, patching it, running tests, updating stakeholders, and
writing the postmortem. The expensive part is not a single coding task; it is
maintaining a safe, evidence-grounded chain from alert to resolution.

## What it does

Incident Commander AI provides one incident room for that chain:

1. Normalize a production-style alert and redact secret-shaped data before it
   crosses the persistence or model boundary.
2. Correlate telemetry, deploy history, repository evidence, and runbooks into
   an inspectable timeline.
3. Produce ranked hypotheses and a code mapping whose material claims cite
   persisted evidence IDs.
4. Generate a bounded remediation plan and stop for human approval.
5. Create a candidate patch in an isolated workspace with explicit file/line,
   command, time, network, and iteration budgets.
6. Reconstruct the patch in a fresh workspace and run targeted tests, the full
   suite, lint, typecheck, regression coverage, and deterministic risk review.
7. Stop again for a distinct, artifact-bound approval before recording one
   idempotent draft-PR package.
8. Draft technical and stakeholder updates plus one evidence-linked postmortem.

## How we built it

- Next.js 15 and strict TypeScript for the operator dashboard and incident room.
- FastAPI, Pydantic v2, strict mypy, SQLAlchemy, and Alembic for typed workflow
  contracts and persistence.
- OpenAI Responses API adapter using Pydantic structured outputs for bounded
  investigation synthesis. A retained credentialed smoke receipt proves that
  the `gpt-5.6` request returned `gpt-5.6-sol`, parsed into the strict schema,
  used `store=false`, and safely returned `insufficient_evidence` for sparse
  synthetic evidence.
- A secure Codex CLI gateway behind `CodeAgentGateway` with workspace-write
  confinement, network denial, secret-free environment, fixed invocation, and
  explicit engine provenance.
- The product and repository were developed side-by-side with Codex during
  Build Week, with agent handoffs and verification receipts retained under
  `docs/project/agent-runs/`.
- Deterministic fixture providers for a reliable offline demo that never
  silently becomes live when credentials are present.
- Separate approval bindings for patch execution and draft-PR creation,
  including artifact hashes, expiry, role checks, stale-state rejection, and
  idempotency.

## Challenges

The hardest problem was preserving trust while still making the workflow feel
agentic. Model output is only a typed proposal: deterministic code validates
citations, budgets, approval bindings, verification artifacts, and risk before
the workflow can advance. We also made provenance visible everywhere so a
fixture artifact can never be mistaken for a live OpenAI, Codex, or GitHub
action.

## Accomplishments

- Full two-approval golden path reaches `RESOLUTION_DRAFTED`.
- 185 backend tests, 20 web tests, and 6 shared-contract tests pass.
- 22 Chromium scenarios pass, including the real local-API resolution flow,
  accessibility checks, and overflow assertions at 375, 768, 1440, and 1920 px.
- Eight deterministic evaluation scenarios cover the golden path, insufficient
  evidence, flaky tests, risky migrations, redaction, prompt injection, noisy
  telemetry, and rollback cancellation.
- Five consecutive complete CLI demos pass against fresh ephemeral databases.
- Gitleaks reports no leaks across the full Git history after a narrowly documented
  synthetic-fixture exception.
- Both production Docker images build; API health and web HTTP checks pass.

## What we learned

Reliable agent products need an evidence model and an authorization model, not
just a prompt. The most useful design decision was separating intelligence from
authority: OpenAI/Codex adapters can propose or edit inside a sandbox, while the
state machine decides what is grounded, approved, verified, and safe to expose.

## What is next

- Diagnose the bounded Codex CLI zero-diff behavior and capture repository-work
  proof without making the offline demo depend on a live service.
- Add production evidence providers and PostgreSQL deployment proof.
- Add optional Slack delivery and a real draft-only GitHub integration for teams
  that enable those credentials and approval policies.

## Truthful disclosure for judges

The recorded golden demo must use deterministic fixture evidence and the
fixture code-agent unless the screen visibly shows a separately verified live
provider receipt. The default draft PR is a simulated offline artifact. No live
GitHub write, production deployment, or credentialed Codex call is claimed by
the current evidence package. One bounded GPT-5.6 Responses call is proven by a
safe hashed receipt and is separate from the offline golden demo.
