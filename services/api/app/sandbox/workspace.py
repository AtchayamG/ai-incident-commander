"""Ephemeral isolated workspace for bounded patch execution (blueprint 19.1/19.2).

A ``SandboxWorkspace`` is a throwaway directory materialized from the
deterministic fixture checkout at an immutable, checksum-verified base. It
starts read-only; writes are enabled only after the executor has consumed an
approved single-use APPLY_PATCH action. Every read and write is confined to
the workspace root, writes are further restricted to the plan's expected
files, prohibited paths are refused, and the change budget (file count and
changed-line count) is enforced deterministically at write time and again at
diff capture. The workspace never inherits parent environment or opens the
network — it exposes no command execution at all; M6 owns the verification
runner.

Content is newline-normalized (CRLF -> LF) for hashing and diffing so the
immutable base checksums are identical across host platforms.
"""

import difflib
import hashlib
import os
import shutil
import stat
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.workflow.policy import path_prohibited


class SandboxViolationError(Exception):
    """Base class for policy violations inside the workspace."""


class WorkspaceReadOnlyError(SandboxViolationError):
    """A write was attempted before write mode was enabled."""


class PathPolicyError(SandboxViolationError):
    """A path escaped the workspace root, matched a prohibited pattern, or
    was outside the plan's allowed files."""


class ChangeBudgetError(SandboxViolationError):
    """The change exceeded the plan's file-count or line budget."""


class WorkspaceIntegrityError(Exception):
    """The source did not match the immutable base manifest, or the
    workspace could not be proven destroyed."""


def normalize_text(raw: bytes) -> str:
    return raw.decode("utf-8").replace("\r\n", "\n")


def content_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class WorkspaceLimits:
    """Deterministic write bounds derived from the approved plan artifact."""

    allowed_write_paths: tuple[str, ...]
    max_files_changed: int
    max_lines_changed: int


@dataclass(frozen=True)
class FileChangeStat:
    path: str
    additions: int
    deletions: int
    diff_text: str


@dataclass(frozen=True)
class WorkspaceDiff:
    changed: tuple[FileChangeStat, ...]
    unified_diff: str

    @property
    def total_additions(self) -> int:
        return sum(c.additions for c in self.changed)

    @property
    def total_deletions(self) -> int:
        return sum(c.deletions for c in self.changed)

    @property
    def total_lines_changed(self) -> int:
        return self.total_additions + self.total_deletions


def _file_diff(path: str, base_text: str, new_text: str) -> FileChangeStat:
    base_lines = base_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff_lines = list(
        difflib.unified_diff(base_lines, new_lines, fromfile=f"a/{path}", tofile=f"b/{path}")
    )
    additions = sum(
        1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
    )
    deletions = sum(
        1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
    )
    text = "".join(
        line if line.endswith("\n") else f"{line}\n" for line in diff_lines
    )
    return FileChangeStat(path=path, additions=additions, deletions=deletions, diff_text=text)


