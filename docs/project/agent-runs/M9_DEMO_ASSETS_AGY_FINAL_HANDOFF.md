# M9 Demo Assets Handoff

## Result

Status: draft assets integrated after M8 and refreshed against the verified M0-M8 baseline.

## Done

- Prepared a 2:30 judge-focused [demo script](../../submission/demo-script.md).
- Prepared a shot-by-shot [demo storyboard](../../submission/demo-storyboard.md).
- Prepared a claim-to-proof [evidence checklist](../../submission/evidence-checklist.md).
- Updated the proven local flow through M7's separate approval and `RESOLUTION_DRAFTED` artifacts.
- Labeled deterministic investigation and patch generation as simulated fixture paths; final OpenAI-provider and live Codex proof remain pending M9.
- Marked the deterministic draft PR, communications, postmortem, and M8 product polish proven; kept Docker/PostgreSQL validation, five-run reliability, secret scan, OpenAI/Codex live proof, and final packaging pending M9.
- Replaced worktree-specific file URIs with portable repository-relative links.

## Blocked

- None for drafting. Final narration and evidence statuses must be refreshed after M7, M8, and M9 validation.

## Risk

- Judge material can become misleading if pending labels are removed before the corresponding proof exists.
- The optional GitHub adapter must never be presented as live unless an explicitly approved, credentialed draft-only run is separately proven.

## Next

1. Complete M9 OpenAI-provider/Codex proof without making deterministic demo mode depend on external services.
2. Complete the five-run golden flow, secret scan, and optional local Docker/PostgreSQL proof.
3. Capture the recording and perform the final submission audit.

## Exact checks

- Portable Markdown link validation: 24 relative links resolved, 0 broken.
- Search across the three submission assets: no absolute file URI schemes or worktree-specific paths.
- `git diff --check`: required again by the integrator after the final truthfulness corrections.

## Integrator corrections

Codex corrected residual overclaims after the agy repair: “eliminating hallucination,” live Codex use in the default demo, an already mock-proven GitHub adapter, and an existing communications schema. The assets now distinguish implemented fixture behavior from pending OpenAI, M7, and infrastructure proof.
