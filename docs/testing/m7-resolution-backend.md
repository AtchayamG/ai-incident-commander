# M7 Backend Verification

Run from the repository root:

```powershell
uv run --project services/api ruff check services/api
uv run --project services/api mypy --strict services/api/app
uv run --project services/api pytest services/api/tests
```

The focused suite is `services/api/tests/test_m7_pr_communications.py`. It covers:

- approval creation only after passing, non-blocked verification;
- exact binding, role, expiry, stale artifact, rejection, single-use, and missing-binding refusal;
- explicit simulated provenance and typed draft-PR responses;
- stable idempotency, failure renewal, redaction, retry, and completed-receipt reuse;
- SQL store reopen persistence;
- demo-mode isolation from ambient GitHub configuration;
- optional GitHub draft-only request mocking, configured refs, timeout, redaction, and diff exclusion;
- persisted technical/stakeholder/resolution drafts without deployment or mitigation claims;
- evidence-linked postmortem timeline, prioritized actions, Markdown, and upsert behavior;
- a real Alembic upgrade on an empty SQLite database with table/index inspection.

For a manual empty-database migration in PowerShell, set `DATABASE_URL` to a new SQLite file before running Alembic from `services/api`:

```powershell
$env:DATABASE_URL = "sqlite:///C:/path/to/fresh.db"
uv run alembic upgrade head
```

The optional GitHub adapter is not part of deterministic demo proof. It requires live mode plus token, repository, and pre-existing head/base refs. Tests mock the HTTP boundary; they never access GitHub.
