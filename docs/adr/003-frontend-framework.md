# ADR 003: Frontend Framework

## Status
Accepted (updated for M0 implementation)

## Context
We need a robust frontend framework for the Incident Commander dashboard and war room (blueprint section 18).

## Decision
Next.js 14 (App Router) with strict TypeScript:

- `tsconfig` enables `strict`, `noUncheckedIndexedAccess`, `noImplicitOverride`, `noFallthroughCasesInSwitch`; `allowJs` is off.
- All API types come from `@incident-commander/contracts`; no hand-rolled response shapes in the app.
- `lib/api.ts` is the only fetch layer. It returns a discriminated `ApiResult<T>` (never throws on transport errors) so pages degrade gracefully when the API is down.
- The M0 dashboard is a server component rendered dynamically (`force-dynamic`) against the live API; TanStack Query/Zustand/SSE arrive with the war room in M1+.
- Tests run under vitest (threads pool — the forks pool crashes tinypool on Windows paths containing spaces).

## Consequences
- Strong type safety across the frontend, aligned with backend contracts by construction.
- UI state is derived from server state, matching the blueprint's "durable state before UI optimism" principle.
