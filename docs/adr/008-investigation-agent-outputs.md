# ADR 008: Typed Investigation-Agent Outputs (M3)

## Status
Accepted (M3 implementation)

## Context
M3 turns collected, redacted evidence into a root-cause investigation. The
output must be trustworthy under demo conditions and safe to act on: ranked
hypotheses that are grounded in persisted evidence, an explicit code/commit
mapping, honest unknowns and contradictions, and a path that refuses to drive
remediation when the evidence is thin. It must run with no credentials in demo
mode, stay deterministic for the golden checkout-api incident, and keep the
model gateway replaceable so a live structured-output model can drop in later.

Two failure modes we explicitly design against: a model fabricating evidence
IDs ("hallucinated citations"), and a model leaking chain-of-thought into
persisted, user-visible output.

## Decision

### Strict typed outputs
`app/domain/investigation.py` defines the structured outputs as Pydantic models
with `extra="forbid"` (`StrictModel`): `IncidentSummary`, `SpecialistFinding`,
`RankedHypothesis`, `CodeMapping`/`AffectedFile`, `FalsificationTest`,
`RejectedClaim`, the gateway `InvestigationDraft`, and the persisted
`InvestigationReport`. Every material claim carries `EvidenceCitation`s (a
persisted evidence ID plus a short note). The only narrative fields are
length-bounded (`rationale`, summary text); `extra="forbid"` means a gateway
cannot attach a `chain_of_thought` (or any other) field — the schema rejects
it. Model validators enforce contiguous ranks, non-increasing confidence, the
three-hypothesis minimum for a COMPLETE report, and that remediation can never
be enabled without a COMPLETE status.

### Bounded specialists + one manager stage
`app/providers/base.py` adds two protocols: `InvestigationSpecialist` (a
bounded, read-only analyst for one angle — telemetry, change correlation, code
mapping, runbook) and `InvestigationGateway` (a replaceable model gateway,
`model_id` env-driven via `INVESTIGATION_MODEL`). `InvestigationManager`
(`app/workflow/investigation_manager.py`) is the single explicit stage that
orchestrates them: run every specialist over the same persisted evidence,
reject any finding citing an unknown evidence ID, ask the gateway to synthesize
a draft from only the surviving findings, then re-validate every citation in
the draft against persisted evidence. Ungrounded hypotheses/summary/code-mapping
are recorded as `RejectedClaim`s and dropped; if a COMPLETE draft loses its
summary, code mapping, or drops below three grounded hypotheses, the manager
downgrades it to `INSUFFICIENT_EVIDENCE`. Remediation is enabled only when the
final status is COMPLETE.

### Persistence and API
`InvestigationReportModel` persists the full typed report as a JSON document
plus scalar `status`/`gateway`/`remediation_enabled` columns (migration
`c3d5f1a9b024`). The report is served read-only at
`GET /api/v1/incidents/{id}/investigation`; each ranked hypothesis is also
persisted as a `Hypothesis` row so the existing `/hypotheses` route returns all
three, ranked.

### Deterministic demo binding
`app/providers/simulated_investigation.py` implements the four fixture
specialists and `FixtureInvestigationGateway`, which synthesizes the golden
draft (top hypothesis: unsafe `session.discount.code` access from commit
`c7f2e9a`; `src/checkout.ts` + `src/checkout.test.ts` coverage gap) from the
fixture evidence, or an insufficient-evidence draft when a golden anchor is
missing. The gateway's `model_id` is environment-driven configuration; the
fixture output never depends on it.

## Consequences
- Unsupported claims cannot be acted on; the safe path disables remediation and
  stops the workflow at `NEEDS_INPUT` before any plan/patch/approval exists.
- Chain-of-thought cannot survive the strict schema into persistence or the API.
- A live gateway is a drop-in: implement `InvestigationGateway`, set
  `INVESTIGATION_MODEL`; the manager, validation, and persistence are unchanged.
- Gateway/specialist protocol changes must update the fixture bindings and the
  `tests/test_investigation.py` determinism/rejection tests in the same commit.
