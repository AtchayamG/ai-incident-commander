# M9 OpenAI Investigation Integration Tests

The focused suite verifies:

- `responses.parse` receives the configured model, timeout, and strict
  `InvestigationDraft` Pydantic schema;
- secret-shaped incident/evidence text is re-redacted before request creation;
- schema-invalid/unparsed responses fail closed;
- provider exceptions are redacted and mapped to typed internal errors;
- demo mode selects the fixture gateway even when live settings are present;
- live selection requires both explicit OpenAI routing and credential presence;
  and
- existing investigation/provider invariants still pass.

```text
ruff check focused files                         PASS
mypy --strict focused application files          PASS
pytest test_openai_investigation.py
       test_investigation.py test_providers.py    PASS (22 tests)
full backend pytest                               PASS (156 tests)
full backend strict mypy                          PASS (46 source files)
five-run deterministic demo                      PASS
```

All OpenAI calls were mocked. This proves request/response contracts and safety
routing, not account access, model availability, latency, cost, or a live
provider response. The official API pattern is documented by the
[OpenAI structured outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs).
