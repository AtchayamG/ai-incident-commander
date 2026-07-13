# Credentialed GPT-5.6 smoke proof

Verified: 2026-07-13 at 15:16:52 UTC.

The bounded submission smoke invoked the repository's production `OpenAIInvestigationGateway` through the Responses API with model alias `gpt-5.6`. OpenAI returned `gpt-5.6-sol`, and the SDK parsed the response directly into the strict `InvestigationDraft` Pydantic schema.

The input was intentionally sparse synthetic incident evidence. The model returned `insufficient_evidence`, which is the required safe behavior: the gateway did not manufacture a root-cause conclusion without sufficient cited support.

Safety properties proven by the request:

- synthetic, non-secret input only;
- low reasoning effort for bounded cost;
- `store=false` on the API request;
- no tools or external actions;
- no chain-of-thought requested or persisted;
- response identifier retained only as SHA-256;
- 1,282 input tokens, 458 output tokens, 1,740 total tokens.

Machine-readable safe receipt: [openai-live-smoke-receipt.json](openai-live-smoke-receipt.json).

Reproduction requires an authorized key and incurs API usage:

```bash
make openai-smoke
```

The default golden demo remains fully offline and does not depend on this credentialed path.
