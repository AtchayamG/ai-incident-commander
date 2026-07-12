"""Approval decision endpoint (blueprint sections 17.4 and 13).

Server-side checks before any effect: approval exists, is pending, has not
expired, the artifact version (if supplied) matches, the caller's role matches
the binding, and the bound plan artifact is still the incident's latest
(id, version, and content hash) — a regenerated plan makes older approvals
stale. Decisions are idempotent-hostile by design: a decided approval cannot
be decided again, so an approval is single-use. Expiry is persisted when it is
observed.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.deps import get_pipeline, get_store
from app.domain.contracts import ApprovalDecisionIn, ApprovalRequest
from app.domain.enums import ApprovalDecision, ApprovalStatus
from app.store.protocol import NotFoundError, StoreProtocol
from app.workflow.pipeline import WorkflowPipeline

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


@router.post("/{approval_id}/decision", response_model=ApprovalRequest)
def decide(
    approval_id: str,
    body: ApprovalDecisionIn,
    store: Annotated[StoreProtocol, Depends(get_store)],
    pipeline: Annotated[WorkflowPipeline, Depends(get_pipeline)],
    x_approver_role: Annotated[str | None, Header()] = None,
) -> ApprovalRequest:
    try:
        approval = store.get_approval(approval_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    now = datetime.now(UTC)
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=409, detail=f"approval already {approval.status}; cannot decide again"
        )
    expires_at = approval.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if now >= expires_at:
        expired = approval.model_copy(update={"status": ApprovalStatus.EXPIRED})
        store.update_approval(expired)
        raise HTTPException(status_code=409, detail="approval has expired")
    if body.artifact_version is not None and body.artifact_version != approval.artifact_version:
        raise HTTPException(
            status_code=409,
            detail=(
                f"artifact version mismatch: approval is at v{approval.artifact_version},"
                f" decision references v{body.artifact_version}"
            ),
        )

    binding = store.get_approval_binding(approval_id)
    if binding is not None:
        # The demo operator acts in the bound role by default; an explicit
        # header claiming a different role is refused.
        role = x_approver_role or binding.approver_role
        if role != binding.approver_role:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"approval is bound to role {binding.approver_role};"
                    f" decision was made as {role}"
                ),
            )
        latest = store.get_latest_plan_artifact(approval.incident_id)
        if (
            latest is None
            or latest.id != binding.plan_id
            or latest.version != binding.plan_version
            or latest.artifact_hash != binding.plan_hash
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "approval is stale: the bound plan artifact is no longer the"
                    " incident's latest plan"
                ),
            )

    approved = body.decision == ApprovalDecision.APPROVED
    decided = approval.model_copy(
        update={
            "status": ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED,
            "decided_at": now,
            "decision_reason": body.reason,
        }
    )
    store.update_approval(decided)

    incident = store.get_incident(approval.incident_id)
    pipeline.apply_patch_approval(incident, approved=approved)
    return decided
