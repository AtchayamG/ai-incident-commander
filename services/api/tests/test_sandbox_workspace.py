"""M5 sandbox workspace and code-agent gateway unit safety tests.

Covers: immutable-base verification on creation, read-only start, path
escape/prohibited/allowlist refusal, deterministic file and line budgets,
diff capture, reset between attempts, provable destruction on demand, and
the Codex CLI adapter's fail-closed availability, sanitized environment, and
sandboxed command contract.
"""

from pathlib import Path

import pytest

from app.config import Settings
from app.providers.base import CodeAgentGateway, PatchTaskContext
from app.providers.code_agent import (
    CodeAgentUnavailableError,
    CodexCliGateway,
    FixtureCodexGateway,
    build_code_agent_gateway,
)
from app.sandbox.workspace import (
    ChangeBudgetError,
    PathPolicyError,
    SandboxWorkspace,
    WorkspaceIntegrityError,
    WorkspaceLimits,
    WorkspaceReadOnlyError,
    content_sha256,
)

BASE_FILES = {
    "src/app.py": "line-1\nline-2\nline-3\n",
    "src/app_test.py": "test-1\n",
}


def _manifest(files: dict[str, str]) -> dict[str, str]:
    return {path: content_sha256(text) for path, text in files.items()}


def _source(tmp_path: Path, files: dict[str, str] | None = None) -> Path:
    root = tmp_path / "source"
    for rel, text in (files or BASE_FILES).items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
    return root


def _limits(**overrides: object) -> WorkspaceLimits:
    fields: dict[str, object] = {
        "allowed_write_paths": ("src/app.py", "src/app_test.py"),
        "max_files_changed": 2,
        "max_lines_changed": 10,
    }
    fields.update(overrides)
    return WorkspaceLimits(**fields)  # type: ignore[arg-type]


def _workspace(tmp_path: Path, **limit_overrides: object) -> SandboxWorkspace:
    return SandboxWorkspace.create(
        _source(tmp_path), _manifest(BASE_FILES), _limits(**limit_overrides)
    )


# --- Creation and immutable base ----------------------------------------------


