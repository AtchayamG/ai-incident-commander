# Repository Instructions

Source of truth: `docs/AI_INCIDENT_COMMANDER_MASTER_BLUEPRINT_v1.md`.

- Complete P0 milestones M0-M9 in order; P1 must not delay P0.
- Use strict typed contracts and deterministic fixture providers.
- Never expose secrets or claim simulated evidence is live.
- Require approval before workspace writes and external actions.
- Run untrusted repository commands only through the sandbox allowlist.
- Never merge, deploy, push protected branches, or perform production actions.
- Use `make lint`, `make typecheck`, `make test`, and `make demo-assert` as gates once available.
- Keep `taskstatus.md`, `handover.md`, `BUILD_STATUS.json`, and `CODEX_RESULT.md` accurate.

