# ADR 002: Backend Framework

## Status
Accepted

## Context
We need a performant, typed, and modern backend for orchestrating agent workflows and APIs.

## Decision
We will use Python 3.12, FastAPI, and Pydantic v2.

## Consequences
- Strong typing and automatic OpenAPI validation.
- Fast async support for parallel agent tasks.
