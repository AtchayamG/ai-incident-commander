# Devpost Final Submission Answers

Prepared: 2026-07-14 (IST)

Live project: https://devpost.com/software/incident-commander-ai

## Required answers

| Field ID | Question | Prepared answer | Status |
|---|---|---|---|
| 27945 | Submitter Type | Individual | Confirmed and submitted |
| 27946 | Country of Residence | India | Confirmed and submitted |
| 27947 | Category | Developer Tools | Confirmed and submitted |
| 27948 | Code repository | https://github.com/AtchayamG/ai-incident-commander | Attached and publicly verified |
| 27950 | `/feedback` Session ID | `019f5282-7c6f-76d1-888e-ffb0c25de3c8` | Ready |

## Optional judge testing instructions (field 27949)

Clone the public repository and follow the README quick start. The simplest
path is `docker compose up -d --build`, then open `http://localhost:3000`.
No credentials are required. The deterministic judging workflow uses fixture
telemetry and a fixture code-agent and clearly labels the draft PR as simulated.
Run `make demo-reset`, `make demo-run`, and `make demo-assert` for the reproducible
two-approval path. The separately credentialed GPT-5.6 structured-output proof
is documented at `docs/submission/openai-live-smoke.md`.

## Developer-tool testing instructions (field 27951)

Supported on Windows, macOS, and Linux through Docker Desktop or Docker Engine.
Clone the repository, run `docker compose up -d --build`, open
`http://localhost:3000`, and follow the seeded incident from evidence through
both approval gates to `RESOLUTION_DRAFTED`. No external account or secret is
required. Full validation commands are listed in the README; the default demo
is deterministic and offline.

## Final personal certification required

Before the final submit action, the account holder confirmed all of the
following were true:

- the entrant is submitting as an individual;
- the entrant's country of residence is India;
- the entrant is at least the age of majority where they reside;
- none of the official-rules exclusions or conflicts of interest applies; and
- the entrant has reviewed and accepts the official rules.

These facts were explicitly confirmed in the build task and were not inferred
from account metadata or timezone. Devpost accepted submission `1078762`.
