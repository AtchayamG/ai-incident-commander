"""Redaction boundary.

Every piece of external content (telemetry payloads, logs, webhook bodies)
must pass through ``redact`` before it is persisted or shown to a model or a
user. Raw content never crosses this boundary.
"""

import re
from dataclasses import dataclass, field

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "private_key",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    ),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}\b")),
    ("url_credentials", re.compile(r"(?i)\b([a-z][a-z0-9+.\-]*://)[^\s/:@]+:[^\s/@]+@")),
    (
        "assigned_secret",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|token|password|passwd|credential)"
            r"(\"?\s*[:=]\s*)(\"[^\"]{4,}\"|'[^']{4,}'|[^\s\"',;]{4,})"
        ),
    ),
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
]


@dataclass
class RedactionResult:
    content: str
    applied: bool
    matched_rules: list[str] = field(default_factory=list)


def redact(raw: str) -> RedactionResult:
    """Replace secret-shaped substrings with stable placeholders."""
    content = raw
    matched: list[str] = []
    for name, pattern in _PATTERNS:
        if name == "assigned_secret":
            replaced = pattern.sub(rf"\1\2[REDACTED:{name}]", content)
        elif name == "url_credentials":
            replaced = pattern.sub(rf"\1[REDACTED:{name}]@", content)
        else:
            replaced = pattern.sub(f"[REDACTED:{name}]", content)
        if replaced != content:
            matched.append(name)
            content = replaced
    return RedactionResult(content=content, applied=bool(matched), matched_rules=matched)
