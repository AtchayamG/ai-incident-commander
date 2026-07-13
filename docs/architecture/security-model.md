# Security Model

## Enforced boundaries

| Boundary | Current enforcement | Evidence |
|---|---|---|
| Redaction before persistence/model use | Stable rules for keys, tokens, private keys, URL credentials and email | `test_redaction.py`, `test_redaction_persistence.py` |
| Patch approval | Single-use, expiring, role- and artifact-bound decision before workspace write | `test_remediation.py`, `test_sandbox_executor.py` |
| PR approval | Separate binding to the passing patch/verification artifacts | `test_m7_pr_communications.py` |
| Workspace confinement | Checksum-pinned fixture copy, guarded relative paths, file/line budgets, cleanup proof | `test_sandbox_workspace.py`, `test_sandbox_executor.py` |
| Command confinement | Exact command-to-argv manifest, no shell, bounded time/output/environment | `test_verification.py` |
| Risk blocking | Auth, payment, migrations, infrastructure, cryptography, secret material and oversized diffs block PR | `workflow/risk.py`, `test_verification.py` |
| Demo truthfulness | Simulated provenance on evidence, code-agent and PR artifacts; live configuration cannot silently replace demo providers | provider and browser tests |
| Secret scanning | Gitleaks scans staged changes and full Git history | `docs/testing/m9-secret-scan.md` |

## Trust boundaries

- The browser never receives provider credentials.
- External evidence is treated as untrusted data, redacted, bounded, and cited;
  it is never executed as instructions.
- The code-agent may edit only its ephemeral workspace after approval. It does
  not decide state transitions, verification results, risk, or PR authority.
- Verification reconstructs the stored diff in a separate fresh workspace.
- Automated tests and demo runs never perform live external actions.

## Honest limitations

- Demo reset is protected by a shared demo admin key, not production identity.
- Authn/z, multi-tenancy, webhook signatures/replay protection, rate limiting,
  and OS-level egress isolation are not implemented and are not claimed.
- The offline harness enforces network denial by exposing no network command;
  it is not an OS network namespace.
- Optional OpenAI, Codex CLI, and GitHub integrations are mock-tested or
  fail-closed. Credentialed smoke receipts remain external evidence work.
