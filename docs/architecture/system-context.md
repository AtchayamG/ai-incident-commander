# System Context (M0)

## What exists after M0

```
Browser ──> Next.js web (apps/web, :3000)
                │  typed client (lib/api.ts) + @incident-commander/contracts
                ▼
        FastAPI API (services/api, :8000)
                │
     ┌──────────┼───────────────────────────────┐
     ▼          ▼                               ▼
 InMemoryStore  WorkflowPipeline ──> state_machine (only state authority)
                │
                ▼ (typed proposals only)
        Simulated providers: telemetry, investigation,
        code agent, verification, pull request
```

- **Demo mode only.** `DEMO_MODE=true` binds simulated providers; `DEMO_MODE=false` refuses to start until live adapters exist (M4-M7).
- **Redaction boundary** sits between providers and the store: `app/security/redaction.py`.
- **Approval gate**: the pipeline halts at `WAITING_PATCH_APPROVAL`; a human decision through `POST /api/v1/approvals/{id}/decision` resumes or cancels it.

## Module map (services/api/app)

| Module | Responsibility |
|---|---|
| `domain/` | Enums + Pydantic contracts (source of truth; mirrored in packages/contracts) |
| `workflow/state_machine.py` | Legal transitions, terminal/recoverable sets, approval-gated pairs |
| `workflow/pipeline.py` | Deterministic golden-path orchestration; writes append-only workflow events |
| `providers/` | Protocols (`base.py`) + deterministic fixtures (`simulated.py`) |
| `security/redaction.py` | Secret/PII scrubbing before persistence |
| `store/memory.py` | In-memory repository (M1 replaces internals with SQLAlchemy, same surface) |
| `demo/seed.py` | Golden incident `inc-demo-0001` |
| `api/routes/` | health, incidents, approvals routers |

## What M0 deliberately does not include

Durable worker/queue, SSE, Postgres/Redis usage (compose services exist behind the `persistence` profile), auth/tenancy, OpenAI SDK calls, GitHub adapter, sandbox runner. Interfaces for all of these are represented so M1-M7 slot in without contract changes.
