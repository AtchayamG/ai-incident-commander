# ADR 004: Docker Contract

## Status
Accepted

## Context
We need a consistent development and execution environment.

## Decision
We will use Docker and docker-compose as the standard contract for running the stack locally and in demo environments.

## Consequences
- Guaranteed deterministic environment.
- Developers don't need to manually configure local dependencies beyond Docker.
