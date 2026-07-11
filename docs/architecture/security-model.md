# Security Model (M0)

Blueprint source: section 21. M0 implements the foundations; sandbox and auth arrive with later milestones.

## Boundaries implemented in M0

| Boundary | Implementation | Test |
|---|---|---|
| Redaction | `app/security/redaction.py`; pipeline redacts every provider payload before persistence; evidence records `redaction_applied` | `tests/test_redaction.py`, planted fixture secret asserted in `tests/test_incidents_api.py` |
| Human approval | Approval-gated state transitions; server checks pending/unexpired/artifact-version before effect; decisions immutable | `tests/test_incidents_api.py` approval cases |
| Deterministic policy around models | Providers return proposals; pipeline validates (change budget) and owns state | `tests/test_providers.py`, `tests/test_state_machine.py` |
| Demo admin | `reset-demo` requires `X-Demo-Admin-Key` = `DEMO_ADMIN_KEY`, demo mode only | `test_reset_demo_requires_admin_key` |
| CORS | Web origin only; GET/POST; minimal headers | wired in `app/main.py` |

## Redaction rules

private key blocks, `sk-*` keys, AWS access keys, GitHub tokens, bearer tokens, credentials embedded in URLs, `key=value` assigned secrets (key name preserved, value redacted), email addresses. Placeholders are stable (`[REDACTED:<rule>]`) to keep the demo deterministic.

## Defaults

- No endpoint ever returns credentials.
- Simulated data is labelled simulated (`provenance.simulated`, `[SIMULATED]` prefixes) — never presented as live.
- Live mode without implemented providers is a startup error, not a silent fallback.
- `.env` is gitignored; `.env.example` contains no real secrets.

## Deferred (with landing milestone)

Sandbox allowlist execution (M4), webhook signature verification (M1-M2 with webhook intake), authn/z and tenancy (P1), rate limiting (P1), audit_events table (M1 persistence).
