# ADR 005: Demo Mode

## Status
Accepted

## Context
Reviewers and users need to run the application easily without configuring API keys or external services initially.

## Decision
We will implement a `DEMO_MODE` environment variable. When true, the system will use mocked data and simulated responses without requiring any external credentials.

## Consequences
- Instant onboarding for reviewers.
- Requires maintaining mock implementations for external services.
