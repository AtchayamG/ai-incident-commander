"""Enumerations for the incident workflow, mirrored in packages/contracts for TypeScript."""

from enum import StrEnum


class WorkflowState(StrEnum):
    RECEIVED = "RECEIVED"
    NORMALIZING = "NORMALIZING"
    COLLECTING_EVIDENCE = "COLLECTING_EVIDENCE"
    EVIDENCE_READY = "EVIDENCE_READY"
    NEEDS_INPUT = "NEEDS_INPUT"
    INVESTIGATING = "INVESTIGATING"
    HYPOTHESES_READY = "HYPOTHESES_READY"
    PLANNING_REMEDIATION = "PLANNING_REMEDIATION"
    PLAN_READY = "PLAN_READY"
    NO_SAFE_REMEDIATION = "NO_SAFE_REMEDIATION"
    WAITING_PATCH_APPROVAL = "WAITING_PATCH_APPROVAL"
    PATCHING = "PATCHING"
    VERIFYING = "VERIFYING"
    PATCH_FAILED = "PATCH_FAILED"
    REVIEW_READY = "REVIEW_READY"
    WAITING_PR_APPROVAL = "WAITING_PR_APPROVAL"
    CREATING_PR = "CREATING_PR"
    PR_READY = "PR_READY"
    EXTERNAL_ACTION_FAILED = "EXTERNAL_ACTION_FAILED"
    RESOLUTION_DRAFTED = "RESOLUTION_DRAFTED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class Severity(StrEnum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"
    SEV4 = "SEV4"


class Environment(StrEnum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    DEMO = "demo"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ApprovalType(StrEnum):
    APPLY_PATCH = "APPLY_PATCH"
    CREATE_DRAFT_PR = "CREATE_DRAFT_PR"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class EvidenceKind(StrEnum):
    LOG = "log"
    METRIC = "metric"
    DEPLOY = "deploy"
    DIFF = "diff"
    CONFIG = "config"
    MANUAL = "manual"


class ProviderMode(StrEnum):
    SIMULATED = "simulated"
    LIVE = "live"
