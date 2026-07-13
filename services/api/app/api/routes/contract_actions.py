"""Manual evidence, feedback, and plan-revision API actions."""

import hashlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_store
from app.domain.api_contracts import (
    HypothesisFeedbackCreate,
    HypothesisFeedbackReceipt,
    ManualEvidenceCreate,
    RemediationPlanRevision,
)
from app.domain.contracts import EvidenceItem, TimelineEvent
from app.domain.remediation import RemediationPlanArtifact, build_plan_artifact
from app.security.redaction import redact
from app.store.protocol import NotFoundError, StoreProtocol

router = APIRouter(prefix="/api/v1/incidents", tags=["incident-actions"])


def _require_incident(store: StoreProtocol, incident_id: str) -> None:
    try:
        store.get_incident(incident_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{incident_id}/evidence",
    response_model=EvidenceItem,
    status_code=status.HTTP_201_CREATED,
)
def attach_manual_evidence(
    incident_id: str,
    body: ManualEvidenceCreate,
    store: Annotated[StoreProtocol, Depends(get_store)],
) -> EvidenceItem:
    _require_incident(store, incident_id)
    now = datetime.now(UTC)
    captured_at = body.captured_at
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=UTC)

    content = redact(body.content)
    source = redact(body.source)
    summary = redact(body.summary)
    display_ref = redact(body.display_ref)
    origin = redact(body.origin)
    matched = sorted(
        set(
            content.matched_rules
            + source.matched_rules
            + summary.matched_rules
            + display_ref.matched_rules
            + origin.matched_rules
        )
    )
    digest = hashlib.sha256(content.content.encode("utf-8")).hexdigest()
    item = EvidenceItem(
        id=store.next_id("ev"),
        incident_id=incident_id,
        kind=body.kind,
        provider="manual",
        source=source.content,
        summary=summary.content,
        content=content.content,
        content_hash=f"sha256:{digest}",
        display_ref=display_ref.content,
        redaction_applied=bool(matched),
        redaction_rules=matched,
        provenance={"manual": True, "origin": origin.content, "simulated": False},
        captured_at=captured_at,
        created_at=now,
    )
    store.add_evidence(item)
    store.add_timeline_event(
        TimelineEvent(
            id=store.next_id("tl"),
            incident_id=incident_id,
            at=captured_at,
            kind="manual_evidence_attached",
            description=f"Manual {body.kind.value} evidence attached.",
            evidence_id=item.id,
        )
    )
    return item


@router.post(
    "/{incident_id}/hypotheses/{hypothesis_id}/feedback",
    response_model=HypothesisFeedbackReceipt,
)
def record_hypothesis_feedback(
    incident_id: str,
    hypothesis_id: str,
    body: HypothesisFeedbackCreate,
    store: Annotated[StoreProtocol, Depends(get_store)],
) -> HypothesisFeedbackReceipt:
    _require_incident(store, incident_id)
    hypotheses = store.list_hypotheses(incident_id)
    if not any(item.id == hypothesis_id for item in hypotheses):
        raise HTTPException(status_code=404, detail="hypothesis not found for incident")
    now = datetime.now(UTC)
    safe_reason = redact(body.reason).content
    store.add_timeline_event(
        TimelineEvent(
            id=store.next_id("tl"),
            incident_id=incident_id,
            at=now,
            kind="hypothesis_feedback",
            description=f"Hypothesis {hypothesis_id} marked {body.feedback.value}: {safe_reason}",
        )
    )
    return HypothesisFeedbackReceipt(
        incident_id=incident_id,
        hypothesis_id=hypothesis_id,
        feedback=body.feedback,
        reason=safe_reason,
        recorded_at=now,
    )


@router.post(
    "/{incident_id}/remediation-plan/revise",
    response_model=RemediationPlanArtifact,
)
def revise_remediation_plan(
    incident_id: str,
    body: RemediationPlanRevision,
    store: Annotated[StoreProtocol, Depends(get_store)],
) -> RemediationPlanArtifact:
    _require_incident(store, incident_id)
    current = store.get_latest_plan_artifact(incident_id)
    if current is None:
        raise HTTPException(status_code=404, detail="no bounded remediation plan to revise")

    now = datetime.now(UTC)
    fields = current.model_dump()
    fields.pop("artifact_hash")
    fields.update(
        id=store.next_id("plan"),
        version=current.version + 1,
        created_at=now,
        summary=body.summary or current.summary,
        steps=body.steps or current.steps,
        rollback=body.rollback or current.rollback,
    )
    revised = build_plan_artifact(**fields)
    store.add_plan_artifact(revised)
    safe_reason = redact(body.reason).content
    store.add_timeline_event(
        TimelineEvent(
            id=store.next_id("tl"),
            incident_id=incident_id,
            at=now,
            kind="remediation_plan_revised",
            description=f"Remediation plan revised by operator: {safe_reason}",
        )
    )
    return revised
