# ADR 006: Security Defaults

## Status
Accepted (updated for M0 implementation)

## Context
The AI will handle sensitive logs, code, and infrastructure states. We need to prevent accidental leakage or unauthorized destructive actions.

## Decision
Three concrete boundaries exist from M0 onward:

1. **Redaction boundary** (`app/security/redaction.py`): all external content (telemetry, logs, webhook payloads) passes through `redact()` before persistence or display. Rules cover private key blocks, OpenAI/AWS/GitHub tokens, bearer tokens, URL-embedded credentials, `key=value` secrets, and email addresses. Each evidence item records `redaction_applied` and the pipeline stores only redacted content — raw payloads never cross the boundary.
2. **Approval gates**: transitions `WAITING_PATCH_APPROVAL → PATCHING` and `WAITING_PR_APPROVAL → CREATING_PR` are approval-gated in the state machine. The approvals endpoint verifies the request is pending, unexpired, and (when supplied) that the artifact version matches before any effect; decided approvals cannot be re-decided.
3. **Deterministic policy around the model**: agents/providers return typed proposals; deterministic code validates them (e.g., the change budget check rejects patches exceeding the plan's file/line budget) and owns every state transition.

Additional defaults: CORS restricted to the web origin with a minimal method/header list; the demo reset endpoint requires an admin key; no credentials are ever echoed by any endpoint.

## Consequences
- Leakage is contained even when fixture or live data embeds secrets (tested with a planted fixture secret).
- External effects always require a recorded human decision.
