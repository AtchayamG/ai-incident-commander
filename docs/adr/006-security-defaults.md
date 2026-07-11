# ADR 006: Security Defaults

## Status
Accepted

## Context
The AI will handle sensitive logs, code, and infrastructure states. We need to prevent accidental leakage or unauthorized destructive actions.

## Decision
We will implement explicit redaction boundaries (e.g., PII stripping) and require explicit human-in-the-loop approvals for destructive state changes.

## Consequences
- Improved safety and auditability.
- Added friction in automated workflows requiring approval loops.
