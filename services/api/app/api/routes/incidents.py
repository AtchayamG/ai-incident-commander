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
    CommunicationUpdate,
    DraftPR,
    EvidenceItem,
    ExternalAction,
    Hypothesis,
    Incident,
    IncidentCreate,
    IncidentList,
    PatchAttempt,
    Postmortem,
    RemediationPlan,
    ResetResult,
    TimelineEvent,
    VerificationRun,
    WorkflowEvent,
)
from app.domain.enums import ApprovalStatus, ApprovalType, Environment, Severity, WorkflowState
from app.domain.investigation import InvestigationReport
from app.domain.remediation import RemediationPlanArtifact
from app.domain.sandbox import PatchExecutionArtifact
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


@router.get(
    "/{incident_id}/patch-executions", response_model=list[PatchExecutionArtifact]
)
def list_patch_executions(
    incident_id: str, store: Annotated[StoreProtocol, Depends(get_store)]
) -> list[PatchExecutionArtifact]:
    """Immutable M5 isolated-workspace execution records: consumed approval,
    engine provenance (simulated/live), captured diff and per-file change
    counts, lifecycle audit, and workspace destruction / source immutability
    proof. Read-only."""
    _get_or_404(store, incident_id)
    return store.list_patch_executions(incident_id)


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


def _map_to_draft_pr(action: ExternalAction, incident: Incident) -> DraftPR:
    url = None
    reference = None
    error_message = None
    if action.provider_receipt_json:
        url = action.provider_receipt_json.get("url")
        reference = action.provider_receipt_json.get("reference") or url
        error_message = action.provider_receipt_json.get("error")
    return DraftPR(
        id=action.id,
        incident_id=action.incident_id,
        status=action.status,
        url=url,
        reference=reference,
        provider_mode=incident.provider_mode,
        idempotency_key=action.idempotency_key,
        error_message=error_message,
        created_at=action.created_at,
    )


def _generate_comms(store: StoreProtocol, incident: Incident) -> CommunicationUpdate:
    hypotheses = store.list_hypotheses(incident.id)
    patches = store.list_patches(incident.id)
    verifications = store.list_verifications(incident.id)
    actions = store.list_external_actions(incident.id)

    latest_patch = patches[-1] if patches else None
    verifications[-1] if verifications else None
    top_hyp = hypotheses[0] if hypotheses else None

    pr_url = "N/A"
    if actions:
        for act in reversed(actions):
            if act.provider_receipt_json and "url" in act.provider_receipt_json:
                pr_url = act.provider_receipt_json["url"]
                break

    # Avoid claiming successfully mitigated/closed/live/deployed when evidence
    # only proves a verified patch and draft-PR artifact.
    tech_lines = [
        f"Incident ID: {incident.id} - Resolution draft created.",
        f"Service: {incident.service} ({incident.environment.value}) | "
        f"Severity: {incident.severity.value}",
        f"Root Cause: {top_hyp.statement if top_hyp else 'Unknown'}",
        "Remediation: Prepared verified patch (attempt "
        f"{latest_patch.attempt if latest_patch else 1}).",
        f"Draft-PR artifact: recorded at {pr_url}."
    ]
    tech_update = "\n".join(tech_lines)

    stakeholder_lines = [
        f"A verified code patch has been prepared for {incident.service} "
        f"in {incident.environment.value}.",
        f"A draft-PR artifact is pending review: {pr_url}",
        "Full postmortem and follow-up action items have been drafted "
        "and are awaiting sign-off."
    ]
    stakeholder_update = "\n".join(stakeholder_lines)

    resolution_lines = [
        f"Draft-PR artifact {pr_url} recorded with verified patch (attempt "
        f"{latest_patch.attempt if latest_patch else 1}).",
        "Verification checks successfully executed. Awaiting command review "
        "and production deployment."
    ]
    resolution_note = "\n".join(resolution_lines)

    return CommunicationUpdate(
        incident_id=incident.id,
        technical_update=tech_update,
        stakeholder_update=stakeholder_update,
        resolution_note=resolution_note,
        created_at=datetime.now(UTC),
    )


