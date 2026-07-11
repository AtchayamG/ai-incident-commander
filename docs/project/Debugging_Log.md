# Debugging Log

## 2026-07-12 — Windows Next.js production build teardown

- Symptom: Next.js 14.2.15 compiles and generates 4/4 pages, then exits 1 with `uncaughtException Error: kill EPERM` from `jest-worker` teardown.
- Reproduced on the primary worktree after a frozen pnpm install.
- Impact: production build gate remains false; generated artifacts are not accepted as a passing build.
- Next action: isolate the Windows worker-process cause or upgrade the affected Next.js toolchain, then rerun build and tests.
