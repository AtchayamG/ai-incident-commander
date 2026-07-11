# Incident Commander M1 Backend

## Changes Implemented
1. **SQLite Database adapter**: Implemented a complete `StoreProtocol` for the `SqlAlchemyStore` in `app/store/sql.py`. The SQLAlchemy adapter creates an `incidents` store that supports SQLite backend, fulfilling demo requirements without relying on Postgres.
2. **Schema & Migrations**: Configured SQLAlchemy 2 models mimicking the existing domain logic and generated the first Alembic migration (`alembic/versions/*_initial_schema.py`) to manage DB structures safely. 
3. **Idempotent Seed**: Made the `seed_demo` mechanism idempotent by checking if the golden incident exists before generating the data.
4. **Webhook Intake**: Created an extensible JSON webhook intake endpoint (`POST /api/v1/incidents/webhook`) with a dummy HMAC signature verification module.
5. **SSE Event Streaming**: Implemented an async stream endpoint (`GET /api/v1/incidents/{incident_id}/events/stream`) using `StreamingResponse` to continuously poll and transmit workflow events via SSE protocol.
6. **Robust Focused Tests**: Enhanced tests coverage in `test_persistence.py` mapping directly to the new features: a fresh-migration test, restart persistence test, webhook signature/data check test, and SSE streaming verification. All Type and Code style verifications have been addressed.

## Architecture Notes
- Kept the same typed domain state-machine in `app/workflow/pipeline.py` by converting to a generic `StoreProtocol` to interface successfully.
- Alembic configuration dynamically pulls DB path from `Settings.from_env()`.
- SSE leverages asyncio to prevent starvation while maintaining compatibility with the synchronous pipeline.

## Pending Items for Future Slices
- Postgres DB configuration is possible via `DATABASE_URL` environment variables when scaling up.
- Live telemetry implementations replacing the Simulated interfaces.
