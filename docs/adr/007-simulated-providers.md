# ADR 007: Simulated Providers

## Status
Accepted

## Context
During local testing and demo mode, we need to interact with external systems (PagerDuty, AWS, GitHub) without real network calls.

## Decision
We will define strict interface contracts for all providers and implement simulated/mock providers that implement these interfaces.

## Consequences
- Decouples core logic from external API availability.
- Easy to swap in real providers for production.
