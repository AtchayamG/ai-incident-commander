# ADR 005: Demo Mode

## Status
Accepted (updated for M0 implementation)

## Context
Reviewers and users must be able to run the application without configuring API keys or external services, and the demo must be assertable (deterministic) for the golden-demo gate.

## Decision
`DEMO_MODE=true` is the default. In demo mode:

- Simulated providers are bound for telemetry, investigation, code agent, verification, and pull requests; no network calls, no credentials.
- Simulated output is deterministic (fixed fixtures, no randomness) so two fresh runs produce identical evidence, hypotheses, diffs, and state transitions (`tests/test_demo_determinism.py`).
- Simulated evidence is explicitly labelled (`[SIMULATED]` summaries, `provenance.simulated = true`) and is never presented as live data.
- A golden incident (`inc-demo-0001`, blueprint section 17.1 example) is seeded at startup.
- `POST /api/v1/incidents/reset-demo` wipes and re-seeds the store; it requires the `X-Demo-Admin-Key` header matching `DEMO_ADMIN_KEY` and is rejected outright when demo mode is off. (Deviation from blueprint 17.1: reset is store-global rather than per-incident because the M0 store is a single demo tenant.)
- `DEMO_MODE=false` makes app startup raise `NotImplementedError` until live providers exist (M4-M7) — the system never silently pretends live mode works.

## Consequences
- Instant onboarding for reviewers and a byte-stable golden path for CI assertion.
- Simulated implementations must be maintained alongside provider interfaces.
