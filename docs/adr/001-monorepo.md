# ADR 001: Monorepo Structure

## Status
Accepted

## Context
We need a scalable repository structure that can house the backend, frontend, and shared packages for Incident Commander AI.

## Decision
We will use a pnpm workspace to manage the monorepo.

## Consequences
- Single source of truth.
- Simplified dependency management for JS/TS packages.
- Need standard Makefile/scripts to bridge Python and JS ecosystem tasks.
