"""Deterministic verification of one captured candidate patch (M6; blueprint
14.2, 17.5, 19.3-19.4, 21).

The verifier never trusts the patching workspace: it materializes a fresh
ephemeral workspace from the immutable fixture base and re-applies the exact
stored unified diff through the same policy-guarded write API the patch turn
used, then proves byte-exact reconstruction against the stored diff hash. If
the tree cannot be reconstructed exactly, nothing runs — a different tree is
never verified.

Checks are the plan's verification commands, authorized three ways before a
process exists: the policy baseline (19.2), the plan's own allowed commands,
and the repository verification manifest (19.3) that pins each command string
to a fixed argv. Execution goes through the strict ``CommandRunner`` (no
shell, env allowlist, cwd confinement, per-command timeout, bounded output)
under a total verification budget. Only deterministic process results mark a
check passed.

Failures are classified with base-state evidence: the failing command is
re-run against a pristine base workspace — if the base also fails, the
failure is pre-existing, not the patch's. Spawn/config problems are
environment issues. Everything else is a patch issue, which is the only
class the bounded repair loop may retry.

Every workspace is destroyed on success and on every failure path, and the
artifact records the proof.
"""

import json
import re
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.domain.contracts import Incident, TimelineEvent
from app.domain.remediation import RemediationPlanArtifact
from app.domain.sandbox import PatchExecutionArtifact
from app.domain.verification import (
    TEST_CATEGORIES,
    CheckCategory,
    VerificationCommandResult,
    VerificationFailureKind,
    VerificationRunArtifact,
    build_verification_artifact,
)
from app.sandbox.command_runner import CommandPolicyError, CommandRunner, CompletedCommand
from app.sandbox.executor import BaseManifest, load_base_manifest
from app.sandbox.workspace import (
    SandboxViolationError,
    SandboxWorkspace,
    WorkspaceLimits,
    content_sha256,
)
from app.store.protocol import StoreProtocol
from app.workflow.policy import command_allowed
from app.workflow.risk import review_patch

VERIFICATION_MANIFEST_FILENAME = "verification_manifest.json"
RUNNER_ID = "deterministic-subprocess-runner"
PER_COMMAND_TIMEOUT_SECONDS = 60.0


class VerificationSetupError(Exception):
    """Verification could not be prepared safely (stale plan, missing or
    invalid verification manifest, unavailable toolchain). Fails closed
    before any workspace exists."""


@dataclass(frozen=True)
class AllowedVerificationCommand:
    """One plan command pinned to a fixed argv by the repository manifest.

    ``argv`` may contain the ``{workspace}`` placeholder, resolved only
    against the ephemeral workspace root at run time."""

    command: str
    category: CheckCategory
    argv: tuple[str, ...]

    def resolve(self, workspace_root: Path) -> tuple[str, ...]:
        return tuple(
            element.replace("{workspace}", str(workspace_root)) for element in self.argv
        )


def load_verification_manifest(
    source_dir: Path, service: str
) -> dict[str, AllowedVerificationCommand]:
    """Load and pin the repository's command map (blueprint 19.3). The
    ``{node}`` and ``{harness}`` placeholders resolve to absolute paths at
    load time so the runner only ever sees pinned executables."""
    manifest_path = source_dir / VERIFICATION_MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise VerificationSetupError(
            f"verification manifest missing for {service} at {manifest_path}; failing closed"
        )
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        harness_rel = raw.get("harness")
        commands = dict(raw["commands"])
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise VerificationSetupError(
            f"verification manifest for {service} is invalid: {exc}"
        ) from exc
    if raw.get("service") != service:
        raise VerificationSetupError(
            f"verification manifest does not describe service {service}"
        )

    node = shutil.which("node")
    harness = (source_dir / harness_rel).resolve() if harness_rel else None
    if harness is not None and not harness.is_file():
        raise VerificationSetupError(f"verification harness missing: {harness}")

    allowed: dict[str, AllowedVerificationCommand] = {}
    for command, spec in commands.items():
        try:
            category = CheckCategory(spec["category"])
            argv_template = list(spec["argv"])
        except (KeyError, TypeError, ValueError) as exc:
            raise VerificationSetupError(
                f"verification manifest entry for {command!r} is invalid: {exc}"
            ) from exc
        argv: list[str] = []
        for element in argv_template:
            if element == "{node}":
                if node is None:
                    raise VerificationSetupError(
                        "node toolchain not available on this host; verification "
                        "cannot run (environment issue)"
                    )
                element = node
            elif element == "{harness}":
                if harness is None:
                    raise VerificationSetupError(
                        f"manifest entry {command!r} references {{harness}} but the "
                        "manifest declares no harness"
                    )
                element = str(harness)
            argv.append(element)
        allowed[command] = AllowedVerificationCommand(
            command=command, category=category, argv=tuple(argv)
        )
    return allowed


