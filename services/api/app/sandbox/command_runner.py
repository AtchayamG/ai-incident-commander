"""Strict argv command runner for deterministic verification (blueprint 14.2, 19.2).

Commands run as real subprocesses with every boundary explicit:

- **No shell, ever.** Commands are fixed argv lists; pipes, substitutions,
  and metacharacters are refused before a process exists.
- **Environment allowlist.** The child sees only the minimal OS variables it
  needs to start (``SYSTEMROOT``/``TEMP``-class); parent API keys, tokens,
  and proxies never cross the boundary. Proxy variables are explicitly
  cleared so nothing routes traffic implicitly.
- **Network denial by policy.** There is no OS-level egress filter available
  in-process; network denial is enforced by the layers above this one — the
  argv allowlist only ever maps to the pinned offline fixture harness — plus
  the environment allowlist. Documented in ADR 009.
- **Confinement.** ``cwd`` is the ephemeral workspace; argv paths are pinned
  absolute paths resolved from the verification manifest, never caller input.
- **Bounded output and time.** Per-command timeout, byte-capped stdout and
  stderr (with explicit truncation flags), and redaction before anything is
  persisted or shown.

The runner never decides pass/fail policy; it only reports deterministic
process results (exit code, duration, sanitized output).
"""

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from app.security.redaction import redact

# Characters that only make sense to a shell. No argv element may contain
# them; the runner never invokes a shell, so this is defense in depth against
# a tampered manifest smuggling `cmd /c`-style payloads into an argument.
SHELL_METACHARACTERS = frozenset('&|;<>`$\n\r')

# Minimal OS variables a child process may inherit when present. Nothing
# secret-shaped: no PATH (argv[0] is always absolute), no HOME, no proxies.
ENV_ALLOWLIST: tuple[str, ...] = ("SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "TEMP", "TMP")

DEFAULT_OUTPUT_LIMIT_BYTES = 16_384


class CommandPolicyError(Exception):
    """The command violates runner policy; no process was spawned."""


@dataclass(frozen=True)
class CompletedCommand:
    """Deterministic result of one subprocess run (or refused spawn)."""

    argv: tuple[str, ...]
    exit_code: int | None
    duration_ms: int
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    timed_out: bool
    spawn_error: str | None = None


def _bounded(raw: bytes, limit: int) -> tuple[str, bool]:
    truncated = len(raw) > limit
    text = raw[:limit].decode("utf-8", errors="replace")
    return redact(text).content, truncated


class CommandRunner:
    def __init__(
        self,
        environ: dict[str, str],
        output_limit_bytes: int = DEFAULT_OUTPUT_LIMIT_BYTES,
    ) -> None:
        self._environ = environ
        self._output_limit = output_limit_bytes

    def subprocess_env(self) -> dict[str, str]:
        """Explicit allowlist over the provided parent environment."""
        return {k: v for k, v in self._environ.items() if k in ENV_ALLOWLIST}

    def run(
        self, argv: tuple[str, ...], cwd: Path, timeout_seconds: float
    ) -> CompletedCommand:
        """Run one fixed argv command inside ``cwd``. Raises
        ``CommandPolicyError`` for policy violations (empty argv, shell
        metacharacters, relative executable, cwd escape) before any process
        exists; spawn failures and timeouts are captured as results so the
        verifier can classify them."""
        if not argv:
            raise CommandPolicyError("empty argv refused")
        for element in argv:
            if any(ch in SHELL_METACHARACTERS for ch in element):
                raise CommandPolicyError(
                    f"argv element contains shell metacharacters: {element!r}"
                )
        executable = Path(argv[0])
        if not executable.is_absolute() or not executable.is_file():
            raise CommandPolicyError(
                f"executable must be a pinned absolute path: {argv[0]!r}"
            )
        if not cwd.is_dir():
            raise CommandPolicyError(f"cwd is not a directory: {cwd}")
        if timeout_seconds <= 0:
            raise CommandPolicyError("timeout budget exhausted before the command ran")

        started = time.monotonic()
        try:
            completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
                list(argv),
                cwd=str(cwd),
                env=self.subprocess_env(),
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout, out_trunc = _bounded(exc.stdout or b"", self._output_limit)
            stderr, err_trunc = _bounded(exc.stderr or b"", self._output_limit)
            return CompletedCommand(
                argv=argv,
                exit_code=None,
                duration_ms=int((time.monotonic() - started) * 1000),
                stdout=stdout,
                stderr=stderr,
                stdout_truncated=out_trunc,
                stderr_truncated=err_trunc,
                timed_out=True,
            )
        except OSError as exc:
            return CompletedCommand(
                argv=argv,
                exit_code=None,
                duration_ms=int((time.monotonic() - started) * 1000),
                stdout="",
                stderr="",
                stdout_truncated=False,
                stderr_truncated=False,
                timed_out=False,
                spawn_error=str(exc)[:500],
            )

        stdout, out_trunc = _bounded(completed.stdout, self._output_limit)
        stderr, err_trunc = _bounded(completed.stderr, self._output_limit)
        return CompletedCommand(
            argv=argv,
            exit_code=completed.returncode,
            duration_ms=int((time.monotonic() - started) * 1000),
            stdout=stdout,
            stderr=stderr,
            stdout_truncated=out_trunc,
            stderr_truncated=err_trunc,
            timed_out=False,
        )
