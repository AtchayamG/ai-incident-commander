# Debugging Log

## 2026-07-12 — Windows Next.js production build teardown

- Symptom: Next.js 14.2.15 compiles and generates 4/4 pages, then exits 1 with `uncaughtException Error: kill EPERM` from `jest-worker` teardown.
- Reproduced on the primary worktree after a frozen pnpm install.
- Impact: production build gate remains false; generated artifacts are not accepted as a passing build.
- Next action: isolate the Windows worker-process cause or upgrade the affected Next.js toolchain, then rerun build and tests.

Resolution:

- Next.js 14.2.35 alone still reproduced the failure.
- Configuring Next's supported `experimental.workerThreads=true` and `cpus=1` avoids the failing child-process teardown path.
- Production build now exits 0 and generates all routes; no process errors are suppressed.

## 2026-07-12 — M1 backend repair

- Initial delegated slice failed with 80 ruff errors, 14 mypy errors, and import-time failure.
- Repair reduced failures to SQLite naive datetime comparisons and a hanging continuous SSE test.
- Normalized persisted approval expiry timestamps to UTC and added explicit `once=true` bounded SSE snapshot semantics for deterministic tests.
- Final result: ruff pass, strict mypy pass (36 files), pytest 39 passed.
