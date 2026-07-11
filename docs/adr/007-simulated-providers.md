# ADR 007: Simulated Providers

## Status
Accepted (updated for M0 implementation)

## Context
During local testing and demo mode, we need the workflow to exercise external-system interactions (telemetry, code agents, GitHub) without real network calls, while keeping the door open for live adapters in M4-M7.

## Decision
`app/providers/base.py` defines `runtime_checkable` Protocols that domain and workflow code depend on exclusively:

- `TelemetryProvider.fetch_evidence` — signals/logs/deploy history
- `InvestigationProvider.propose_hypothesis` / `propose_plan` — wraps OpenAI Agents SDK in live mode
- `CodeAgentGateway.propose_patch` — wraps OpenAI Codex SDK against an isolated workspace in live mode
- `VerificationRunner.verify` — test/lint/typecheck execution
- `PullRequestProvider.create_draft_pr` — idempotency-keyed external writes

`app/providers/simulated.py` implements all five deterministically (fixture data, fixed timestamps, no randomness). Protocol conformance is asserted in `tests/test_providers.py`. All provider outputs are proposals; the workflow pipeline validates them and owns state.

## Consequences
- Core logic is decoupled from external API availability; live adapters are drop-in.
- Provider interface changes must update the simulated implementations and conformance tests in the same commit.
