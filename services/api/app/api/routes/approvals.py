"""Approval decision endpoint (blueprint section 17.4).

Server-side checks before any effect: approval exists, is pending, has not
expired, and the artifact version (if supplied) matches. Decisions are
idempotent-hostile by design: a decided approval cannot be decided again.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

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
