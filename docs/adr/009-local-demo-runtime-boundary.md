# ADR 009: Local demo runtime boundary

- Status: Accepted for hackathon submission
- Date: 2026-07-13

## Context

The blueprint's production target includes PostgreSQL, Redis, and a background worker. The submission must also retain a deterministic, credential-free judging path that can be reproduced on a laptop and in CI.

## Decision

The default Docker Compose stack starts PostgreSQL, Redis, API, web, and a lightweight Redis-heartbeat worker. Alembic runs against PostgreSQL before API startup, and typed health endpoints verify database, cache, and worker readiness. The five-run judging harness intentionally uses ephemeral SQLite and synchronous orchestration for deterministic isolation. The worker is claimed only as a health-heartbeat process, not as a workflow queue consumer.

## Consequences

- Judges can reproduce the full two-approval workflow without cloud accounts or service credentials.
- The Compose smoke proves PostgreSQL compatibility, migrations, Redis connectivity, and worker liveness, but not production-scale durability or multi-process workflow coordination.
- Moving beyond the hackathon boundary requires an idempotent queue consumer plus concurrency, recovery, load, and operational tests against a hosted topology.

## Guardrail

Documentation, health responses, screenshots, and submission text must distinguish the verified local runtime from a hosted production deployment and must not imply that the heartbeat worker consumes workflow jobs.
