from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class IncidentModel(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    service: Mapped[str] = mapped_column(String(100))
    environment: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(50))
    summary: Mapped[str] = mapped_column(String(2000))
    state: Mapped[str] = mapped_column(String(50))
    provider_mode: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EvidenceItemModel(Base):
    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    kind: Mapped[str] = mapped_column(String(50))
    provider: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(100))
    summary: Mapped[str] = mapped_column(String(1000))
    content: Mapped[str] = mapped_column(String)
    content_hash: Mapped[str] = mapped_column(String(100))
    display_ref: Mapped[str] = mapped_column(String(500))
    redaction_applied: Mapped[bool] = mapped_column(Boolean)
    redaction_rules: Mapped[list[str]] = mapped_column(JSON)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TimelineEventModel(Base):
    __tablename__ = "timeline_events"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    kind: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(1000))
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_items.id"), nullable=True)


class HypothesisModel(Base):
    __tablename__ = "hypotheses"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    statement: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float)
    supporting_evidence_ids: Mapped[list[str]] = mapped_column(JSON)
    contradictions: Mapped[list[str]] = mapped_column(JSON)
    unknowns: Mapped[list[str]] = mapped_column(JSON)


class RemediationPlanModel(Base):
    __tablename__ = "remediation_plans"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    hypothesis_id: Mapped[str] = mapped_column(ForeignKey("hypotheses.id"))
    summary: Mapped[str] = mapped_column(String)
    steps: Mapped[list[str]] = mapped_column(JSON)
    risk_level: Mapped[str] = mapped_column(String(50))
    max_files_changed: Mapped[int] = mapped_column(Integer)
    max_lines_changed: Mapped[int] = mapped_column(Integer)


class PatchAttemptModel(Base):
    __tablename__ = "patch_attempts"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("remediation_plans.id"))
    attempt: Mapped[int] = mapped_column(Integer)
    diff: Mapped[str] = mapped_column(String)
    files_changed: Mapped[int] = mapped_column(Integer)
    lines_changed: Mapped[int] = mapped_column(Integer)
    provider_mode: Mapped[str] = mapped_column(String(50))


class VerificationRunModel(Base):
    __tablename__ = "verification_runs"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    patch_id: Mapped[str] = mapped_column(ForeignKey("patch_attempts.id"), index=True)
    passed: Mapped[bool] = mapped_column(Boolean)
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSON)


class ApprovalRequestModel(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    approval_type: Mapped[str] = mapped_column(String(50))
    risk_level: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str] = mapped_column(String(2000))
    artifact_version: Mapped[int] = mapped_column(Integer)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class WorkflowEventModel(Base):
    __tablename__ = "workflow_events"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    from_state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_state: Mapped[str] = mapped_column(String(50))
    trigger: Mapped[str] = mapped_column(String(100))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
