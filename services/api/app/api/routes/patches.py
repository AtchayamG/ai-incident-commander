"""Patch diff, verification, and bounded retry endpoints."""

import hashlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_pipeline, get_store
from app.domain.api_contracts import PatchDiffResponse, PatchRetryRequest, PatchRetryResponse
from app.domain.contracts import PatchAttempt, TimelineEvent
from app.domain.verification import VerificationRunArtifact
from app.security.redaction import redact
from app.store.protocol import NotFoundError, StoreProtocol
from app.workflow.pipeline import PatchRetryRefusedError, WorkflowPipeline

router = APIRouter(prefix="/api/v1/patches", tags=["patches"])


def _get_patch(store: StoreProtocol, patch_id: str) -> PatchAttempt:
    try:
        return store.get_patch(patch_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{patch_id}/diff", response_model=PatchDiffResponse)
def get_patch_diff(
    patch_id: str, store: Annotated[StoreProtocol, Depends(get_store)]
) -> PatchDiffResponse:
    patch = _get_patch(store, patch_id)
    digest = hashlib.sha256(patch.diff.encode("utf-8")).hexdigest()
    return PatchDiffResponse(
        patch_id=patch.id,
        incident_id=patch.incident_id,
        attempt=patch.attempt,
        unified_diff=patch.diff,
        diff_hash=f"sha256:{digest}",
        files_changed=patch.files_changed,
        lines_changed=patch.lines_changed,
    )


@router.get("/{patch_id}/verification", response_model=VerificationRunArtifact)
def get_patch_verification(
    patch_id: str, store: Annotated[StoreProtocol, Depends(get_store)]
) -> VerificationRunArtifact:
    _get_patch(store, patch_id)
    artifact = store.get_verification_artifact_for_patch(patch_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="no verification found for patch")
    return artifact


@router.post("/{patch_id}/retry", response_model=PatchRetryResponse)
def retry_patch(
    patch_id: str,
    body: PatchRetryRequest,
    store: Annotated[StoreProtocol, Depends(get_store)],
    pipeline: Annotated[WorkflowPipeline, Depends(get_pipeline)],
) -> PatchRetryResponse:
    patch = _get_patch(store, patch_id)
    incident = store.get_incident(patch.incident_id)
    plan = store.get_latest_plan_artifact(incident.id)
    if plan is None:
        raise HTTPException(status_code=409, detail="no current bounded plan")
    attempts_used = len(store.list_patches(incident.id))
    try:
        updated = pipeline.request_patch_retry(incident, patch)
    except PatchRetryRefusedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    safe_reason = redact(body.reason).content
    store.add_timeline_event(
        TimelineEvent(
            id=store.next_id("tl"),
            incident_id=incident.id,
            at=datetime.now(UTC),
            kind="patch_retry_requested",
            description=f"Patch retry requested: {safe_reason}",
        )
    )
    return PatchRetryResponse(
        patch_id=patch.id,
        incident_id=incident.id,
        accepted=True,
        state=updated.state,
        attempts_used=attempts_used,
        max_attempts=plan.max_attempts,
        attempts_remaining=plan.max_attempts - attempts_used,
    )
