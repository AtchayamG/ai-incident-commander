"""Deterministic remediation policy (blueprint FR-008 and section 19.2).

Pure functions and constants only: no store, no providers, no clock. The
planning manager applies this policy to every planner draft; anything the
policy rejects becomes a NO_SAFE_REMEDIATION refusal, never a weaker plan.
"""

from dataclasses import dataclass
from fnmatch import fnmatch

from app.domain.contracts import Incident
from app.domain.enums import RiskLevel, Severity
from app.domain.remediation import RemediationPlanDraft


@dataclass(frozen=True)
class PolicyLimits:
    """Hard ceilings a plan's own budgets may never exceed."""

    max_files: int = 5
    max_lines: int = 200
    max_attempts: int = 3
    max_timeout_seconds: int = 600


# Paths a remediation plan may never name or touch, matched with fnmatch
# against the repository-relative path. CI/CD, infrastructure, dependency
# lockfiles, and anything secret-shaped are out of bounds for an automated fix.
PROHIBITED_PATH_PATTERNS: tuple[str, ...] = (
    ".github/*",
    ".github/**/*",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "secrets/*",
    "secrets/**/*",
    "infra/*",
    "infra/**/*",
    "deploy/*",
    "deploy/**/*",
    "Dockerfile",
    "docker-compose*",
    "package-lock.json",
    "pnpm-lock.yaml",
)

# Safe command baseline (blueprint section 19.2). A plan's verification and
# allowed commands must all be exact members of this list; there is no shell
# parsing, so pipes, substitutions, and flags outside the baseline never pass.
ALLOWED_COMMAND_BASELINE: frozenset[str] = frozenset(
    {
        "git status",
        "git diff",
        "git log",
        "npm test",
        "npm test -- checkout.test.ts",
        "npm run lint",
        "npm run typecheck",
        "pytest",
        "ruff check",
        "mypy",
    }
)


def path_prohibited(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    return any(fnmatch(normalized, pattern) for pattern in PROHIBITED_PATH_PATTERNS)


def command_allowed(command: str) -> bool:
    return command in ALLOWED_COMMAND_BASELINE


def classify_risk(incident: Incident, draft: RemediationPlanDraft) -> RiskLevel:
    """Deterministic risk from declared change size and incident severity.

    The golden two-file, forty-line guard restoration is LOW. Anything that
    classifies HIGH is refused by the planning manager, never planned.
    """
    if draft.max_files_changed > 4 or draft.max_lines_changed > 150:
        return RiskLevel.HIGH
    if (
        draft.max_files_changed > 2
        or draft.max_lines_changed > 60
        or incident.severity is Severity.SEV1
    ):
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
