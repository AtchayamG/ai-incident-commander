# M9 Secret Scan

Gitleaks 8.30.1 scanned the current repository and all 80 commits on
2026-07-13:

```text
gitleaks detect --source . --redact --no-banner --exit-code 1 --verbose
80 commits scanned
~2.54 MB scanned
no leaks found
```

The first scan reported one intentional synthetic Stripe-shaped credential in
`services/api/fixtures/checkout-api/telemetry/error_samples.log`. That fixture
exists specifically to prove ingestion-boundary redaction. `.gitleaks.toml`
contains a narrow allowlist requiring all of the following:

- the `generic-api-key` rule;
- that exact fixture path; and
- the exact synthetic log-line marker.

It does not disable the rule or ignore the whole fixture directory. The scan
passed after this documented false-positive treatment. Output was redacted;
no credential value is reproduced here.