# Unified diff application ----------------------------------------------------

_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class DiffApplyError(Exception):
    """The stored diff does not apply cleanly to the immutable base."""


def _split_file_sections(unified_diff: str) -> list[tuple[str, list[str]]]:
    """Split a multi-file unified diff into (path, diff lines) sections."""
    sections: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    path: str | None = None
    for line in unified_diff.splitlines(keepends=True):
        if line.startswith("--- "):
            current = None
            continue
        if line.startswith("+++ "):
            target = line[4:].strip()
            path = target[2:] if target.startswith("b/") else target
            current = []
            sections.append((path, current))
            continue
        if current is not None:
            current.append(line)
    return sections


def _apply_file_diff(base_text: str, diff_lines: list[str], path: str) -> str:
    base_lines = base_text.splitlines(keepends=True)
    out: list[str] = []
    cursor = 0
    for line in diff_lines:
        header = _HUNK_HEADER.match(line)
        if header:
            old_start = int(header.group(1))
            old_len = int(header.group(2) or "1")
            target = old_start - 1 if old_len > 0 else old_start
            if target < cursor or target > len(base_lines):
                raise DiffApplyError(f"hunk out of order in {path}")
            out.extend(base_lines[cursor:target])
            cursor = target
            continue
        if not line:
            continue
        tag, text = line[0], line[1:]
        if tag == " ":
            if cursor >= len(base_lines) or base_lines[cursor] != text:
                raise DiffApplyError(f"context mismatch in {path} at base line {cursor + 1}")
            out.append(text)
            cursor += 1
        elif tag == "-":
            if cursor >= len(base_lines) or base_lines[cursor] != text:
                raise DiffApplyError(f"deletion mismatch in {path} at base line {cursor + 1}")
            cursor += 1
        elif tag == "+":
            out.append(text)
        elif tag == "\\":
            continue  # "\ No newline at end of file"
        else:
            raise DiffApplyError(f"unrecognized diff line in {path}: {line!r}")
    out.extend(base_lines[cursor:])
    return "".join(out)


def apply_stored_diff(workspace: SandboxWorkspace, unified_diff: str) -> None:
    """Apply the exact stored candidate diff through the workspace's guarded
    write API, so path policy and change budgets bind the reconstruction the
    same way they bound the original patch turn."""
    for path, diff_lines in _split_file_sections(unified_diff):
        try:
            base_text = workspace.read_file(path)
        except SandboxViolationError:
            base_text = ""
        workspace.write_file(path, _apply_file_diff(base_text, diff_lines, path))


# Verifier ---------------------------------------------------------------------


@runtime_checkable
class Verifier(Protocol):
    """The single strict verifier contract the pipeline depends on: run one
    deterministic verification of a captured candidate patch and return its
    immutable artifact. ``DeterministicVerifier`` is the production
    implementation; test doubles conform to this same signature so the
    pipeline never special-cases them."""

    def verify(
        self, incident: Incident, execution: PatchExecutionArtifact, patch_id: str, attempt: int
    ) -> VerificationRunArtifact: ...


