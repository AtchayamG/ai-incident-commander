# M9 Five-Run Demo Reliability

Verified on 2026-07-13 with no external credentials:

```text
uv run --project services/api python -m app.demo.runner --runs 5
runs: 5
passed: true
```

Every run used a fresh ephemeral SQLite database and the deterministic fixture
investigation/code-agent providers. Each run exercised both public approval
decisions and asserted:

- final state `RESOLUTION_DRAFTED`;
- `provider_mode` is `simulated`;
- exactly two approval records;
- completed simulated draft-PR artifact;
- technical and stakeholder communication drafts; and
- an evidence-linked postmortem with 28 timeline events.

The protected reset command also passed and returned the golden incident in
`RECEIVED` with simulated provenance:

```text
uv run --project services/api python -m app.demo.runner --reset-only
```

Supporting gates after the runner addition:

```text
ruff check services/api                 PASS
mypy --strict services/api/app          PASS (45 source files)
pytest services/api/tests               PASS
focused demo-runner tests               PASS (2 tests)
```

One upstream Starlette/httpx deprecation warning remains. It does not affect
the run result. No OpenAI, GitHub, deployment, or production action occurred.