@router.post("/{incident_id}/draft-pr", response_model=DraftPR)
def create_draft_pr(
    incident_id: str,
    store: Annotated[StoreProtocol, Depends(get_store)],
    pipeline: Annotated[WorkflowPipeline, Depends(get_pipeline)],
) -> DraftPR:
    incident = _get_or_404(store, incident_id)

    # 1. Return existing completed projection when present
    actions = store.list_external_actions(incident.id)
    completed_action = next((a for a in actions if a.status == "completed"), None)
    if completed_action is not None:
        return _map_to_draft_pr(completed_action, incident)

    # 2. Otherwise require latest exact approved approval/current valid state.
    # It must never accept REVIEW_READY, execute from EXTERNAL_ACTION_FAILED,
    # or silently reuse a stale approval.
    if incident.state == WorkflowState.REVIEW_READY:
        raise HTTPException(
            status_code=400,
            detail="draft PR cannot be requested in REVIEW_READY state",
        )
    if incident.state == WorkflowState.EXTERNAL_ACTION_FAILED:
        raise HTTPException(
            status_code=400,
            detail="draft PR cannot be requested directly in EXTERNAL_ACTION_FAILED state",
        )
    if incident.state not in (WorkflowState.WAITING_PR_APPROVAL, WorkflowState.CREATING_PR):
        raise HTTPException(
            status_code=400,
            detail=(
                f"incident is in state {incident.state}; "
                "draft PR requires WAITING_PR_APPROVAL or CREATING_PR"
            ),
        )

    approvals = store.list_approvals(incident.id)
    latest_approval = approvals[-1] if approvals else None
    if (
        latest_approval is None
        or latest_approval.approval_type != ApprovalType.CREATE_DRAFT_PR
        or latest_approval.status != ApprovalStatus.APPROVED
    ):
        raise HTTPException(
            status_code=400,
            detail="no approved CREATE_DRAFT_PR approval request found for this incident",
        )

    # Check if the latest approval is stale
    binding = store.get_approval_binding(latest_approval.id)
    if binding is None:
        raise HTTPException(
            status_code=400,
            detail="stale approval: missing binding",
        )

    patches = store.list_patches(incident.id)
    latest_patch = patches[-1] if patches else None
    if latest_patch is None:
        raise HTTPException(
            status_code=400,
            detail="stale approval: no patch attempt found",
        )
    latest_verification = store.get_verification_artifact_for_patch(latest_patch.id)
    if latest_verification is None:
        raise HTTPException(
            status_code=400,
            detail="stale approval: no verification artifact found for latest patch",
        )

    if (
        latest_patch.id != binding.plan_id
        or latest_patch.attempt != binding.plan_version
        or latest_verification.artifact_hash != binding.plan_hash
    ):
        raise HTTPException(
            status_code=400,
            detail="stale approval: patch or verification has changed",
        )

    # Do not reuse an already-decided approval if it was already used in an external action.
    existing_action_for_approval = next(
        (a for a in actions if a.approval_request_id == latest_approval.id), None
    )
    if existing_action_for_approval is not None:
        raise HTTPException(
            status_code=400,
            detail="the approved approval has already been used/decided",
        )

    pipeline.apply_pr_approval(incident, approved=True, approval_id=latest_approval.id)

    updated_actions = store.list_external_actions(incident.id)
    if not updated_actions:
        raise HTTPException(status_code=500, detail="External action was not recorded")
    return _map_to_draft_pr(updated_actions[-1], incident)


@router.get("/{incident_id}/draft-pr", response_model=DraftPR)
def get_draft_pr(
    incident_id: str,
    store: Annotated[StoreProtocol, Depends(get_store)],
) -> DraftPR:
    incident = _get_or_404(store, incident_id)
    actions = store.list_external_actions(incident_id)
    if not actions:
        raise HTTPException(
            status_code=404,
            detail="no draft PR action has been attempted for this incident",
        )
    return _map_to_draft_pr(actions[-1], incident)


@router.get("/{incident_id}/communications", response_model=CommunicationUpdate)
def get_communications(
    incident_id: str,
    store: Annotated[StoreProtocol, Depends(get_store)],
) -> CommunicationUpdate:
    incident = _get_or_404(store, incident_id)

    # Check if resolution artifacts exist (verified patch and completed draft-PR action)
    patches = store.list_patches(incident.id)
    latest_patch = patches[-1] if patches else None
    latest_verification = (
        store.get_verification_artifact_for_patch(latest_patch.id)
        if latest_patch
        else None
    )

    actions = store.list_external_actions(incident.id)
    completed_pr = next((a for a in actions if a.status == "completed"), None)

    if not latest_verification or not latest_verification.passed or not completed_pr:
        raise HTTPException(
            status_code=404,
            detail="no communications found; resolution artifacts must exist first",
        )

    comms = store.get_communications(incident.id)
    if comms is None:
        comms = _generate_comms(store, incident)
        store.add_communications(comms)
    return comms


@router.post("/{incident_id}/communications/regenerate", response_model=CommunicationUpdate)
def regenerate_communications(
    incident_id: str,
    store: Annotated[StoreProtocol, Depends(get_store)],
) -> CommunicationUpdate:
    incident = _get_or_404(store, incident_id)

    # Check if resolution artifacts exist (verified patch and completed draft-PR action)
    patches = store.list_patches(incident.id)
    latest_patch = patches[-1] if patches else None
    latest_verification = (
        store.get_verification_artifact_for_patch(latest_patch.id)
        if latest_patch
        else None
    )

    actions = store.list_external_actions(incident.id)
    completed_pr = next((a for a in actions if a.status == "completed"), None)

    if not latest_verification or not latest_verification.passed or not completed_pr:
        raise HTTPException(
            status_code=400,
            detail="cannot regenerate communications; resolution artifacts must exist first",
        )

    store.add_timeline_event(
        TimelineEvent(
            id=store.next_id("tl"),
            incident_id=incident.id,
            at=datetime.now(UTC),
            kind="communications_regenerated",
            description="Incident updates regenerated.",
        )
    )
    comms = _generate_comms(store, incident)
    store.add_communications(comms)
    return comms


@router.get("/{incident_id}/postmortem", response_model=Postmortem)
def get_postmortem(
    incident_id: str,
    store: Annotated[StoreProtocol, Depends(get_store)],
) -> Postmortem:
    _get_or_404(store, incident_id)
    postmortem = store.get_postmortem(incident_id)
    if postmortem is None:
        raise HTTPException(
            status_code=404,
            detail="no postmortem has been drafted or persisted for this incident yet",
        )
    return postmortem


