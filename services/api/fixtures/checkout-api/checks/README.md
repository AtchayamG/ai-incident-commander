# checkout-api fixture verification toolchain

`harness.mjs` is the deterministic, zero-dependency check toolchain for the
checkout-api fixture repository (blueprint 19.3: allowed commands come from
repository configuration). `verification_manifest.json` maps the plan's
baseline command strings (`npm test`, `npm run lint`, ...) to pinned argv
invocations of this harness so the M6 verifier runs real subprocesses with no
shell, no package installs, and no network.

Honest labels:

- **test / targeted-test** — genuinely executes `src/checkout.test.ts`
  against `src/checkout.ts` under node's `--experimental-strip-types`
  loader with a minimal `describe`/`it`/`expect(...).toBe` shim. The patched
  code really runs: an unguarded `session.discount.code` really throws a
  `TypeError` and fails the check.
- **lint** — deterministic minimal ruleset (`no-var`, `no-console`,
  `eqeqeq-allow-null`), not full eslint.
- **typecheck** — strip-types module-load check (syntax + import resolution
  + exported-function shape), explicitly not full tsc type analysis; the
  check output says so.

Output is timestamp-free and byte-deterministic so the golden demo can be
compared across runs. Exit code 0 = pass, 1 = fail, 2 = harness misuse.
