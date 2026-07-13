# M9 OpenAI Investigation Integration — Handoff

Status: implemented and mock-verified; credentialed live proof remains pending.

## Delivered

- Optional OpenAI Responses API investigation gateway using Pydantic structured output.
- Explicit `INVESTIGATION_ENGINE`, configurable model, and bounded timeout.
- Unconditional fixture routing in demo mode, even when live configuration exists.
- Fail-closed live selection when the engine, model, or API credential is absent.
- Bounded, re-redacted model input containing only normalized incident data,
  persisted evidence IDs/content, hashes, display references, and already-validated
  specialist findings.
- Strict `InvestigationDraft` output; the deterministic `InvestigationManager`
  remains authoritative for evidence-citation and remediation eligibility checks.
- Safe typed provider errors with redacted messages.

The implementation follows OpenAI's official structured-output pattern:
Python `client.responses.parse(...)`, a Pydantic `text_format`, and
`response.output_parsed` ([OpenAI structured outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)).

## Verification

- Focused Ruff: pass.
- Focused strict mypy: pass.
- OpenAI/investigation/provider tests: 22 pass.
- Full backend: Ruff pass, strict mypy pass (46 source files), 156 tests pass.
- Five complete deterministic demo runs pass after the SDK integration.
- No network calls were made; the Responses client was mocked.

## Codex gateway review

The existing `CodexCliGateway` and sandbox tests already prove the required
seam: fixed `codex exec` invocation, workspace-write confinement, network
denial, secret-free child environment, configured model/provenance, and
fail-closed authentication/binary behavior. No redesign was needed. A real
credentialed Codex turn was not run or claimed in this handoff.

## Remaining proof

- Run one explicitly approved, cost-aware OpenAI smoke against redacted fixture
  evidence and retain the provider response identifier/provenance without the
  prompt or secret.
- Run one explicitly approved Codex CLI fixture-workspace smoke and retain its
  diff/engine receipt.
- Full `DEMO_MODE=false` application startup remains intentionally disabled
  until non-fixture evidence sources exist, avoiding a misleading hybrid mode.
