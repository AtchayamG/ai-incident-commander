# Dependency security verification

Verified on 2026-07-13 after upgrading the web stack.

## JavaScript

- Next.js and `eslint-config-next`: 15.5.18.
- Vitest: 3.2.7.
- Vite is constrained to the patched 6.4.3-or-newer line through the pnpm override.
- PostCSS is constrained to the patched 8.5.10-or-newer line through the pnpm override.
- `pnpm audit --audit-level moderate` reports no known vulnerabilities.
- Lint, strict TypeScript, 26 unit/contract tests, the containerized production build, and all 22 Playwright scenarios pass after the upgrade.

## Python

- `pip-audit services/api` reports no known vulnerabilities for the resolved backend project.
- CI installs the backend project and runs `pip-audit` against the resulting environment.

## CI policy

The security job performs a full-history Gitleaks scan, Python advisory scan, and JavaScript advisory scan. The container job builds the API, worker, and web images. A new high/critical JavaScript advisory or any known Python advisory fails CI.