class SandboxWorkspace:
    """One ephemeral, policy-bounded copy of the fixture checkout."""

    def __init__(
        self,
        workspace_id: str,
        root: Path,
        base_snapshot: dict[str, str],
        base_checksum: str,
        limits: WorkspaceLimits,
    ) -> None:
        self.workspace_id = workspace_id
        self._root = root
        self._base = base_snapshot
        self.base_checksum = base_checksum
        self._limits = limits
        self._write_enabled = False
        self._destroyed = False

    # Construction ----------------------------------------------------------

    @classmethod
    def create(
        cls,
        source_root: Path,
        manifest_files: dict[str, str],
        limits: WorkspaceLimits,
    ) -> "SandboxWorkspace":
        """Copy the fixture checkout into a fresh temp directory, verifying
        every file against the immutable base manifest. Any drift — a hash
        mismatch, a missing file, or an unlisted extra file — fails closed
        before a workspace exists. The workspace starts read-only."""
        actual = {
            p.relative_to(source_root).as_posix(): normalize_text(p.read_bytes())
            for p in sorted(source_root.rglob("*"))
            if p.is_file()
        }
        if set(actual) != set(manifest_files):
            raise WorkspaceIntegrityError(
                "source checkout does not match the immutable base manifest: "
                f"expected {sorted(manifest_files)}, found {sorted(actual)}"
            )
        for rel, text in actual.items():
            digest = content_sha256(text)
            if digest != manifest_files[rel]:
                raise WorkspaceIntegrityError(
                    f"source file {rel} drifted from the immutable base "
                    f"(sha256 {digest} != {manifest_files[rel]})"
                )

        workspace_id = f"ws-{uuid.uuid4().hex[:12]}"
        root = Path(tempfile.mkdtemp(prefix=f"icx-{workspace_id}-"))
        for rel, text in actual.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
            os.chmod(target, stat.S_IREAD)

        base_checksum = "sha256:" + hashlib.sha256(
            "\n".join(f"{rel} {manifest_files[rel]}" for rel in sorted(manifest_files)).encode(
                "utf-8"
            )
        ).hexdigest()
        return cls(
            workspace_id=workspace_id,
            root=root,
            base_snapshot=actual,
            base_checksum=base_checksum,
            limits=limits,
        )

    # Introspection ---------------------------------------------------------

    @property
    def root(self) -> Path:
        return self._root

    @property
    def write_enabled(self) -> bool:
        return self._write_enabled

    @property
    def destroyed(self) -> bool:
        return self._destroyed

    def exists(self) -> bool:
        return self._root.exists()

    def list_files(self) -> list[str]:
        self._assert_alive()
        return sorted(
            p.relative_to(self._root).as_posix()
            for p in self._root.rglob("*")
            if p.is_file()
        )

    # Guarded IO ------------------------------------------------------------

    def _assert_alive(self) -> None:
        if self._destroyed:
            raise WorkspaceIntegrityError("workspace has been destroyed")

    def _resolve(self, relative: str) -> Path:
        normalized = relative.replace("\\", "/")
        candidate = Path(normalized)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise PathPolicyError(f"path escapes the workspace root: {relative}")
        resolved = (self._root / candidate).resolve()
        root_resolved = self._root.resolve()
        if resolved != root_resolved and root_resolved not in resolved.parents:
            raise PathPolicyError(f"path escapes the workspace root: {relative}")
        return resolved

    def read_file(self, relative: str) -> str:
        self._assert_alive()
        target = self._resolve(relative)
        if not target.is_file():
            raise PathPolicyError(f"not a readable workspace file: {relative}")
        return normalize_text(target.read_bytes())

    def enable_write(self) -> None:
        """Switch to workspace-write mode. The executor calls this only after
        a valid approved single-use action has been consumed."""
        self._assert_alive()
        self._write_enabled = True
        for path in self._root.rglob("*"):
            if path.is_file():
                os.chmod(path, stat.S_IREAD | stat.S_IWRITE)

    def write_file(self, relative: str, content: str) -> None:
        self._assert_alive()
        if not self._write_enabled:
            raise WorkspaceReadOnlyError(
                f"workspace is read-only; write to {relative} refused"
            )
        normalized = relative.replace("\\", "/")
        self._resolve(normalized)
        if path_prohibited(normalized):
            raise PathPolicyError(f"path matches a prohibited pattern: {normalized}")
        if normalized not in self._limits.allowed_write_paths:
            raise PathPolicyError(
                f"path is outside the approved plan's expected files: {normalized}"
            )

        # Prospective budget check: reject before the byte hits disk.
        changed_paths = {c.path for c in self._compute_changes()}
        base_text = self._base.get(normalized, "")
        if content != base_text:
            changed_paths.add(normalized)
        else:
            changed_paths.discard(normalized)
        if len(changed_paths) > self._limits.max_files_changed:
            raise ChangeBudgetError(
                f"change touches {len(changed_paths)} files; budget is "
                f"{self._limits.max_files_changed}"
            )
        prospective = self._compute_changes(override={normalized: content})
        lines = sum(c.additions + c.deletions for c in prospective)
        if lines > self._limits.max_lines_changed:
            raise ChangeBudgetError(
                f"change totals {lines} lines; budget is {self._limits.max_lines_changed}"
            )

        target = self._root / Path(normalized)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")

    def reset_to_base(self) -> None:
        """Restore every file to the immutable base snapshot between repair
        attempts, deleting anything a failed turn added."""
        self._assert_alive()
        if not self._write_enabled:
            raise WorkspaceReadOnlyError("workspace is read-only; reset refused")
        current = self._current_snapshot()
        for path in set(current) - set(self._base):
            (self._root / Path(path)).unlink()
        for path, text in self._base.items():
            if current.get(path) != text:
                target = self._root / Path(path)
                target.write_text(text, encoding="utf-8", newline="\n")

    # Diff capture ----------------------------------------------------------

    def _current_snapshot(self) -> dict[str, str]:
        return {
            p.relative_to(self._root).as_posix(): normalize_text(p.read_bytes())
            for p in sorted(self._root.rglob("*"))
            if p.is_file()
        }

    def _compute_changes(
        self, override: dict[str, str] | None = None
    ) -> list[FileChangeStat]:
        current = self._current_snapshot()
        if override:
            current.update(override)
        stats: list[FileChangeStat] = []
        for path in sorted(set(self._base) | set(current)):
            base_text = self._base.get(path, "")
            new_text = current.get(path, "")
            if base_text == new_text:
                continue
            stats.append(_file_diff(path, base_text, new_text))
        return stats

    def compute_diff(self) -> WorkspaceDiff:
        """Capture the unified diff of the workspace against its immutable
        base, with per-file addition/deletion counts."""
        self._assert_alive()
        changed = tuple(self._compute_changes())
        unified = "".join(c.diff_text for c in changed)
        return WorkspaceDiff(changed=changed, unified_diff=unified)

    def enforce_budget(self, diff: WorkspaceDiff) -> None:
        """Re-check the full change (however it was produced) against the
        plan budget and path policy before anything is persisted."""
        if len(diff.changed) > self._limits.max_files_changed:
            raise ChangeBudgetError(
                f"patch touches {len(diff.changed)} files; budget is "
                f"{self._limits.max_files_changed}"
            )
        if diff.total_lines_changed > self._limits.max_lines_changed:
            raise ChangeBudgetError(
                f"patch changes {diff.total_lines_changed} lines; budget is "
                f"{self._limits.max_lines_changed}"
            )
        for change in diff.changed:
            if path_prohibited(change.path):
                raise PathPolicyError(f"patch touches a prohibited path: {change.path}")
            if change.path not in self._limits.allowed_write_paths:
                raise PathPolicyError(
                    f"patch touches a file outside the approved plan: {change.path}"
                )

    # Destruction -----------------------------------------------------------

    def destroy(self) -> None:
        """Remove the workspace directory and prove it is gone. Idempotent;
        called on success and on every failure path."""
        if self._destroyed and not self._root.exists():
            return

        def _on_error(_func: object, path: str, _exc: object) -> None:
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
            os.unlink(path)

        if self._root.exists():
            shutil.rmtree(self._root, onexc=_on_error)
        if self._root.exists():
            raise WorkspaceIntegrityError(
                f"workspace {self.workspace_id} could not be destroyed at {self._root}"
            )
        self._destroyed = True
