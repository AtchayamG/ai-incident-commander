# M3 Handoff — Typed Investigation-Agent Outputs

Branch: `agent/m3-investigation` · Role: architecture/backend · Scope: `services/api/**`, `docs/**`

## Objective (met)
Typed, evidence-grounded investigation for the deterministic golden incident:
three ranked hypotheses, code/commit mapping, explicit unknowns and
contradictions, structured validation, and a safe insufficient-evidence path —
all behind a replaceable, environment-driven model gateway that needs no
credentials in demo mode.

## What shipped

### Structured outputs (strict Pydantic)
`app/domain/investigation.py` — `IncidentSummary`, `SpecialistFinding`,
`RankedHypothesis`, `CodeMapping`/`AffectedFile`, `FalsificationTest`,
`EvidenceCitation`, `RejectedClaim`, `InvestigationDraft`, `InvestigationReport`.
All `extra="forbid"` (no chain-of-thought can attach). Validators enforce
contiguous ranks, non-increasing confidence, ≥3 hypotheses for COMPLETE, and
"remediation only when COMPLETE". Every hypothesis mandates supporting AND
contradicting citations plus ≥1 unknown and ≥1 falsification test.

### Bounded specialists + one manager stage
- `app/providers/base.py` — `InvestigationSpecialist` and `InvestigationGateway`
  protocols (`model_id` env-driven).
- `app/providers/simulated_investigation.py` — four fixture specialists
  (telemetry, change-correlation, code-mapping, runbook) + `FixtureInvestigationGateway`.
- `app/workflow/investigation_manager.py` — **the single explicit stage**. Runs
  specialists → rejects findings citing unknown evidence → gateway synthesizes
  draft from surviving findings → re-validates every draft citation against
  persisted evidence → downgrades to INSUFFICIENT_EVIDENCE if a COMPLETE draft
  loses summary/code-mapping or drops below 3 grounded hypotheses. Rejected
  claims recorded, never acted on. Remediation enabled only when COMPLETE.

### Golden result (deterministic)
Top hypothesis: unsafe `session.discount.code` access from commit `c7f2e9a`,
shipped in deploy `2026.07.13.4`. Code map: `src/checkout.ts` (defect site),
`src/checkout.test.ts` (coverage gap — no no-discount test). Plus two lower
ranked hypotheses (malformed-discount data, infra/rollout), each with
contradicting evidence + unknowns + bounded falsification steps. All citations
resolve to persisted, redacted evidence IDs.

### Persistence + API
- `InvestigationReportModel` (JSON document + scalar `status`/`gateway`/
  `remediation_enabled`). Store methods on protocol/memory/sql.
- Migration `alembic/versions/c3d5f1a9b024_investigation_reports.py`
  (down_revision `7b91c4e2a6d5`).
- `GET /api/v1/incidents/{id}/investigation` → `InvestigationReport` (404 until
  run). `/hypotheses` now returns all three ranked hypotheses.

### Wiring / config
- `INVESTIGATION_MODEL` env var → `Settings.investigation_model`
  (default `simulated-fixture`); demo mode needs no credentials.
- `main.py` builds the manager from fixture specialists + gateway.
- Pipeline `_investigate` runs the manager, persists report + hypotheses. On
  non-COMPLETE it stops at `NEEDS_INPUT` — no plan/patch/approval created, so
  approval gates and remediation are disabled by construction.

## Tests / results (Python 3.12, `services/api`)
- `py -3.12 -m ruff check .` → **All checks passed!**
- `py -3.12 -m mypy` (strict) → **Success: no issues found in 44 source files**
- `py -3.12 -m pytest` → **66 passed, 1 warning** (pre-existing httpx deprecation)

New file `tests/test_investigation.py` (12 tests) covers:
- schema rejection (missing contradicting/unknowns, extra field, <3 hyps,
  remediation-without-complete),
- top-hypothesis / citation / code-map determinism (two runs byte-identical),
- unsupported specialist claim rejected while report stays COMPLETE,
- ungrounded hypothesis rejected → safe downgrade to INSUFFICIENT_EVIDENCE,
- missing-evidence → INSUFFICIENT_EVIDENCE + remediation disabled,
- pipeline insufficient path stops at NEEDS_INPUT with no plan/approval,
- golden report persisted and served via the route.

`tests/test_persistence.py::test_fresh_migration` extended to assert the new
`investigation_reports` table works after `alembic upgrade head` (no
`create_all` shortcut). `tests/test_incidents_api.py` updated: `/hypotheses`
now returns 3, ranked, top = unsafe access.

## Notes for the next agent
- Live gateway is a drop-in: implement `InvestigationGateway`, set
  `INVESTIGATION_MODEL`; manager/validation/persistence unchanged.
- `Hypothesis` contract (mirrored in `packages/contracts`) was left unchanged;
  rich ranked data lives on `InvestigationReport` via `/investigation`.
- ADR: `docs/adr/008-investigation-agent-outputs.md`.
- Dev tools (alembic/ruff/mypy) were installed into the Python 3.12 interpreter
  to run the suite; no project venv is checked in.
- No commits made (per constraints).
