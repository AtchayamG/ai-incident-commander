"""Code-agent gateway adapters (M5).

Two adapters behind the same strict ``CodeAgentGateway`` protocol:

``FixtureCodexGateway``
    Deterministic demo adapter. It writes the golden checkout-api repair
    through the workspace's guarded write API, so read-only mode, path
    policy, and change budgets are enforced on every byte. Its output is a
    fixture and is always labeled ``simulated``; it is never presented as
    live Codex output.

``CodexCliGateway``
    Real adapter for the locally installed OpenAI Codex CLI, following the
    ``codex exec`` non-interactive contract: ``--sandbox workspace-write`` confines writes to the
    workspace, network access stays disabled, the session is ephemeral, and
    the model is configuration-driven. The subprocess environment is built
    from an explicit allowlist so no parent secrets leak. It fails closed —
    a missing binary, model, or credential raises before any workspace
    mutation; nothing is ever faked as a live call.
"""

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

from app.config import Settings
from app.providers.base import PatchTaskContext
from app.sandbox.workspace import SandboxWorkspace

FIXTURE_ENGINE_ID = "fixture-codex"

# The exact defective line in the fixture checkout and its repair. The
# fixture gateway grounds its edit on this content; if the workspace does not
# contain it, the turn fails instead of guessing.
_DEFECT_LINE = "  const code = session.discount.code;"
_REPAIRED_LINE = "  const code = session.discount?.code ?? null;"

# Anchor for inserting the missing regression test at the end of the
# applyDiscount describe block.
_TEST_ANCHOR = """    expect(total).toBe(50);
  });
});
"""
_TEST_INSERTION = """    expect(total).toBe(50);
  });

  it("returns the cart total for a session without a discount", () => {
    const total = applyDiscount({ id: "sess-5", cartTotal: 75 });
    expect(total).toBe(75);
  });
});
"""

_SOURCE_FILE = "src/checkout.ts"
_TEST_FILE = "src/checkout.test.ts"


class CodeAgentUnavailableError(Exception):
    """The configured live code agent cannot run (missing binary, model, or
    credentials). Raised before any workspace mutation; never faked."""


class GatewayTurnError(Exception):
    """A patch turn failed; the workspace may hold partial edits and must be
    destroyed by the executor."""


class FixtureCodexGateway:
    """Deterministic fixture stand-in for the Codex agent (demo mode only).

    Output provenance is explicitly ``simulated``; this adapter never
    performs or claims a live Codex call.
    """

    engine_id = FIXTURE_ENGINE_ID
    simulated = True

    def apply_patch_turn(self, workspace: SandboxWorkspace, task: PatchTaskContext) -> None:
        source = workspace.read_file(_SOURCE_FILE)
        if _DEFECT_LINE not in source:
            raise GatewayTurnError(
                f"fixture gateway cannot ground its edit: defect line missing "
                f"from {_SOURCE_FILE}"
            )
        workspace.write_file(
            _SOURCE_FILE, source.replace(_DEFECT_LINE, _REPAIRED_LINE, 1)
        )

        tests = workspace.read_file(_TEST_FILE)
        if _TEST_ANCHOR not in tests:
            raise GatewayTurnError(
                f"fixture gateway cannot ground its edit: test anchor missing "
                f"from {_TEST_FILE}"
            )
        workspace.write_file(_TEST_FILE, tests.replace(_TEST_ANCHOR, _TEST_INSERTION, 1))


# Environment variables the Codex subprocess may inherit. Everything else —
# API keys, tokens, cloud credentials — is dropped. CODEX_HOME is set
# explicitly from configuration, never inherited implicitly.
CODEX_ENV_ALLOWLIST: tuple[str, ...] = ("PATH", "SYSTEMROOT", "TEMP", "TMP")


