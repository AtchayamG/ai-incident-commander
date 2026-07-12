# checkout-api golden patch fixtures (M5)

`golden_patch.diff` is the expected unified diff of one successful bounded
patch execution against the checkout-api fixture repository at its immutable
base (`services/api/fixtures/checkout-api/base_manifest.json`):

- restores the optional discount access in `src/checkout.ts`
  (`session.discount?.code ?? null`), and
- adds the missing no-discount regression test in `src/checkout.test.ts`.

It is produced by the **deterministic fixture gateway** (`fixture-codex`,
explicitly labeled `simulated`) running inside the M5 ephemeral sandbox
workspace; it is not live Codex output. `services/api/tests/test_sandbox_executor.py`
asserts the captured execution diff matches this file byte-for-byte, so any
change to the fixture repo, the gateway edit, or the diff capture shows up as
a golden regression.

Newlines are normalized to LF; regenerate by running the golden path and
saving `unified_diff` from `GET /api/v1/incidents/{id}/patch-executions`.
