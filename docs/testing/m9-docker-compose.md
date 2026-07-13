# M9 Docker Compose Verification

Verified locally on 2026-07-13 with Docker Desktop 29.5.3 and Compose 5.1.4.

The first web-image build exposed a cross-platform context bug: host
`node_modules` content could overwrite pnpm's Linux workspace links. A root
`.dockerignore` now excludes host dependencies, build outputs, caches,
databases, and unrelated documentation from the web build context. Browser
verification then exposed and fixed three additional container-only gaps:

- the public bundle now uses `http://localhost:8000`, not the Compose-only
  `api` hostname;
- the detail page requests optional artifacts only after their workflow state
  makes them available, eliminating expected-404 console noise; and
- the API image includes the exact Node 22 runtime required by the offline
  TypeScript verification harness.

After the fix:

```text
docker compose config             PASS
docker compose up -d --build      PASS
API image build                   PASS (OpenAI SDK 2.45.0 installed)
Web production build              PASS (Next.js 14.2.35)
API container                     healthy
API verifier runtime              Node v22.23.1
GET http://localhost:8000/health/ready
  200 {"status":"ok","demo_mode":true,"provider_mode":"simulated"}
GET http://localhost:3000/        200
fresh browser console             0 errors, 0 warnings
approval gate 1                   PASS; six verification checks pass
approval gate 2                   PASS; simulated draft PR only
terminal workflow state           RESOLUTION_DRAFTED
docker compose down               PASS; containers/network removed
```

Screenshots from this exact run are retained under
`docs/submission/screenshots/`. This is local container-build and complete demo
proof only. It is not a deployment, production-readiness, live provider, or
PostgreSQL claim; the Compose demo uses SQLite and simulated providers.
