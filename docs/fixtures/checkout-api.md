# [SIMULATED] checkout-api fixture repository

Deterministic demo fixture for the golden incident (blueprint section 32).
Everything in this directory is simulated data consumed by the fixture
providers in `app/providers/simulated.py`; nothing here is executed or
deployed. There is intentionally no nested `.git` directory — commit and
deploy history are plain JSON/diff artifacts under `repo/history/` and
`deploys/`.

Layout:

- `repo/src/checkout.ts` — source snapshot at deployed version `2026.07.13.4`
  containing the unsafe `session.discount.code` regression.
- `repo/src/checkout.test.ts` — test suite that covers discounted sessions
  only (the coverage gap the incident exposes).
- `repo/history/commits.json` — commit history; `c7f2e9a` (09:48 UTC) is the
  regressing commit.
- `repo/history/c7f2e9a.diff` — diff artifact for the regressing commit.
- `deploys/deploys.json` — deployment history; `2026.07.13.4` at 10:02 UTC.
- `telemetry/alerts.json` — HTTP 500 rate alert (0.2% -> 12.4%), incident
  start 10:05 UTC.
- `telemetry/error_samples.log` — raw error samples with the stack trace
  pointing at `src/checkout.ts`. Contains planted secret-shaped tokens so
  tests can prove the redaction boundary holds before persistence.
- `telemetry/samples_analysis.json` — failure correlation: only sessions
  without a discount fail.
- `services/api/fixtures/checkout-api/runbooks/checkout-api.txt` — runbook guidance (deployment correlation,
  local reproduction).
