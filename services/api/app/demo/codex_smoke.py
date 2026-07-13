"""Bounded live Codex CLI smoke test over the immutable synthetic fixture."""

import argparse
import hashlib
import json
from datetime import UTC, datetime

from app.providers.base import CodeAgentGateway, PatchTaskContext
from app.providers.code_agent import CodexCliGateway
from app.providers.simulated import default_fixtures_root
from app.sandbox.executor import load_base_manifest
from app.sandbox.workspace import SandboxWorkspace, WorkspaceLimits

EXPECTED_FILES = ("src/checkout.test.ts", "src/checkout.ts")


def run_smoke(gateway: CodeAgentGateway) -> dict[str, object]:
    source_dir, manifest = load_base_manifest(default_fixtures_root(), "checkout-api")
    workspace = SandboxWorkspace.create(
        source_dir / "repo",
        manifest.files,
        WorkspaceLimits(
            allowed_write_paths=EXPECTED_FILES,
            max_files_changed=2,
            max_lines_changed=40,
        ),
    )
    try:
        workspace.enable_write()
        gateway.apply_patch_turn(
            workspace,
            PatchTaskContext(
                incident_id="inc-synthetic-codex-smoke",
                service="checkout-api",
                plan_summary="Restore safe optional discount access and add a regression test.",
                steps=(
                    "Replace direct discount access with null-safe optional access.",
                    "Add a regression test for a checkout session without a discount.",
                ),
                files_expected=EXPECTED_FILES,
                max_files_changed=2,
                max_lines_changed=40,
                timeout_seconds=300,
            ),
        )
        diff = workspace.compute_diff()
        workspace.enforce_budget(diff)
        changed_files = tuple(change.path for change in diff.changed)
        passed = (
            changed_files == EXPECTED_FILES
            and "session.discount?.code" in workspace.read_file("src/checkout.ts")
            and "without a discount" in workspace.read_file("src/checkout.test.ts")
        )
        result: dict[str, object] = {
            "passed": passed,
            "checked_at": datetime.now(UTC).isoformat(),
            "synthetic_input": True,
            "external_action_attempted": False,
            "network_access_for_agent_tools": False,
            "engine": gateway.engine_id,
            "simulated": gateway.simulated,
            "base_checksum": workspace.base_checksum,
            "changed_files": list(changed_files),
            "additions": diff.total_additions,
            "deletions": diff.total_deletions,
            "diff_sha256": hashlib.sha256(diff.unified_diff.encode("utf-8")).hexdigest(),
        }
        receipt = getattr(gateway, "last_receipt", None)
        if receipt is not None:
            result["cli_receipt"] = receipt
        return result
    finally:
        workspace.destroy()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--binary", default="codex.cmd")
    args = parser.parse_args()
    result = run_smoke(CodexCliGateway(binary=args.binary, model=args.model))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
