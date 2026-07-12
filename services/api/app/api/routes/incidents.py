"""Incident endpoints (blueprint sections 17.1-17.3)."""

import asyncio
import hashlib
import hmac
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_pipeline, get_settings, get_store
from app.config import Settings
from app.demo.seed import seed_demo
from app.domain.contracts import (
    ApprovalRequest,
    EvidenceItem,
    Hypothesis,
    Incident,
    IncidentCreate,
    IncidentList,
    PatchAttempt,
    RemediationPlan,
    ResetResult,
    TimelineEvent,
    VerificationRun,
    WorkflowEvent,
)
from app.domain.enums import Environment, Severity, WorkflowState
from app.domain.investigation import InvestigationReport
from app.domain.remediation import RemediationPlanArtifact
from app.store.protocol import NotFoundError, StoreProtocol
from app.workflow import state_machine
from app.workflow.pipeline import WorkflowPipeline

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


def _get_or_404(store: StoreProtocol, incident_id: str) -> Incident:
    try:
        return store.get_incident(incident_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("", response_model=Incident, status_code=status.HTTP_201_CREATED)
def create_incident(
    body: IncidentCreate,
    store: Annotated[StoreProtocol, Depends(get_store)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Incident:
    now = datetime.now(UTC)
    incident = Incident(
        id=store.next_id("inc"),
        title=body.title,
        service=body.service,
        environment=body.environment,
        severity=body.severity,
        summary=body.summary,
        state=WorkflowState.RECEIVED,
        provider_mode=settings.provider_mode,
        created_at=now,
        updated_at=now,
    )
    store.add_incident(incident)
    store.append_workflow_event(incident.id, None, WorkflowState.RECEIVED, "incident.created")
    return incident


@router.post("/webhook", response_model=Incident, status_code=status.HTTP_201_CREATED)
async def webhook_intake(
    request: Request,
    payload: dict[str, Any],
    store: Annotated[StoreProtocol, Depends(get_store)],
    settings: Annotated[Settings, Depends(get_settings)],
    x_webhook_signature: Annotated[str | None, Header()] = None,
) -> Incident:
    if not settings.demo_mode:
        if not x_webhook_signature:
            raise HTTPException(status_code=401, detail="missing signature")
        body = await request.body()
        expected = hmac.new(b"secret", body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(x_webhook_signature, expected):
            raise HTTPException(status_code=401, detail="invalid signature")

    now = datetime.now(UTC)
    incident = Incident(
        id=store.next_id("inc"),
        title=payload.get("title", "Webhook Incident"),
        service=payload.get("service", "unknown"),
        environment=Environment.PRODUCTION,
        severity=Severity.SEV3,
        summary=payload.get("summary", "Received via webhook"),
        state=WorkflowState.RECEIVED,
        provider_mode=settings.provider_mode,
        created_at=now,
        updated_at=now,
    )
    store.add_incident(incident)
    store.append_workflow_event(incident.id, None, WorkflowState.RECEIVED, "webhook.received")
    return incident


@router.get("", response_model=IncidentList)
def list_incidents(
    store: Annotated[StoreProtocol, Depends(get_store)],
    status_filter: Annotated[WorkflowState | None, Query(alias="status")] = None,
    severity: Severity | None = None,
    service: str | None = None,
    environment: Environment | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> IncidentList:
    items = store.list_incidents(
        status=status_filter,
        severity=severity,
        service=service,
        environment=environment,
        limit=limit,
    )
    return IncidentList(items=items, total=len(items))


@router.get("/{incident_id}", response_model=Incident)
def get_incident(
    incident_id: str, store: Annotated[StoreProtocol, Depends(get_store)]
) -> Incident:
    return _get_or_404(store, incident_id)


@router.post("/{incident_id}/start", response_model=Incident)
def start_incident(
    incident_id: str,
    store: Annotated[StoreProtocol, Depends(get_store)],
    pipeline: Annotated[WorkflowPipeline, Depends(get_pipeline)],
) -> Incident:
    incident = _get_or_404(store, incident_id)
    if incident.state != WorkflowState.RECEIVED:
        raise HTTPException(
            status_code=409,
            detail=f"incident is in state {incident.state}; start requires RECEIVED",
        )
    return pipeline.start(incident)


@router.post("/{incident_id}/cancel", response_model=Incident)
def cancel_incident(
    incident_id: str, store: Annotated[StoreProtocol, Depends(get_store)]
) -> Incident:
    incident = _get_or_404(store, incident_id)
    if state_machine.is_terminal(incident.state):
        raise HTTPException(status_code=409, detail="incident is already terminal")
    new_state = state_machine.advance(incident.state, WorkflowState.CANCELLED)
    updated = store.set_incident_state(incident.id, new_state)
    store.append_workflow_event(incident.id, incident.state, new_state, "incident.cancelled")
    return updated


@router.post("/reset-demo", response_model=ResetResult)
def reset_demo(
    store: Annotated[StoreProtocol, Depends(get_store)],
    settings: Annotated[Settings, Depends(get_settings)],
    x_demo_admin_key: Annotated[str | None, Header()] = None,
) -> ResetResult:
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="reset-demo is demo mode only")
    if x_demo_admin_key != settings.demo_admin_key:
        raise HTTPException(status_code=401, detail="missing or invalid X-Demo-Admin-Key")
    store.reset()
    seeded = seed_demo(store)
    return ResetResult(status="reset", seeded_incident_ids=seeded)


@router.get("/{incident_id}/evidence", response_model=list[EvidenceItem])
def list_evidence(
    incident_id: str, store: Annotated[StoreProtocol, Depends(get_store)]
) -> list[EvidenceItem]:
    _get_or_404(store, incident_id)
    return store.list_evidence(incident_id)


@router.get("/{incident_id}/timeline", response_model=list[TimelineEvent])
def list_timeline(
    incident_id: str, store: Annotated[StoreProtocol, Depends(get_store)]
) -> list[TimelineEvent]:
    _get_or_404(store, incident_id)
    return store.list_timeline(incident_id)


@router.get("/{incident_id}/hypotheses", response_model=list[Hypothesis])
def list_hypotheses(
    incident_id: str, store: Annotated[StoreProtocol, Depends(get_store)]
) -> list[Hypothesis]:
    _get_or_404(store, incident_id)
    return store.list_hypotheses(incident_id)


@router.get("/{incident_id}/investigation", response_model=InvestigationReport)
def get_investigation(
    incident_id: str, store: Annotated[StoreProtocol, Depends(get_store)]
) -> InvestigationReport:
    """Return the latest typed M3 investigation report for the incident.

    404 until the investigation stage has run. The report carries ranked,
    evidence-grounded hypotheses, the code/commit mapping, unknowns, rejected
    claims, and the remediation gate.
    """
    _get_or_404(store, incident_id)
    report = store.get_investigation_report(incident_id)
    if report is None:
        raise HTTPException(
            status_code=404, detail="no investigation report for this incident yet"
        )
    return report


@router.get("/{incident_id}/remediation-plan", response_model=list[RemediationPlan])
def list_plans(
    incident_id: str, store: Annotated[StoreProtocol, Depends(get_store)]
) -> list[RemediationPlan]:
    _get_or_404(store, incident_id)
    return store.list_plans(incident_id)


@router.get("/{incident_id}/remediation-plan/artifact", response_model=RemediationPlanArtifact)
def get_plan_artifact(
    incident_id: str, store: Annotated[StoreProtocol, Depends(get_store)]
) -> RemediationPlanArtifact:
    """Return the latest bounded M4 remediation plan artifact.

    404 until planning has produced a valid bounded plan. The artifact carries
    the expected files, steps, verification commands, budgets, risk, rollback,
    and the content hash approvals bind to. Read-only; M5 owns execution.
    """
    _get_or_404(store, incident_id)
    artifact = store.get_latest_plan_artifact(incident_id)
    if artifact is None:
        raise HTTPException(
            status_code=404, detail="no bounded remediation plan for this incident yet"
        )
    return artifact


@router.get("/{incident_id}/patches", response_model=list[PatchAttempt])
def list_patches(
    incident_id: str, store: Annotated[StoreProtocol, Depends(get_store)]
) -> list[PatchAttempt]:
    _get_or_404(store, incident_id)
    return store.list_patches(incident_id)


@router.get("/{incident_id}/verifications", response_model=list[VerificationRun])
def list_verifications(
    incident_id: str, store: Annotated[StoreProtocol, Depends(get_store)]
) -> list[VerificationRun]:
    _get_or_404(store, incident_id)
    return store.list_verifications(incident_id)


@router.get("/{incident_id}/approvals", response_model=list[ApprovalRequest])
def list_approvals(
    incident_id: str, store: Annotated[StoreProtocol, Depends(get_store)]
) -> list[ApprovalRequest]:
    _get_or_404(store, incident_id)
    return store.list_approvals(incident_id)


@router.get("/{incident_id}/events", response_model=list[WorkflowEvent])
def list_workflow_events(
    incident_id: str, store: Annotated[StoreProtocol, Depends(get_store)]
) -> list[WorkflowEvent]:
    _get_or_404(store, incident_id)
    return store.list_workflow_events(incident_id)


@router.get("/{incident_id}/events/stream")
async def stream_workflow_events(
    request: Request,
    incident_id: str,
    store: Annotated[StoreProtocol, Depends(get_store)],
    once: bool = Query(default=False),
) -> StreamingResponse:
    _get_or_404(store, incident_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        last_seen = 0
        while True:
            if await request.is_disconnected():
                break

            events = store.list_workflow_events(incident_id)
            for event in events[last_seen:]:
                yield f"data: {event.model_dump_json()}\n\n"
            last_seen = len(events)

            if once:
                break

            incident = store.get_incident(incident_id)
            if state_machine.is_terminal(incident.state):
                break

            yield ": ping\n\n"
            await asyncio.sleep(0.1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