class DeterministicVerifier:
    def __init__(
        self,
        store: StoreProtocol,
        environ: dict[str, str],
        fixtures_root: Path | None = None,
        clock: Callable[[], datetime] | None = None,
        per_command_timeout_seconds: float = PER_COMMAND_TIMEOUT_SECONDS,
        output_limit_bytes: int = 16_384,
    ) -> None:
        self._store = store
        self._runner = CommandRunner(environ, output_limit_bytes)
        self._fixtures_root = fixtures_root
        self._clock = clock or (lambda: datetime.now(UTC))
        self._per_command_timeout = per_command_timeout_seconds

    # Public API ---------------------------------------------------------------

    def verify(
        self, incident: Incident, execution: PatchExecutionArtifact, patch_id: str, attempt: int
    ) -> VerificationRunArtifact:
        """Run one deterministic verification of the captured candidate diff.

        Setup problems (stale plan, missing manifest, missing toolchain) raise
        ``VerificationSetupError`` before any workspace exists; every later
        outcome is captured as an immutable artifact with the workspace
        provably destroyed."""
        plan = self._store.get_latest_plan_artifact(incident.id)
        if plan is None or plan.artifact_hash != execution.plan_hash:
            raise VerificationSetupError(
                "the incident's current plan does not match the plan the candidate "
                "patch was approved under; refusing to verify a different contract"
            )
        source_dir, base_manifest = load_base_manifest(
            self._fixtures_root, incident.service
        )
        command_map = load_verification_manifest(source_dir, incident.service)

        events: list[tuple[datetime, str]] = []

        def log(detail: str) -> None:
            events.append((self._clock(), detail[:1000]))

        started = time.monotonic()
        budget_seconds = plan.timeout_seconds
        results: list[VerificationCommandResult] = []
        failure_kind: VerificationFailureKind | None = None
        failure_evidence: list[str] = []
        diff_reconstructed = False

        stored_diff_hash = f"sha256:{content_sha256(execution.unified_diff)}"
        if stored_diff_hash != execution.diff_hash:
            failure_kind = VerificationFailureKind.ENVIRONMENT_ISSUE
            failure_evidence.append(
                "stored candidate diff does not match its recorded hash "
                f"({stored_diff_hash} != {execution.diff_hash}); artifact integrity "
                "cannot be trusted"
            )

        authorized, auth_failures = self._authorize_commands(plan, command_map)
        if auth_failures and failure_kind is None:
            failure_kind = VerificationFailureKind.ENVIRONMENT_ISSUE
            failure_evidence.extend(auth_failures)

        relevant_test = self._has_relevant_regression_test(execution, authorized)

        workspace: SandboxWorkspace | None = None
        workspace_id = "unmaterialized"
        try:
            if failure_kind is None:
                workspace = self._materialize(plan, base_manifest, source_dir)
                workspace_id = workspace.workspace_id
                log(f"verification workspace {workspace_id} materialized from "
                    f"{base_manifest.base_ref}")
                try:
                    apply_stored_diff(workspace, execution.unified_diff)
                    recomputed = workspace.compute_diff().unified_diff
                except (DiffApplyError, SandboxViolationError) as exc:
                    failure_kind = VerificationFailureKind.ENVIRONMENT_ISSUE
                    failure_evidence.append(
                        f"stored candidate diff could not be re-applied to the "
                        f"immutable base: {exc}"
                    )
                else:
                    diff_reconstructed = recomputed == execution.unified_diff
                    if not diff_reconstructed:
                        failure_kind = VerificationFailureKind.ENVIRONMENT_ISSUE
                        failure_evidence.append(
                            "re-applied diff is not byte-identical to the stored "
                            "candidate diff; refusing to verify a different tree"
                        )
                    else:
                        log(
                            "candidate diff reconstructed byte-exact "
                            f"({execution.diff_hash})"
                        )

            if failure_kind is None and not relevant_test:
                failure_kind = VerificationFailureKind.PATCH_ISSUE
                failure_evidence.append(
                    "no relevant regression test: the candidate diff must add or "
                    "update a test and the plan must run a test-category check"
                )

            if failure_kind is None and workspace is not None:
                for allowed in authorized:
                    remaining = budget_seconds - (time.monotonic() - started)
                    if remaining <= 0:
                        failure_kind = VerificationFailureKind.ENVIRONMENT_ISSUE
                        failure_evidence.append(
                            f"total verification budget of {budget_seconds}s exhausted "
                            f"after {len(results)} command(s)"
                        )
                        break
                    result = self._run_command(allowed, workspace, remaining, baseline=False)
                    results.append(result)
                    log(
                        f"{allowed.category}: {allowed.command!r} exited "
                        f"{result.exit_code} in {result.duration_ms}ms"
                    )
                    if result.passed:
                        continue
                    failure_kind, evidence = self._classify_failure(
                        allowed,
                        result,
                        plan,
                        base_manifest,
                        source_dir,
                        budget_seconds - (time.monotonic() - started),
                        results,
                    )
                    failure_evidence.extend(evidence)
                    break
        finally:
            # Base-state workspaces are created and destroyed inside
            # _classify_failure; destroy() raises when removal cannot be
            # proven, so no path leaks silently.
            if workspace is not None:
                workspace.destroy()
                log(
                    f"verification workspace {workspace.workspace_id} destroyed "
                    f"(path exists: {workspace.exists()})"
                )

        risk = review_patch(list(execution.changed_files), execution.unified_diff)
        log(
            f"risk review: {risk.risk_level} over {risk.files_changed} file(s), "
            f"{risk.lines_changed} line(s); blocks_pr={risk.blocks_pr}"
        )

        passed = (
            failure_kind is None
            and diff_reconstructed
            and relevant_test
            and bool(results)
            and all(r.passed for r in results if not r.baseline)
        )
        if not passed and failure_kind is None:
            failure_kind = VerificationFailureKind.ENVIRONMENT_ISSUE
            failure_evidence.append("no verification command produced a result")

        destroyed = workspace is None or (workspace.destroyed and not workspace.exists())
        artifact = build_verification_artifact(
            id=self._store.next_id("vrun"),
            incident_id=incident.id,
            patch_id=patch_id,
            patch_execution_id=execution.id,
            plan_id=plan.id,
            plan_hash=plan.artifact_hash,
            attempt=attempt,
            base_ref=base_manifest.base_ref,
            base_checksum=execution.base_checksum,
            diff_hash=execution.diff_hash,
            diff_reconstructed=diff_reconstructed,
            workspace_id=workspace_id,
            runner_id=RUNNER_ID,
            target_simulated=True,
            commands=results,
            relevant_regression_test=relevant_test,
            passed=passed,
            failure_kind=None if passed else failure_kind,
            failure_evidence=[] if passed else failure_evidence,
            risk=risk,
            workspace_destroyed=destroyed,
            total_duration_ms=int((time.monotonic() - started) * 1000),
            budget_seconds=budget_seconds,
            created_at=self._clock(),
        )
        self._store.add_verification_artifact(artifact)
        self._audit_timeline(incident, events, artifact)
        return artifact

    # Internal stages -----------------------------------------------------------

    def _authorize_commands(
        self,
        plan: RemediationPlanArtifact,
        command_map: dict[str, AllowedVerificationCommand],
    ) -> tuple[list[AllowedVerificationCommand], list[str]]:
        """Authorize every plan verification command against the policy
        baseline, the plan's own allowlist, and the repository manifest.
        Unauthorized commands are refused with evidence; no process is ever
        spawned for them."""
        authorized: list[AllowedVerificationCommand] = []
        failures: list[str] = []
        for command in plan.verification_commands:
            if not command_allowed(command):
                failures.append(
                    f"command {command!r} is not in the safe policy baseline; refused"
                )
                continue
            if command not in plan.allowed_commands:
                failures.append(
                    f"command {command!r} is not in the approved plan's allowed "
                    "commands; refused"
                )
                continue
            allowed = command_map.get(command)
            if allowed is None:
                failures.append(
                    f"command {command!r} has no pinned argv in the repository "
                    "verification manifest; refused"
                )
                continue
            authorized.append(allowed)
        if not authorized and not failures:
            failures.append("the plan authorizes no verification commands")
        return authorized, failures

    @staticmethod
    def _has_relevant_regression_test(
        execution: PatchExecutionArtifact,
        authorized: list[AllowedVerificationCommand],
    ) -> bool:
        adds_test = any(
            "test" in change.path.lower() and change.additions > 0
            for change in execution.changed_files
        )
        runs_test = any(a.category in TEST_CATEGORIES for a in authorized)
        return adds_test and runs_test

    def _materialize(
        self,
        plan: RemediationPlanArtifact,
        manifest: BaseManifest,
        source_dir: Path,
    ) -> SandboxWorkspace:
        limits = WorkspaceLimits(
            allowed_write_paths=tuple(sorted(plan.files_expected)),
            max_files_changed=plan.max_files_changed,
            max_lines_changed=plan.max_lines_changed,
        )
        workspace = SandboxWorkspace.create(
            source_dir / "repo", dict(manifest.files), limits
        )
        workspace.enable_write()
        return workspace

    def _run_command(
        self,
        allowed: AllowedVerificationCommand,
        workspace: SandboxWorkspace,
        remaining_budget: float,
        baseline: bool,
    ) -> VerificationCommandResult:
        timeout = min(self._per_command_timeout, remaining_budget)
        argv = allowed.resolve(workspace.root)
        try:
            completed = self._runner.run(argv, workspace.root, timeout)
        except CommandPolicyError as exc:
            completed = CompletedCommand(
                argv=argv,
                exit_code=None,
                duration_ms=0,
                stdout="",
                stderr="",
                stdout_truncated=False,
                stderr_truncated=False,
                timed_out=False,
                spawn_error=f"refused by runner policy: {exc}",
            )
        return VerificationCommandResult(
            command=allowed.command,
            category=allowed.category,
            argv=list(completed.argv),
            baseline=baseline,
            exit_code=completed.exit_code,
            duration_ms=completed.duration_ms,
            stdout=completed.stdout,
            stderr=completed.stderr,
            stdout_truncated=completed.stdout_truncated,
            stderr_truncated=completed.stderr_truncated,
            timed_out=completed.timed_out,
            spawn_error=completed.spawn_error,
        )

    def _classify_failure(
        self,
        allowed: AllowedVerificationCommand,
        result: VerificationCommandResult,
        plan: RemediationPlanArtifact,
        manifest: BaseManifest,
        source_dir: Path,
        remaining_budget: float,
        results: list[VerificationCommandResult],
    ) -> tuple[VerificationFailureKind, list[str]]:
        """Classify one failing check using base-state evidence (19.4): the
        same command runs against a pristine base workspace; a failure there
        is pre-existing, not the patch's."""
        if result.spawn_error is not None:
            return VerificationFailureKind.ENVIRONMENT_ISSUE, [
                f"{allowed.command!r} could not be spawned: {result.spawn_error}"
            ]
        if remaining_budget <= 0:
            return VerificationFailureKind.ENVIRONMENT_ISSUE, [
                f"{allowed.command!r} failed and no budget remains to gather "
                "base-state evidence"
            ]
        base_workspace = self._materialize(plan, manifest, source_dir)
        try:
            base_result = self._run_command(
                allowed, base_workspace, remaining_budget, baseline=True
            )
        finally:
            base_workspace.destroy()
        results.append(base_result)
        detail = "timed out" if result.timed_out else f"exited {result.exit_code}"
        if base_result.spawn_error is not None:
            return VerificationFailureKind.ENVIRONMENT_ISSUE, [
                f"{allowed.command!r} failed on the patched tree ({detail}) and the "
                f"base-state run could not be spawned: {base_result.spawn_error}"
            ]
        if not base_result.passed:
            base_detail = (
                "timed out" if base_result.timed_out else f"exited {base_result.exit_code}"
            )
            return VerificationFailureKind.PRE_EXISTING_FAILURE, [
                f"{allowed.command!r} fails on the pristine base too "
                f"(patched: {detail}; base: {base_detail}); the failure pre-dates "
                "the candidate patch"
            ]
        return VerificationFailureKind.PATCH_ISSUE, [
            f"{allowed.command!r} {detail} on the patched tree but passes on the "
            "pristine base; the candidate patch caused the failure"
        ]

    def _audit_timeline(
        self,
        incident: Incident,
        events: list[tuple[datetime, str]],
        artifact: VerificationRunArtifact,
    ) -> None:
        outcome = (
            "passed"
            if artifact.passed
            else f"failed ({artifact.failure_kind}): " + "; ".join(artifact.failure_evidence)
        )
        entries = [*events, (self._clock(), f"verification {outcome}")]
        for at, detail in entries:
            self._store.add_timeline_event(
                TimelineEvent(
                    id=self._store.next_id("tl"),
                    incident_id=incident.id,
                    at=at,
                    kind="verification_lifecycle",
                    description=f"[deterministic:{RUNNER_ID}] {detail}"[:1000],
                )
            )
