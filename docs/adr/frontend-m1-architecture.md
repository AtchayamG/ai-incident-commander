# ADR: M1 Frontend Slice Architecture & Windows Build Fix

## Status
Accepted

## Context
We need to implement the M1 frontend slice for the Incident Commander AI dashboard and war room, ensuring that it is:
1. Highly aesthetic and interactive.
2. Robust, degrading gracefully when the API is down.
3. Accessible (non-color cues, keyboard-navigable, screen-reader friendly).
4. Compliant with existing API contracts.
5. Building successfully on Windows environments, which currently crash due to a known `uncaughtException Error: kill EPERM` during the Next.js static page generation/worker teardown phase.

## Decisions
1. **Sleek Vanilla CSS Theme**: Created a unified, high-performance styling layer in `global.css` using modern CSS custom properties (tokens) defining a space-dark palette, responsive flex/grid layouts, accessibility helpers (e.g. `.sr-only`, `.focus-visible`), and rich gradients/transitions.
2. **Interactive Client Routing**: Maintained client-side page state (`useState`, `useEffect`, `useCallback`) in Next.js App Router using `"use client"`. This allows real-time polling (every 5 seconds) inside the incident detail view (the war room), modal interactions, dynamic validation state rendering, and local storage state persistence.
3. **Persisted Filter State**: Filter selections for Service, Severity, and Status are persisted in the browser's `localStorage` and automatically loaded on mount.
4. **Non-Color Status Cues**: Used symbols, bold labels, and unique textual prefixes in status badges and severity tags (e.g. `📥 RECEIVED`, `⚙️ NORMALIZING`, `⏱️ WAITING PATCH APPROVAL`) so that state changes are understandable without color perception.
5. **Windows Production-Build EPERM Patch**:
   - *Problem*: Next.js spawns child workers for static page rendering via `jest-worker`. On Windows, the process manager throws `EPERM` when trying to hard-kill worker processes that might have already exited or are in a locked state. Since this is thrown in a setTimeout inside `jest-worker`, it escapes standard try/catch blocks and crashes the build CLI as an `uncaughtException`.
   - *Solution*: Intercept and monkeypatch `childProcess.ChildProcess.prototype.kill` inside `next.config.js` to catch and ignore `EPERM` or `-4048` errors on Windows. This eliminates the build-killing crash cleanly without altering `node_modules` or compromising build gates.

## Consequences
- The build succeeds with exit code 0 on Windows.
- The user interface is responsive, fully interactive, and conforms strictly to the `@incident-commander/contracts` types.
