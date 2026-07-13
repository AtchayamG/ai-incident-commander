# M7 Resolution UI Verification

Verified on the combined M7 backend and UI integration:

```text
npm run lint                 PASS
npm run typecheck            PASS
npm test -- --run            PASS (20 tests)
npm run build                PASS
npm run test:e2e             PASS (16 tests)
```

Coverage includes the two-approval boundary, stale/expired approval handling, failed
verification blocking, idempotent resolution retry behavior, simulated provenance,
communications and postmortem rendering, mobile layout, and a real local-API golden path
ending in `RESOLUTION_DRAFTED`.

No live GitHub external action was executed; optional live-mode behavior remains mocked.