def test_create_verifies_the_immutable_base(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    try:
        assert workspace.list_files() == ["src/app.py", "src/app_test.py"]
        assert workspace.base_checksum.startswith("sha256:")
        assert not workspace.write_enabled
    finally:
        workspace.destroy()


def test_create_refuses_drifted_source(tmp_path: Path) -> None:
    source = _source(tmp_path)
    (source / "src/app.py").write_text("tampered\n", encoding="utf-8", newline="\n")
    with pytest.raises(WorkspaceIntegrityError, match="drifted"):
        SandboxWorkspace.create(source, _manifest(BASE_FILES), _limits())


def test_create_refuses_unlisted_extra_file(tmp_path: Path) -> None:
    source = _source(tmp_path)
    (source / "src/extra.py").write_text("x\n", encoding="utf-8", newline="\n")
    with pytest.raises(WorkspaceIntegrityError, match="does not match"):
        SandboxWorkspace.create(source, _manifest(BASE_FILES), _limits())


# --- Read-only mode and path policy --------------------------------------------


def test_writes_are_refused_before_write_is_enabled(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    try:
        with pytest.raises(WorkspaceReadOnlyError):
            workspace.write_file("src/app.py", "changed\n")
        assert workspace.read_file("src/app.py") == BASE_FILES["src/app.py"]
    finally:
        workspace.destroy()


def test_path_escapes_are_refused(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.enable_write()
    try:
        for path in ("../evil.py", "..\\evil.py", "/etc/passwd", "C:/evil.py"):
            with pytest.raises(PathPolicyError):
                workspace.write_file(path, "x\n")
        with pytest.raises(PathPolicyError):
            workspace.read_file("../outside.txt")
    finally:
        workspace.destroy()


def test_prohibited_and_unapproved_paths_are_refused(tmp_path: Path) -> None:
    workspace = _workspace(
        tmp_path, allowed_write_paths=("src/app.py", "src/app_test.py", ".env")
    )
    workspace.enable_write()
    try:
        with pytest.raises(PathPolicyError, match="prohibited"):
            workspace.write_file(".env", "SECRET=1\n")
        with pytest.raises(PathPolicyError, match="outside the approved plan"):
            workspace.write_file("src/other.py", "x\n")
    finally:
        workspace.destroy()


# --- Change budgets -------------------------------------------------------------


def test_file_count_budget_is_enforced(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, max_files_changed=1)
    workspace.enable_write()
    try:
        workspace.write_file("src/app.py", "changed\n")
        with pytest.raises(ChangeBudgetError, match="files"):
            workspace.write_file("src/app_test.py", "changed too\n")
    finally:
        workspace.destroy()


def test_line_budget_is_enforced_before_the_write_lands(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, max_lines_changed=2)
    workspace.enable_write()
    try:
        oversized = "".join(f"new-{i}\n" for i in range(10))
        with pytest.raises(ChangeBudgetError, match="lines"):
            workspace.write_file("src/app.py", oversized)
        # The refused write never landed.
        assert workspace.read_file("src/app.py") == BASE_FILES["src/app.py"]
    finally:
        workspace.destroy()


# --- Diff capture and reset -----------------------------------------------------


def test_diff_captures_per_file_additions_and_deletions(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.enable_write()
    try:
        workspace.write_file("src/app.py", "line-1\nline-CHANGED\nline-3\n")
        workspace.write_file("src/app_test.py", "test-1\ntest-2\n")
        diff = workspace.compute_diff()
        by_path = {c.path: c for c in diff.changed}
        assert by_path["src/app.py"].additions == 1
        assert by_path["src/app.py"].deletions == 1
        assert by_path["src/app_test.py"].additions == 1
        assert by_path["src/app_test.py"].deletions == 0
        assert diff.total_lines_changed == 3
        assert "--- a/src/app.py" in diff.unified_diff
        assert "+line-CHANGED" in diff.unified_diff
    finally:
        workspace.destroy()


def test_reset_to_base_restores_the_snapshot(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.enable_write()
    try:
        workspace.write_file("src/app.py", "broken attempt\n")
        workspace.reset_to_base()
        assert workspace.compute_diff().changed == ()
    finally:
        workspace.destroy()


# --- Destruction ----------------------------------------------------------------


def test_destroy_is_proven_and_idempotent(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    root = workspace.root
    workspace.destroy()
    assert workspace.destroyed
    assert not root.exists()
    workspace.destroy()  # idempotent
    with pytest.raises(WorkspaceIntegrityError):
        workspace.read_file("src/app.py")


# --- Code agent gateways ---------------------------------------------------------


def _task() -> PatchTaskContext:
    return PatchTaskContext(
        incident_id="inc-test-0001",
        service="checkout-api",
        plan_summary="test",
        steps=("step",),
        files_expected=("src/app.py",),
        max_files_changed=2,
        max_lines_changed=40,
        timeout_seconds=30,
    )


def test_codex_cli_env_never_leaks_parent_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SUPER_SECRET_TOKEN", "sk-parent-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-parent-openai")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-parent")
    gateway = CodexCliGateway(binary="codex", model="m", codex_home=str(tmp_path))
    env = gateway.subprocess_env()
    assert "SUPER_SECRET_TOKEN" not in env
    assert "OPENAI_API_KEY" not in env
    assert "AWS_SECRET_ACCESS_KEY" not in env
    assert set(env) <= {"PATH", "SYSTEMROOT", "TEMP", "TMP", "CODEX_HOME"}
    assert env["CODEX_HOME"] == str(tmp_path)


def test_codex_cli_command_denies_network_and_confines_writes(tmp_path: Path) -> None:
    gateway = CodexCliGateway(binary="codex", model="test-model", codex_home=str(tmp_path))
    command = gateway.build_command(tmp_path, "prompt")
    assert command[:2] == ["codex", "exec"]
    assert command[2:4] == ["--sandbox", "workspace-write"]
    assert "sandbox_workspace_write.network_access=false" in command
    assert "shell_environment_policy.inherit=none" in command
    assert str(tmp_path) in command
    assert "--skip-git-repo-check" in command
    assert "--ephemeral" in command
    assert "--ignore-user-config" in command
    assert command[command.index("-m") + 1] == "test-model"


def test_codex_cli_fails_closed_without_binary_or_credentials(tmp_path: Path) -> None:
    gateway = CodexCliGateway(
        binary="definitely-not-a-real-binary-xyz", model="", codex_home=str(tmp_path / "none")
    )
    errors = gateway.availability_errors()
    assert any("CODEX_MODEL" in e for e in errors)
    assert any("binary" in e for e in errors)
    assert any("credentials" in e for e in errors)

    workspace = _workspace(tmp_path)
    workspace.enable_write()
    try:
        with pytest.raises(CodeAgentUnavailableError, match="failing closed"):
            gateway.apply_patch_turn(workspace, _task())
        # Nothing was faked and nothing was touched.
        assert workspace.compute_diff().changed == ()
    finally:
        workspace.destroy()


def test_gateway_builder_selects_and_refuses_explicitly() -> None:
    fixture = build_code_agent_gateway(Settings(demo_mode=True))
    assert isinstance(fixture, FixtureCodexGateway)
    assert isinstance(fixture, CodeAgentGateway)
    with pytest.raises(ValueError, match="demo mode requires the fixture"):
        build_code_agent_gateway(Settings(demo_mode=True, code_agent_engine="codex-cli"))
    with pytest.raises(ValueError, match="unknown CODE_AGENT_ENGINE"):
        build_code_agent_gateway(Settings(demo_mode=True, code_agent_engine="mystery"))