class CodexCliGateway:
    """Live adapter for the locally installed OpenAI Codex CLI.

    Drives ``codex exec`` per the installed CLI contract. Model and
    binary come from configuration; there are no defaults that could silently
    select a wrong runtime. Fails closed when unavailable.
    """

    simulated = False

    def __init__(self, binary: str, model: str, codex_home: str | None = None) -> None:
        self._binary = binary
        self._model = model
        self._codex_home = codex_home
        self._last_receipt: dict[str, object] | None = None

    @property
    def engine_id(self) -> str:
        return f"codex-cli:{self._model or 'unconfigured'}"

    @property
    def last_receipt(self) -> dict[str, object] | None:
        """Safe proof of the last successful CLI turn.

        The raw JSON event stream may contain code or prompts, so only its
        digest and event count cross the provider boundary.
        """
        return dict(self._last_receipt) if self._last_receipt is not None else None

    def availability_errors(self) -> list[str]:
        errors: list[str] = []
        if not self._model:
            errors.append("CODEX_MODEL is not configured")
        if not self._binary or shutil.which(self._binary) is None:
            errors.append(f"codex binary not found: {self._binary!r}")
        home = self._resolved_codex_home()
        if home is None or not (home / "auth.json").is_file():
            errors.append("no Codex credentials found (CODEX_HOME/auth.json missing)")
        return errors

    def _resolved_codex_home(self) -> Path | None:
        if self._codex_home:
            return Path(self._codex_home)
        default = Path.home() / ".codex"
        return default if default.is_dir() else None

    def subprocess_env(self) -> dict[str, str]:
        """Explicit-allowlist environment: no parent secrets ever cross into
        the agent subprocess."""
        env = {
            key: value
            for key, value in os.environ.items()
            if key in CODEX_ENV_ALLOWLIST
        }
        home = self._resolved_codex_home()
        if home is not None:
            env["CODEX_HOME"] = str(home)
        return env

    def build_command(self, workspace_root: Path, prompt: str) -> list[str]:
        """``codex exec`` invocation per the installed CLI contract:
        workspace-write sandbox, network disabled, no inherited shell
        environment, ephemeral session, user config ignored. The prompt is
        supplied on stdin because Windows batch shims do not preserve a
        multiline positional argument reliably."""
        del prompt
        return [
            self._binary,
            "exec",
            "--sandbox",
            "workspace-write",
            "-c",
            "sandbox_workspace_write.network_access=false",
            "-c",
            "shell_environment_policy.inherit=none",
            "-c",
            'approval_policy="never"',
            "--cd",
            str(workspace_root),
            "--skip-git-repo-check",
            "--ephemeral",
            "--ignore-user-config",
            "--color",
            "never",
            "--json",
            "-m",
            self._model,
            "-",
        ]

    def build_prompt(self, task: PatchTaskContext) -> str:
        files = ", ".join(task.files_expected)
        steps = "\n".join(f"- {step}" for step in task.steps)
        return (
            f"You are repairing service {task.service} for incident "
            f"{task.incident_id}.\n"
            f"Plan: {task.plan_summary}\n"
            f"Steps:\n{steps}\n"
            f"Edit ONLY these files: {files}.\n"
            f"Change at most {task.max_files_changed} files and "
            f"{task.max_lines_changed} lines in total. Add or update a "
            "regression test. Do not add dependencies, do not access the "
            "network, and do not run destructive commands."
        )

    def apply_patch_turn(self, workspace: SandboxWorkspace, task: PatchTaskContext) -> None:
        self._last_receipt = None
        errors = self.availability_errors()
        if errors:
            raise CodeAgentUnavailableError(
                "live Codex agent unavailable; failing closed: " + "; ".join(errors)
            )
        command = self.build_command(workspace.root, self.build_prompt(task))
        try:
            completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
                command,
                cwd=workspace.root,
                env=self.subprocess_env(),
                input=self.build_prompt(task),
                capture_output=True,
                text=True,
                timeout=task.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise GatewayTurnError(
                f"codex exec exceeded the {task.timeout_seconds}s timeout"
            ) from exc
        except OSError as exc:
            raise CodeAgentUnavailableError(f"codex exec could not start: {exc}") from exc
        if completed.returncode != 0:
            tail = (completed.stderr or completed.stdout or "")[-500:]
            raise GatewayTurnError(
                f"codex exec exited with {completed.returncode}: {tail}"
            )
        event_stream = completed.stdout or ""
        self._last_receipt = {
            "engine": self.engine_id,
            "event_count": sum(1 for line in event_stream.splitlines() if line.strip()),
            "event_stream_sha256": hashlib.sha256(event_stream.encode("utf-8")).hexdigest(),
            "exit_code": completed.returncode,
        }


def build_code_agent_gateway(settings: Settings) -> FixtureCodexGateway | CodexCliGateway:
    """Select the configured gateway. Demo mode binds only the fixture
    adapter; the live adapter is a separate, explicit configuration and is
    never silently substituted."""
    engine = settings.code_agent_engine
    if engine == "fixture":
        return FixtureCodexGateway()
    if engine == "codex-cli":
        if settings.demo_mode:
            raise ValueError(
                "demo mode requires the fixture code agent; refusing to bind codex-cli"
            )
        return CodexCliGateway(
            binary=settings.codex_binary,
            model=settings.codex_model,
            codex_home=settings.codex_home,
        )
    raise ValueError(f"unknown CODE_AGENT_ENGINE: {engine!r}")
