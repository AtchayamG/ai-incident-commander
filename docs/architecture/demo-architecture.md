# Demo Architecture (M0)

Deterministic, credential-free, assertable. Blueprint sources: sections 23.4, 26.2, 32-33.

## Golden incident

`inc-demo-0001` — "Checkout API elevated 500 errors" (`checkout-api`, production, SEV2), seeded at startup by `app/demo/seed.py`.

## Golden path walkthrough (all simulated)

1. `POST /api/v1/incidents/inc-demo-0001/start`
   - Pipeline advances through evidence collection: 3 fixture evidence items (metric spike, error log, deploy event), each redacted and timeline-linked. The fixture log plants `api_key=sk-demo...` which must appear redacted.
   - Investigation produces one hypothesis (bad deploy d-4821, confidence 0.85) and a remediation plan (1 file / 10 line change budget).
   - Halts at `WAITING_PATCH_APPROVAL` with a pending `APPLY_PATCH` approval.
2. `POST /api/v1/approvals/{id}/decision` with `{"decision": "approved", ...}`
   - `PATCHING`: simulated Codex gateway returns a fixed 1-file/2-line diff; change budget enforced.
   - `VERIFYING`: simulated runner passes unit/lint/typecheck checks.
   - Ends at `REVIEW_READY`. Rejection ends at `CANCELLED`.
3. `POST /api/v1/incidents/reset-demo` (header `X-Demo-Admin-Key`) wipes and re-seeds.

## Determinism guarantee

`tests/test_demo_determinism.py` runs the full path on two fresh app instances and asserts identical evidence tuples, hypothesis, diff, and transition sequence. Simulated providers use fixed fixtures and fixed timestamps; store IDs are counter-based.

## Running it

```
make docker-up          # api :8000 + web :3000
# or natively:
make setup && make dev-api   # then make dev-web in another terminal
```

No environment variables are required; defaults are demo-safe.
