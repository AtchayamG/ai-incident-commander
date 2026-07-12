"""Bounded isolated-workspace patch executor (blueprint 19.1; milestone M5).

The executor owns the deterministic control flow around one patch run:

1. Refuse unless an APPROVED, single-use APPLY_PATCH approval is bound to the
   incident's latest plan artifact (id, version, content hash) and has not
   already been consumed by a previous execution.
2. Verify the source fixture against its pinned immutable base manifest and
   materialize an ephemeral read-only workspace from it.
3. Enable write mode only after the approval is consumed, run the gateway's
   patch turn within the plan's attempt and timeout budgets, and enforce the
   allowed files, prohibited paths, and change budget on the result.
4. Capture the changed files, addition/deletion counts, and unified diff as
   an immutable hashed artifact, then destroy the workspace — on success and
   on every failure path — and prove the source fixture was never mutated.

Every lifecycle stage is persisted on the artifact and mirrored to the
incident timeline for audit, with explicit simulated/live provenance from the
gateway. The executor never runs repository commands; M6 owns verification.
"""

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.domain.contracts import ApprovalRequest, Incident, TimelineEvent
from app.domain.enums import ApprovalStatus, ApprovalType, ProviderMode
from app.domain.remediation import RemediationPlanArtifact
from app.domain.sandbox import (
    FileChange,
    PatchExecutionArtifact,
    PatchExecutionStatus,
    SandboxLifecycleEvent,
    SandboxLifecycleStage,
    build_patch_execution_artifact,
)
from app.providers.base import CodeAgentGateway, PatchTaskContext
from app.providers.code_agent import CodeAgentUnavailableError, GatewayTurnError
from app.providers.simulated import default_fixtures_root
from app.sandbox.workspace import (
    SandboxViolationError,
    SandboxWorkspace,
    WorkspaceDiff,
    WorkspaceIntegrityError,
    WorkspaceLimits,
    content_sha256,
    normalize_text,
)
from app.store.protocol import StoreProtocol

MANIFEST_FILENAME = "base_manifest.json"


class ApprovalRequiredError(Exception):
    """Raised when a patch is attempted without a valid, bound approval."""


class ApprovalConsumedError(ApprovalRequiredError):
    """The bound approval was already consumed by a previous execution;
    approvals authorize exactly one workspace mutation."""


class SandboxSetupError(Exception):
    """The sandbox could not be prepared safely (missing or drifted immutable
    base manifest, or a plan that violates sandbox policy). Fails closed
    before any workspace exists."""


@dataclass(frozen=True)
class BaseManifest:
    """Pinned immutable base of the fixture checkout."""

    service: str
    base_ref: str
    files: dict[str, str]


