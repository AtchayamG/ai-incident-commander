"""Application settings.

Read from the environment at app creation time (not import time) so tests can
construct apps with explicit settings. Demo mode is the default and requires
no external credentials; live mode is not implemented in M0 and endpoints
that would need it return 501.
"""

import os
from dataclasses import dataclass, field

from app.domain.enums import ProviderMode


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    demo_mode: bool = True
    demo_admin_key: str = "demo-admin-key"
    api_port: int = 8000
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:3000"])
    database_url: str | None = None
    redis_url: str | None = None
    investigation_model: str = "simulated-fixture"
    # M5 code-agent gateway selection. "fixture" is the deterministic,
    # explicitly simulated adapter; "codex-cli" drives the locally installed
    # Codex CLI and fails closed when binary/model/credentials are missing.
    code_agent_engine: str = "fixture"
    codex_model: str = ""
    codex_binary: str = "codex"
    codex_home: str | None = None
    openai_api_key_present: bool = False
    github_token_present: bool = False
    github_token: str = ""
    github_repository: str = ""
    github_head_ref: str = ""
    github_base_ref: str = ""

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.SIMULATED if self.demo_mode else ProviderMode.LIVE

    @classmethod
    def from_env(cls) -> "Settings":
        origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
        return cls(
            demo_mode=_env_bool("DEMO_MODE", True),
            demo_admin_key=os.environ.get("DEMO_ADMIN_KEY", "demo-admin-key"),
            api_port=int(os.environ.get("API_PORT", "8000")),
            cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
            database_url=os.environ.get("DATABASE_URL") or None,
            redis_url=os.environ.get("REDIS_URL") or None,
            investigation_model=os.environ.get("INVESTIGATION_MODEL", "simulated-fixture"),
            code_agent_engine=os.environ.get("CODE_AGENT_ENGINE", "fixture"),
            codex_model=os.environ.get("CODEX_MODEL", ""),
            codex_binary=os.environ.get("CODEX_BINARY", "codex"),
            codex_home=os.environ.get("CODEX_HOME") or None,
            openai_api_key_present=bool(os.environ.get("OPENAI_API_KEY")),
            github_token_present=bool(os.environ.get("GITHUB_TOKEN")),
            github_token=os.environ.get("GITHUB_TOKEN", ""),
            github_repository=os.environ.get("GITHUB_REPOSITORY", ""),
            github_head_ref=os.environ.get("GITHUB_HEAD_REF", ""),
            github_base_ref=os.environ.get("GITHUB_BASE_REF", ""),
        )
