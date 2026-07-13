"""Deterministic patch risk review (blueprint 21.3; milestone M6).

Pure functions over the captured diff only: changed paths, change size, and
added content. No model output participates. HIGH risk — authentication,
payments, authorization, database schema/migrations, infrastructure,
cryptography, secrets — blocks real PR readiness by default; the workflow
records the findings as structured evidence instead of proceeding.
"""

import re

from app.domain.enums import RiskLevel
from app.domain.sandbox import FileChange
from app.domain.verification import RiskFinding, RiskReview

# Path segments (directory or file-stem tokens) that mark a change HIGH risk.
HIGH_RISK_SEGMENTS: frozenset[str] = frozenset(
    {
        "auth",
        "authn",
        "authz",
        "authentication",
        "authorization",
        "payment",
        "payments",
        "billing",
        "migration",
        "migrations",
        "infra",
        "infrastructure",
        "terraform",
        "crypto",
        "cryptography",
        "secret",
        "secrets",
    }
)

HIGH_RISK_SUFFIXES: tuple[str, ...] = (".pem", ".key")

# Added-line content that marks a change HIGH risk regardless of path:
# schema DDL and secret-shaped assignments.
HIGH_RISK_CONTENT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "schema_ddl",
        re.compile(r"(?i)\b(alter|drop|create)\s+(table|index|schema|database)\b"),
    ),
    (
        "secret_material",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|token|password|private[_-]?key)\b"
            r"\s*[:=]\s*[\"'][^\"']{4,}[\"']"
        ),
    ),
)

# Size thresholds aligned with the planning policy (policy.classify_risk).
HIGH_MAX_FILES = 4
HIGH_MAX_LINES = 150
MEDIUM_MAX_FILES = 2
MEDIUM_MAX_LINES = 60


def _path_findings(path: str) -> list[RiskFinding]:
    normalized = path.replace("\\", "/").lstrip("/").lower()
    findings: list[RiskFinding] = []
    segments = set(normalized.split("/"))
    stem_tokens = set(re.split(r"[._\-]", normalized.rsplit("/", 1)[-1]))
    hits = (segments | stem_tokens) & HIGH_RISK_SEGMENTS
    for token in sorted(hits):
        findings.append(
            RiskFinding(
                rule="high_risk_path",
                path=path,
                detail=f"path touches a high-risk area ({token})",
                risk_level=RiskLevel.HIGH,
            )
        )
    if normalized.endswith(HIGH_RISK_SUFFIXES) or normalized.startswith(".env"):
        findings.append(
            RiskFinding(
                rule="secret_file",
                path=path,
                detail="path is secret-shaped key material or environment config",
                risk_level=RiskLevel.HIGH,
            )
        )
    return findings


def _content_findings(unified_diff: str) -> list[RiskFinding]:
    findings: list[RiskFinding] = []
    added_lines = [
        line[1:]
        for line in unified_diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    for rule, pattern in HIGH_RISK_CONTENT_RULES:
        for line in added_lines:
            if pattern.search(line):
                findings.append(
                    RiskFinding(
                        rule=rule,
                        path=None,
                        detail=f"added content matches {rule}: {line.strip()[:200]}",
                        risk_level=RiskLevel.HIGH,
                    )
                )
                break  # one finding per rule is enough evidence
    return findings


def review_patch(changed_files: list[FileChange], unified_diff: str) -> RiskReview:
    """Deterministic risk decision over one captured candidate diff."""
    files_changed = len(changed_files)
    lines_changed = sum(c.additions + c.deletions for c in changed_files)

    findings: list[RiskFinding] = []
    for change in changed_files:
        findings.extend(_path_findings(change.path))
    findings.extend(_content_findings(unified_diff))

    if files_changed > HIGH_MAX_FILES or lines_changed > HIGH_MAX_LINES:
        findings.append(
            RiskFinding(
                rule="change_size",
                path=None,
                detail=(
                    f"change of {files_changed} files / {lines_changed} lines exceeds "
                    f"the high-risk threshold ({HIGH_MAX_FILES} files / {HIGH_MAX_LINES} lines)"
                ),
                risk_level=RiskLevel.HIGH,
            )
        )
    elif files_changed > MEDIUM_MAX_FILES or lines_changed > MEDIUM_MAX_LINES:
        findings.append(
            RiskFinding(
                rule="change_size",
                path=None,
                detail=(
                    f"change of {files_changed} files / {lines_changed} lines exceeds "
                    f"the medium threshold ({MEDIUM_MAX_FILES} files / {MEDIUM_MAX_LINES} lines)"
                ),
                risk_level=RiskLevel.MEDIUM,
            )
        )

    if any(f.risk_level is RiskLevel.HIGH for f in findings):
        level = RiskLevel.HIGH
    elif any(f.risk_level is RiskLevel.MEDIUM for f in findings):
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    return RiskReview(
        risk_level=level,
        findings=findings,
        files_changed=files_changed,
        lines_changed=lines_changed,
        blocks_pr=level is RiskLevel.HIGH,
    )