class SandboxPatchExecutor:
    def __init__(
        self,
        store: StoreProtocol,
        gateway: CodeAgentGateway,
        fixtures_root: Path | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._gateway = gateway
        self._fixtures_root = fixtures_root
        self._clock = clock or (lambda: datetime.now(UTC))

    # Public API -------------------------------------------------------------

    def execute(self, incident: Incident) -> PatchExecutionArtifact:
        """Run one bounded patch execution for the incident's latest approved
        plan. Authorization failures raise before any workspace exists; every
        later failure is captured as a FAILED artifact with the workspace
        provably destroyed."""
        plan = self._store.get_latest_plan_artifact(incident.id)
        if plan is None:
            raise ApprovalRequiredError(
                "no bounded remediation plan exists for this incident"
            )
        approval = self._authorizing_approval(incident, plan)
        for previous in self._store.list_patch_executions(incident.id):
            if previous.approval_id == approval.id:
                raise ApprovalConsumedError(
                    f"approval {approval.id} was already consumed by execution "
                    f"{previous.id}; a new approval is required"
                )
        if plan.network_allowed:
            raise SandboxSetupError(
                "plan requests network access; sandbox policy denies network"
            )

        source_dir, manifest = self._load_manifest(incident.service)
        repo_root = source_dir / "repo"
        pre_hashes = self._source_hashes(repo_root)
        self._verify_against_manifest(pre_hashes, manifest)

        events: list[SandboxLifecycleEvent] = []

        def log(stage: SandboxLifecycleStage, detail: str) -> None:
            events.append(
                SandboxLifecycleEvent(at=self._clock(), stage=stage, detail=detail[:1000])
            )

        limits = WorkspaceLimits(
            allowed_write_paths=tuple(sorted(plan.files_expected)),
            max_files_changed=plan.max_files_changed,
            max_lines_changed=plan.max_lines_changed,
        )
        workspace = SandboxWorkspace.create(repo_root, dict(manifest.files), limits)
        log(
            SandboxLifecycleStage.WORKSPACE_CREATED,
            f"ephemeral workspace {workspace.workspace_id} created from "
            f"{manifest.base_ref}",
        )
        log(
            SandboxLifecycleStage.BASE_VERIFIED,
            f"immutable base verified: {workspace.base_checksum}",
        )
        log(SandboxLifecycleStage.READ_ONLY, "workspace opened in read-only mode")

        status = PatchExecutionStatus.FAILED
        failure_reasons: list[str] = []
        diff = WorkspaceDiff(changed=(), unified_diff="")
        attempts_used = 0
        try:
            log(
                SandboxLifecycleStage.APPROVAL_CONSUMED,
                f"single-use approval {approval.id} consumed for plan {plan.id} "
                f"v{plan.version}",
            )
            workspace.enable_write()
            log(
                SandboxLifecycleStage.WRITE_ENABLED,
                "workspace-write mode enabled after approval consumption",
            )

            task = PatchTaskContext(
                incident_id=incident.id,
                service=incident.service,
                plan_summary=plan.summary,
                steps=tuple(plan.steps),
                files_expected=tuple(sorted(plan.files_expected)),
                max_files_changed=plan.max_files_changed,
                max_lines_changed=plan.max_lines_changed,
                timeout_seconds=plan.timeout_seconds,
            )
            attempts_used, turn_error = self._run_attempts(workspace, task, plan, log)
            if turn_error is not None:
                raise turn_error

            diff = workspace.compute_diff()
            if not diff.changed:
                raise GatewayTurnError("patch turn produced no changes")
            workspace.enforce_budget(diff)
            if not any("test" in c.path.lower() and c.additions > 0 for c in diff.changed):
                raise SandboxViolationError(
                    "patch does not add or update a regression test"
                )
            log(
                SandboxLifecycleStage.PATCH_APPLIED,
                f"patch applied to {len(diff.changed)} file(s) within budget",
            )
            log(
                SandboxLifecycleStage.DIFF_CAPTURED,
                f"diff captured: {len(diff.changed)} file(s), "
                f"+{diff.total_additions}/-{diff.total_deletions} lines",
            )
            status = PatchExecutionStatus.SUCCEEDED
        except SandboxViolationError as exc:
            failure_reasons.append(str(exc))
            log(SandboxLifecycleStage.POLICY_VIOLATION, str(exc))
            diff = self._best_effort_diff(workspace)
        except (GatewayTurnError, CodeAgentUnavailableError) as exc:
            failure_reasons.append(str(exc))
            log(SandboxLifecycleStage.PATCH_TURN_FAILED, str(exc))
            diff = self._best_effort_diff(workspace)
        finally:
            workspace.destroy()
            log(
                SandboxLifecycleStage.WORKSPACE_DESTROYED,
                f"workspace {workspace.workspace_id} destroyed "
                f"(path exists: {workspace.exists()})",
            )

        post_hashes = self._source_hashes(repo_root)
        source_intact = post_hashes == pre_hashes == manifest.files
        log(
            SandboxLifecycleStage.SOURCE_VERIFIED,
            "source fixture verified unmutated after run"
            if source_intact
            else "SOURCE FIXTURE MUTATED — investigate immediately",
        )
        if status is PatchExecutionStatus.SUCCEEDED and not source_intact:
            status = PatchExecutionStatus.FAILED
            failure_reasons.append("source fixture was mutated during the run")

        provider_mode = (
            ProviderMode.SIMULATED if self._gateway.simulated else ProviderMode.LIVE
        )
        artifact = build_patch_execution_artifact(
            id=self._store.next_id("pexec"),
            incident_id=incident.id,
            plan_id=plan.id,
            plan_version=plan.version,
            plan_hash=plan.artifact_hash,
            approval_id=approval.id,
            engine_id=self._gateway.engine_id,
            simulated=self._gateway.simulated,
            provider_mode=provider_mode,
            workspace_id=workspace.workspace_id,
            base_ref=manifest.base_ref,
            base_checksum=workspace.base_checksum,
            status=status,
            changed_files=[
                FileChange(path=c.path, additions=c.additions, deletions=c.deletions)
                for c in diff.changed
            ],
            total_additions=diff.total_additions,
            total_deletions=diff.total_deletions,
            unified_diff=diff.unified_diff,
            diff_hash=f"sha256:{content_sha256(diff.unified_diff)}",
            attempts_used=attempts_used,
            max_attempts=plan.max_attempts,
            failure_reasons=failure_reasons,
            workspace_destroyed=workspace.destroyed and not workspace.exists(),
            source_fixture_intact=source_intact,
            lifecycle=events,
            created_at=self._clock(),
        )
        self._store.add_patch_execution(artifact)
        self._audit_timeline(incident, artifact)
        return artifact

    # Internal stages ---------------------------------------------------------

    def _run_attempts(
        self,
        workspace: SandboxWorkspace,
        task: PatchTaskContext,
        plan: RemediationPlanArtifact,
        log: Callable[[SandboxLifecycleStage, str], None],
    ) -> tuple[int, GatewayTurnError | None]:
        """Run gateway patch turns within the plan's attempt and timeout
        budgets. Returns (attempts used, error); the error is the final turn
        failure once the budget is exhausted, so attempts stay auditable on
        failure paths."""
        started = time.monotonic()
        last_error: GatewayTurnError | None = None
        attempts_used = 0
        for attempt in range(1, plan.max_attempts + 1):
            if time.monotonic() - started >= plan.timeout_seconds:
                return attempts_used, GatewayTurnError(
                    f"timeout budget of {plan.timeout_seconds}s exhausted after "
                    f"{attempts_used} attempt(s)"
                )
            log(
                SandboxLifecycleStage.PATCH_TURN_STARTED,
                f"attempt {attempt}/{plan.max_attempts} via {self._gateway.engine_id}",
            )
            attempts_used = attempt
            try:
                self._gateway.apply_patch_turn(workspace, task)
                return attempts_used, None
            except GatewayTurnError as exc:
                last_error = exc
                log(
                    SandboxLifecycleStage.PATCH_TURN_FAILED,
                    f"attempt {attempt} failed: {exc}",
                )
                if attempt < plan.max_attempts:
                    workspace.reset_to_base()
        return attempts_used, GatewayTurnError(
            f"attempt budget of {plan.max_attempts} exhausted: {last_error}"
        )

    def _authorizing_approval(
        self, incident: Incident, plan: RemediationPlanArtifact
    ) -> ApprovalRequest:
        for approval in self._store.list_approvals(incident.id):
            if (
                approval.approval_type is not ApprovalType.APPLY_PATCH
                or approval.status is not ApprovalStatus.APPROVED
            ):
                continue
            binding = self._store.get_approval_binding(approval.id)
            if (
                binding is not None
                and binding.plan_id == plan.id
                and binding.plan_version == plan.version
                and binding.plan_hash == plan.artifact_hash
            ):
                return approval
        raise ApprovalRequiredError(
            "no approved APPLY_PATCH approval is bound to the current plan artifact"
        )

    def _load_manifest(self, service: str) -> tuple[Path, BaseManifest]:
        source_dir = (self._fixtures_root or default_fixtures_root()) / service
        manifest_path = source_dir / MANIFEST_FILENAME
        if not manifest_path.is_file():
            raise SandboxSetupError(
                f"immutable base manifest missing for {service} at {manifest_path}; "
                "failing closed"
            )
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = BaseManifest(
                service=raw["service"],
                base_ref=raw["base_ref"],
                files=dict(raw["files"]),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise SandboxSetupError(
                f"immutable base manifest for {service} is invalid: {exc}"
            ) from exc
        if manifest.service != service or not manifest.files:
            raise SandboxSetupError(
                f"immutable base manifest does not describe service {service}"
            )
        return source_dir, manifest

    @staticmethod
    def _source_hashes(repo_root: Path) -> dict[str, str]:
        return {
            p.relative_to(repo_root).as_posix(): content_sha256(normalize_text(p.read_bytes()))
            for p in sorted(repo_root.rglob("*"))
            if p.is_file()
        }

    @staticmethod
    def _verify_against_manifest(hashes: dict[str, str], manifest: BaseManifest) -> None:
        if hashes != manifest.files:
            raise SandboxSetupError(
                f"source fixture for {manifest.service} drifted from the immutable "
                "base manifest; failing closed"
            )

    @staticmethod
    def _best_effort_diff(workspace: SandboxWorkspace) -> WorkspaceDiff:
        """Capture whatever partial change exists for audit on failure paths;
        an unreadable workspace yields an empty diff, never a crash."""
        try:
            return workspace.compute_diff()
        except (WorkspaceIntegrityError, OSError):
            return WorkspaceDiff(changed=(), unified_diff="")

    def _audit_timeline(self, incident: Incident, artifact: PatchExecutionArtifact) -> None:
        provenance = "simulated" if artifact.simulated else "live"
        for event in artifact.lifecycle:
            self._store.add_timeline_event(
                TimelineEvent(
                    id=self._store.next_id("tl"),
                    incident_id=incident.id,
                    at=event.at,
                    kind="sandbox_lifecycle",
                    description=(
                        f"[{provenance}:{artifact.engine_id}] {event.stage}: {event.detail}"
                    )[:1000],
                )
            )


def compute_repo_manifest_hash(files: dict[str, str]) -> str:
    """Combined checksum over a manifest's per-file hashes (stable ordering)."""
    body = "\n".join(f"{rel} {digest}" for rel, digest in sorted(files.items()))
    return f"sha256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}"
