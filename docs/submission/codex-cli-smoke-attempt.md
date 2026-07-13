# Credentialed Codex CLI smoke attempt

Checked: 2026-07-13.

The bounded live adapter successfully reached `gpt-5.6-sol` through Codex CLI 0.144.3 twice. Both invocations exited successfully but produced an empty workspace diff, so neither run qualifies as repository-work proof and no successful live Codex claim is made.

Safety controls remained active:

- immutable synthetic checkout only;
- ephemeral workspace destroyed after each run;
- agent-tool network access denied;
- only two approved fixture paths writable;
- 40-line change cap;
- parent API keys and cloud credentials excluded from the subprocess environment;
- raw event streams discarded, retaining only SHA-256 and event counts.

Safe attempt receipts:

| Attempt | Events | Event stream SHA-256 | Exit | Diff |
|---|---:|---|---:|---|
| 1 | 12 | `c0282d0e524c3b4a79e29839d40b2e99092e9a9e18808bc78343c0b61b0b3f5e` | 0 | empty |
| 2 | 18 | `728d6b910c83f8ea509ca68eadd1b4ad37d7651e374e66a5b4d28a8e1cced4bb` | 0 | empty |

This limitation does not affect the offline golden demo, which uses an explicitly simulated fixture code-agent. The separate GPT-5.6 Responses structured-output proof passed and is documented in `openai-live-smoke.md`.
