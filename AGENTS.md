# Repository Instructions

Source of truth: `docs/AI_INCIDENT_COMMANDER_MASTER_BLUEPRINT_v1.md`.

- Complete P0 milestones M0-M9 in order; P1 must not delay P0.
- Use strict typed contracts and deterministic fixture providers.
- Never expose secrets or claim simulated evidence is live.
- Require approval before workspace writes and external actions.
- Run untrusted repository commands only through the sandbox allowlist.
- Never merge, deploy, push protected branches, or perform production actions.
- Use `make lint`, `make typecheck`, `make test`, and `make demo-assert` as gates once available.
- Keep `docs/project/taskstatus.md`, `docs/project/handover.md`, `docs/project/BUILD_STATUS.json`, and `docs/project/CODEX_RESULT.md` accurate.

## External-agent routing (persistent project policy)

- Use the `orchestrate-external-coding-agents` skill for delegated project work in every session.
- Route complex architecture/backend/reasoning work to Claude `Fable 5` first while usage remains.
- When Fable usage is exhausted, route Claude work to `Opus 4.8`.
- Route UI/UX and suitable frontend/integration tasks to agy.
- Use Hermes for bounded implementation, tests, documentation, repair, or fallback when authenticated.
- Keep one clean worktree per writable worker, avoid overlapping file ownership, and reproduce all worker verification before integration.

## Repository structure

- Keep the project root clean and purpose-driven.
- Store documentation and durable project state under `docs/` with clear subfolders (`docs/project/`, `docs/adr/`, `docs/architecture/`, `docs/submission/`, `docs/testing/`).
- Root Markdown is limited to tooling/convention entrypoints: `AGENTS.md` and `README.md`.
- Do not create duplicate documentation trees or miscellaneous files at the root.
