from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.domain.contracts import (
    ActionItem,
    ApprovalRequest,
    CommunicationUpdate,
    EvidenceItem,
    ExternalAction,
    Hypothesis,
    Incident,
    PatchAttempt,
    Postmortem,
    RemediationPlan,
    TimelineEvent,
    VerificationRun,
    WorkflowEvent,
)
from app.domain.enums import Environment, Severity, WorkflowState
from app.domain.investigation import InvestigationReport
from app.domain.remediation import ApprovalBinding, RemediationPlanArtifact
from app.domain.sandbox import PatchExecutionArtifact
from app.domain.verification import VerificationRunArtifact
from app.store.models import (
    ApprovalBindingModel,
    ApprovalRequestModel,
    Base,
    CommunicationModel,
    EvidenceItemModel,
    ExternalActionModel,
    HypothesisModel,
    IncidentModel,
    InvestigationReportModel,
    PatchAttemptModel,
    PatchExecutionArtifactModel,
    PostmortemModel,
    RemediationPlanArtifactModel,
    RemediationPlanModel,
    TimelineEventModel,
    VerificationRunArtifactModel,
    VerificationRunModel,
    WorkflowEventModel,
)
from app.store.protocol import NotFoundError, StoreProtocol


class SqlAlchemyStore(StoreProtocol):
    def __init__(self, database_url: str) -> None:
        from sqlalchemy.pool import StaticPool
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        poolclass = StaticPool if database_url == "sqlite:///:memory:" else None

        if poolclass:
            self.engine = create_engine(
                database_url, connect_args=connect_args, poolclass=poolclass
            )
        else:
            self.engine = create_engine(database_url, connect_args=connect_args)

        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._counter = 0

    def ping(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def reset(self) -> None:
        # Preserve the schema so concurrent dashboard reads never observe the
        # drop/create gap during a demo reset. Readers see either the old rows
        # or the committed empty store; foreign-key order is reversed.
        with self.engine.begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())
        self._counter = 0

    def next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}-{self._counter:04d}"

    def add_incident(self, incident: Incident) -> Incident:
        with self.SessionLocal() as session:
            model = IncidentModel(
                id=incident.id,
                title=incident.title,
                service=incident.service,
                environment=incident.environment.value,
                severity=incident.severity.value,
                summary=incident.summary,
                state=incident.state.value,
                provider_mode=incident.provider_mode.value,
                created_at=incident.created_at,
                updated_at=incident.updated_at,
            )
            session.add(model)
            session.commit()
            return incident

    def get_incident(self, incident_id: str) -> Incident:
        with self.SessionLocal() as session:
            model = session.get(IncidentModel, incident_id)
            if not model:
                raise NotFoundError(f"incident {incident_id} not found")
            return Incident.model_validate(model, from_attributes=True)

    def list_incidents(
        self,
        status: WorkflowState | None = None,
        severity: Severity | None = None,
        service: str | None = None,
        environment: Environment | None = None,
        limit: int = 50,
    ) -> list[Incident]:
        with self.SessionLocal() as session:
            stmt = select(IncidentModel).order_by(IncidentModel.created_at.desc())
            if status:
                stmt = stmt.where(IncidentModel.state == status.value)
            if severity:
                stmt = stmt.where(IncidentModel.severity == severity.value)
            if service:
                stmt = stmt.where(IncidentModel.service == service)
            if environment:
                stmt = stmt.where(IncidentModel.environment == environment.value)
            stmt = stmt.limit(limit)
            models = session.scalars(stmt).all()
            return [Incident.model_validate(m, from_attributes=True) for m in models]

    def set_incident_state(self, incident_id: str, state: WorkflowState) -> Incident:
        with self.SessionLocal() as session:
            model = session.get(IncidentModel, incident_id)
            if not model:
                raise NotFoundError(f"incident {incident_id} not found")
            model.state = state.value
            model.updated_at = datetime.now(UTC)
            session.commit()
            session.refresh(model)
            return Incident.model_validate(model, from_attributes=True)

    def append_workflow_event(
        self,
        incident_id: str,
        from_state: WorkflowState | None,
        to_state: WorkflowState,
        trigger: str,
    ) -> WorkflowEvent:
        with self.SessionLocal() as session:
            count = session.query(WorkflowEventModel).filter_by(incident_id=incident_id).count()
            event = WorkflowEventModel(
                id=self.next_id("evt"),
                incident_id=incident_id,
                sequence=count + 1,
                from_state=from_state.value if from_state else None,
                to_state=to_state.value,
                trigger=trigger,
                at=datetime.now(UTC),
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            return WorkflowEvent.model_validate(event, from_attributes=True)

    def list_workflow_events(self, incident_id: str) -> list[WorkflowEvent]:
        with self.SessionLocal() as session:
            stmt = (
                select(WorkflowEventModel)
                .where(WorkflowEventModel.incident_id == incident_id)
                .order_by(WorkflowEventModel.sequence.asc())
            )
            models = session.scalars(stmt).all()
            return [WorkflowEvent.model_validate(m, from_attributes=True) for m in models]

    def add_evidence(self, item: EvidenceItem) -> EvidenceItem:
        with self.SessionLocal() as session:
            model = EvidenceItemModel(
                id=item.id,
                incident_id=item.incident_id,
                kind=item.kind.value,
                provider=item.provider,
                source=item.source,
                summary=item.summary,
                content=item.content,
                content_hash=item.content_hash,
                display_ref=item.display_ref,
                redaction_applied=item.redaction_applied,
                redaction_rules=item.redaction_rules,
                provenance=item.provenance,
                captured_at=item.captured_at,
                created_at=item.created_at,
            )
            session.add(model)
            session.commit()
            return item

    def list_evidence(self, incident_id: str) -> list[EvidenceItem]:
        with self.SessionLocal() as session:
            stmt = (
                select(EvidenceItemModel)
                .where(EvidenceItemModel.incident_id == incident_id)
                .order_by(EvidenceItemModel.captured_at.asc(), EvidenceItemModel.id.asc())
            )
            models = session.scalars(stmt).all()
            return [EvidenceItem.model_validate(m, from_attributes=True) for m in models]

    def add_timeline_event(self, event: TimelineEvent) -> TimelineEvent:
        with self.SessionLocal() as session:
            model = TimelineEventModel(
                id=event.id,
                incident_id=event.incident_id,
                at=event.at,
                kind=event.kind,
                description=event.description,
                evidence_id=event.evidence_id,
            )
            session.add(model)
            session.commit()
            return event

    def list_timeline(self, incident_id: str) -> list[TimelineEvent]:
        with self.SessionLocal() as session:
            stmt = (
                select(TimelineEventModel)
                .where(TimelineEventModel.incident_id == incident_id)
                .order_by(TimelineEventModel.at.asc(), TimelineEventModel.id.asc())
            )
            models = session.scalars(stmt).all()
            return [TimelineEvent.model_validate(m, from_attributes=True) for m in models]

    def add_hypothesis(self, hypothesis: Hypothesis) -> Hypothesis:
        with self.SessionLocal() as session:
            model = HypothesisModel(
                id=hypothesis.id,
                incident_id=hypothesis.incident_id,
                statement=hypothesis.statement,
                confidence=hypothesis.confidence,
                supporting_evidence_ids=hypothesis.supporting_evidence_ids,
                contradictions=hypothesis.contradictions,
                unknowns=hypothesis.unknowns,
            )
            session.add(model)
            session.commit()
            return hypothesis

    def list_hypotheses(self, incident_id: str) -> list[Hypothesis]:
        with self.SessionLocal() as session:
            stmt = (
                select(HypothesisModel)
                .where(HypothesisModel.incident_id == incident_id)
                .order_by(HypothesisModel.id.asc())
            )
            models = session.scalars(stmt).all()
            return [Hypothesis.model_validate(m, from_attributes=True) for m in models]

    def add_investigation_report(self, report: InvestigationReport) -> InvestigationReport:
        with self.SessionLocal() as session:
            model = InvestigationReportModel(
                id=report.id,
                incident_id=report.incident_id,
                status=report.status.value,
                gateway=report.gateway,
                remediation_enabled=report.remediation_enabled,
                document=report.model_dump(mode="json"),
                created_at=report.created_at,
            )
            session.add(model)
            session.commit()
            return report

    def get_investigation_report(self, incident_id: str) -> InvestigationReport | None:
        with self.SessionLocal() as session:
            stmt = (
                select(InvestigationReportModel)
                .where(InvestigationReportModel.incident_id == incident_id)
                .order_by(
                    InvestigationReportModel.created_at.desc(),
                    InvestigationReportModel.id.desc(),
                )
                .limit(1)
            )
            model = session.scalars(stmt).first()
            if model is None:
                return None
            return InvestigationReport.model_validate(model.document)

    def add_plan(self, plan: RemediationPlan) -> RemediationPlan:
        with self.SessionLocal() as session:
            model = RemediationPlanModel(
                id=plan.id,
                incident_id=plan.incident_id,
                hypothesis_id=plan.hypothesis_id,
                summary=plan.summary,
                steps=plan.steps,
                risk_level=plan.risk_level.value,
                max_files_changed=plan.max_files_changed,
                max_lines_changed=plan.max_lines_changed,
            )
            session.add(model)
            session.commit()
            return plan

    def list_plans(self, incident_id: str) -> list[RemediationPlan]:
        with self.SessionLocal() as session:
            stmt = select(RemediationPlanModel).where(
                RemediationPlanModel.incident_id == incident_id
            )
            models = session.scalars(stmt).all()
            return [RemediationPlan.model_validate(m, from_attributes=True) for m in models]

    def add_plan_artifact(self, artifact: RemediationPlanArtifact) -> RemediationPlanArtifact:
        with self.SessionLocal() as session:
            model = RemediationPlanArtifactModel(
                id=artifact.id,
                incident_id=artifact.incident_id,
                version=artifact.version,
                artifact_hash=artifact.artifact_hash,
                risk_level=artifact.risk_level.value,
                document=artifact.model_dump(mode="json"),
                created_at=artifact.created_at,
            )
            session.add(model)
            session.commit()
            return artifact

    def get_latest_plan_artifact(self, incident_id: str) -> RemediationPlanArtifact | None:
        with self.SessionLocal() as session:
            stmt = (
                select(RemediationPlanArtifactModel)
                .where(RemediationPlanArtifactModel.incident_id == incident_id)
                .order_by(
                    RemediationPlanArtifactModel.created_at.desc(),
                    RemediationPlanArtifactModel.version.desc(),
                    RemediationPlanArtifactModel.id.desc(),
                )
                .limit(1)
            )
            model = session.scalars(stmt).first()
            if model is None:
                return None
            return RemediationPlanArtifact.model_validate(model.document)

    def list_plan_artifacts(self, incident_id: str) -> list[RemediationPlanArtifact]:
        with self.SessionLocal() as session:
            stmt = (
                select(RemediationPlanArtifactModel)
                .where(RemediationPlanArtifactModel.incident_id == incident_id)
                .order_by(
                    RemediationPlanArtifactModel.created_at.asc(),
                    RemediationPlanArtifactModel.version.asc(),
                    RemediationPlanArtifactModel.id.asc(),
                )
            )
            models = session.scalars(stmt).all()
            return [RemediationPlanArtifact.model_validate(m.document) for m in models]

    def add_patch(self, patch: PatchAttempt) -> PatchAttempt:
        with self.SessionLocal() as session:
            model = PatchAttemptModel(
                id=patch.id,
                incident_id=patch.incident_id,
                plan_id=patch.plan_id,
                attempt=patch.attempt,
                diff=patch.diff,
                files_changed=patch.files_changed,
                lines_changed=patch.lines_changed,
                provider_mode=patch.provider_mode.value,
            )
            session.add(model)
            session.commit()
            return patch

    def list_patches(self, incident_id: str) -> list[PatchAttempt]:
        with self.SessionLocal() as session:
            stmt = (
                select(PatchAttemptModel)
                .where(PatchAttemptModel.incident_id == incident_id)
                .order_by(PatchAttemptModel.attempt.asc())
            )
            models = session.scalars(stmt).all()
            return [PatchAttempt.model_validate(m, from_attributes=True) for m in models]

    def add_patch_execution(self, artifact: PatchExecutionArtifact) -> PatchExecutionArtifact:
        with self.SessionLocal() as session:
            model = PatchExecutionArtifactModel(
                id=artifact.id,
                incident_id=artifact.incident_id,
                approval_id=artifact.approval_id,
                status=artifact.status.value,
                engine_id=artifact.engine_id,
                simulated=artifact.simulated,
                artifact_hash=artifact.artifact_hash,
                document=artifact.model_dump(mode="json"),
                created_at=artifact.created_at,
            )
            session.add(model)
            session.commit()
            return artifact

    def list_patch_executions(self, incident_id: str) -> list[PatchExecutionArtifact]:
        with self.SessionLocal() as session:
            stmt = (
                select(PatchExecutionArtifactModel)
                .where(PatchExecutionArtifactModel.incident_id == incident_id)
                .order_by(
                    PatchExecutionArtifactModel.created_at.asc(),
                    PatchExecutionArtifactModel.id.asc(),
                )
            )
            models = session.scalars(stmt).all()
            return [PatchExecutionArtifact.model_validate(m.document) for m in models]

    def add_verification(self, incident_id: str, run: VerificationRun) -> VerificationRun:
        with self.SessionLocal() as session:
            model = VerificationRunModel(
                id=run.id,
                patch_id=run.patch_id,
                passed=run.passed,
                checks=[c.model_dump() for c in run.checks],
            )
            session.add(model)
            session.commit()
            return run

    def list_verifications(self, incident_id: str) -> list[VerificationRun]:
        with self.SessionLocal() as session:
            stmt = (
                select(VerificationRunModel)
                .join(PatchAttemptModel)
                .where(PatchAttemptModel.incident_id == incident_id)
            )
            models = session.scalars(stmt).all()
            return [VerificationRun.model_validate(m, from_attributes=True) for m in models]

    def add_verification_artifact(
        self, artifact: VerificationRunArtifact
    ) -> VerificationRunArtifact:
        with self.SessionLocal() as session:
            model = VerificationRunArtifactModel(
                id=artifact.id,
                incident_id=artifact.incident_id,
                patch_id=artifact.patch_id,
                passed=artifact.passed,
                failure_kind=artifact.failure_kind.value if artifact.failure_kind else None,
                artifact_hash=artifact.artifact_hash,
                document=artifact.model_dump(mode="json"),
                created_at=artifact.created_at,
            )
            session.add(model)
            session.commit()
            return artifact

    def list_verification_artifacts(
        self, incident_id: str
    ) -> list[VerificationRunArtifact]:
        with self.SessionLocal() as session:
            stmt = (
                select(VerificationRunArtifactModel)
                .where(VerificationRunArtifactModel.incident_id == incident_id)
                .order_by(
                    VerificationRunArtifactModel.created_at.asc(),
                    VerificationRunArtifactModel.id.asc(),
                )
            )
            models = session.scalars(stmt).all()
            return [VerificationRunArtifact.model_validate(m.document) for m in models]

    def get_verification_artifact_for_patch(
        self, patch_id: str
    ) -> VerificationRunArtifact | None:
        with self.SessionLocal() as session:
            stmt = (
                select(VerificationRunArtifactModel)
                .where(VerificationRunArtifactModel.patch_id == patch_id)
                .order_by(
                    VerificationRunArtifactModel.created_at.desc(),
                    VerificationRunArtifactModel.id.desc(),
                )
                .limit(1)
            )
            model = session.scalars(stmt).first()
            if model is None:
                return None
            return VerificationRunArtifact.model_validate(model.document)

    def add_approval(self, approval: ApprovalRequest) -> ApprovalRequest:
        with self.SessionLocal() as session:
            model = ApprovalRequestModel(
                id=approval.id,
                incident_id=approval.incident_id,
                approval_type=approval.approval_type.value,
                risk_level=approval.risk_level.value,
                status=approval.status.value,
                reason=approval.reason,
                artifact_version=approval.artifact_version,
                requested_at=approval.requested_at,
                expires_at=approval.expires_at,
                decided_at=approval.decided_at,
                decision_reason=approval.decision_reason,
            )
            session.add(model)
            session.commit()
            return approval

    def get_approval(self, approval_id: str) -> ApprovalRequest:
        with self.SessionLocal() as session:
            model = session.get(ApprovalRequestModel, approval_id)
            if not model:
                raise NotFoundError(f"approval {approval_id} not found")
            return ApprovalRequest.model_validate(model, from_attributes=True)

    def update_approval(self, approval: ApprovalRequest) -> ApprovalRequest:
        with self.SessionLocal() as session:
            model = session.get(ApprovalRequestModel, approval.id)
            if not model:
                raise NotFoundError(f"approval {approval.id} not found")
            model.status = approval.status.value
            model.decided_at = approval.decided_at
            model.decision_reason = approval.decision_reason
            session.commit()
            return approval

    def list_approvals(self, incident_id: str) -> list[ApprovalRequest]:
        with self.SessionLocal() as session:
            stmt = select(ApprovalRequestModel).where(
                ApprovalRequestModel.incident_id == incident_id
            ).order_by(ApprovalRequestModel.requested_at, ApprovalRequestModel.id)
            models = session.scalars(stmt).all()
            return [ApprovalRequest.model_validate(m, from_attributes=True) for m in models]

    def add_approval_binding(self, binding: ApprovalBinding) -> ApprovalBinding:
        with self.SessionLocal() as session:
            model = ApprovalBindingModel(
                approval_id=binding.approval_id,
                incident_id=binding.incident_id,
                plan_id=binding.plan_id,
                plan_version=binding.plan_version,
                plan_hash=binding.plan_hash,
                action=binding.action.value,
                risk_level=binding.risk_level.value,
                approver_role=binding.approver_role,
                expires_at=binding.expires_at,
                created_at=binding.created_at,
            )
            session.add(model)
            session.commit()
            return binding

    def get_approval_binding(self, approval_id: str) -> ApprovalBinding | None:
        with self.SessionLocal() as session:
            model = session.get(ApprovalBindingModel, approval_id)
            if model is None:
                return None
            return ApprovalBinding.model_validate(model, from_attributes=True)

    def add_external_action(self, action: ExternalAction) -> ExternalAction:
        with self.SessionLocal() as session:
            model = ExternalActionModel(
                id=action.id,
                incident_id=action.incident_id,
                action_type=action.action_type,
                provider=action.provider,
                idempotency_key=action.idempotency_key,
                approval_request_id=action.approval_request_id,
                status=action.status,
                request_json=action.request_json,
                provider_receipt_json=action.provider_receipt_json,
                created_at=action.created_at,
                completed_at=action.completed_at,
            )
            session.add(model)
            session.commit()
            return action

    def get_external_action(self, action_id: str) -> ExternalAction:
        with self.SessionLocal() as session:
            model = session.get(ExternalActionModel, action_id)
            if not model:
                raise NotFoundError(f"external action {action_id} not found")
            return ExternalAction.model_validate(model, from_attributes=True)

    def get_external_action_by_idempotency_key(
        self, idempotency_key: str
    ) -> ExternalAction | None:
        with self.SessionLocal() as session:
            stmt = select(ExternalActionModel).where(
                ExternalActionModel.idempotency_key == idempotency_key
            )
            model = session.scalars(stmt).first()
            if model is None:
                return None
            return ExternalAction.model_validate(model, from_attributes=True)

    def update_external_action(self, action: ExternalAction) -> ExternalAction:
        with self.SessionLocal() as session:
            model = session.get(ExternalActionModel, action.id)
            if not model:
                raise NotFoundError(f"external action {action.id} not found")
            model.status = action.status
            model.provider = action.provider
            model.approval_request_id = action.approval_request_id
            model.request_json = action.request_json
            model.provider_receipt_json = action.provider_receipt_json
            model.created_at = action.created_at
            model.completed_at = action.completed_at
            session.commit()
            return action

    def list_external_actions(self, incident_id: str) -> list[ExternalAction]:
        with self.SessionLocal() as session:
            stmt = select(ExternalActionModel).where(
                ExternalActionModel.incident_id == incident_id
            ).order_by(ExternalActionModel.created_at, ExternalActionModel.id)
            models = session.scalars(stmt).all()
            return [ExternalAction.model_validate(m, from_attributes=True) for m in models]

    def add_postmortem(self, postmortem: Postmortem) -> Postmortem:
        with self.SessionLocal() as session:
            stmt = select(PostmortemModel).where(
                PostmortemModel.incident_id == postmortem.incident_id
            )
            model = session.scalars(stmt).first()

            timeline_dump = [
                t if isinstance(t, dict) else (
                    t.model_dump(mode="json") if hasattr(t, "model_dump") else t
                )
                for t in postmortem.timeline_json
            ]
            action_items_dump = cast(
                list[dict[str, Any]],
                [
                    a if isinstance(a, dict) else (
                        a.model_dump(mode="json") if hasattr(a, "model_dump") else a
                    )
                    for a in postmortem.action_items_json
                ]
            )

            if model is not None:
                model.summary = postmortem.summary
                model.impact = postmortem.impact
                model.root_cause = postmortem.root_cause
                model.resolution = postmortem.resolution
                model.timeline_json = timeline_dump
                model.action_items_json = action_items_dump
                model.markdown_content = postmortem.markdown_content
                model.created_at = postmortem.created_at
            else:
                model = PostmortemModel(
                    id=postmortem.id,
                    incident_id=postmortem.incident_id,
                    summary=postmortem.summary,
                    impact=postmortem.impact,
                    root_cause=postmortem.root_cause,
                    resolution=postmortem.resolution,
                    timeline_json=timeline_dump,
                    action_items_json=action_items_dump,
                    markdown_content=postmortem.markdown_content,
                    created_at=postmortem.created_at,
                )
                session.add(model)
            session.commit()
            return postmortem

    def get_postmortem(self, incident_id: str) -> Postmortem | None:
        with self.SessionLocal() as session:
            stmt = select(PostmortemModel).where(PostmortemModel.incident_id == incident_id)
            model = session.scalars(stmt).first()
            if model is None:
                return None
            action_items = [
                ActionItem(**a) if isinstance(a, dict) else a
                for a in model.action_items_json
            ]
            return Postmortem(
                id=model.id,
                incident_id=model.incident_id,
                summary=model.summary,
                impact=model.impact,
                root_cause=model.root_cause,
                resolution=model.resolution,
                timeline_json=model.timeline_json,
                action_items_json=action_items,
                markdown_content=model.markdown_content,
                markdown_uri=None,
                created_at=model.created_at,
            )

    def add_communications(self, comms: CommunicationUpdate) -> CommunicationUpdate:
        with self.SessionLocal() as session:
            stmt = select(CommunicationModel).where(
                CommunicationModel.incident_id == comms.incident_id
            )
            model = session.scalars(stmt).first()
            if model is not None:
                model.technical_update = comms.technical_update
                model.stakeholder_update = comms.stakeholder_update
                model.resolution_note = comms.resolution_note
                model.created_at = comms.created_at
            else:
                model = CommunicationModel(
                    incident_id=comms.incident_id,
                    technical_update=comms.technical_update,
                    stakeholder_update=comms.stakeholder_update,
                    resolution_note=comms.resolution_note,
                    created_at=comms.created_at,
                )
                session.add(model)
            session.commit()
            return comms

    def get_communications(self, incident_id: str) -> CommunicationUpdate | None:
        with self.SessionLocal() as session:
            stmt = select(CommunicationModel).where(CommunicationModel.incident_id == incident_id)
            model = session.scalars(stmt).first()
            if model is None:
                return None
            return CommunicationUpdate(
                incident_id=model.incident_id,
                technical_update=model.technical_update,
                stakeholder_update=model.stakeholder_update,
                resolution_note=model.resolution_note,
                created_at=model.created_at,
            )


