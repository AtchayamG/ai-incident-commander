/**
 * TypeScript mirror of the backend contracts in
 * services/api/app/domain/{enums,contracts}.py.
 *
 * Keep both sides in sync: a parity test on each side pins the workflow
 * state list and transition map. When the backend contracts change, this
 * package must change in the same commit.
 */

export const WORKFLOW_STATES = [
  "RECEIVED",
  "NORMALIZING",
  "COLLECTING_EVIDENCE",
  "EVIDENCE_READY",
  "NEEDS_INPUT",
  "INVESTIGATING",
  "HYPOTHESES_READY",
  "PLANNING_REMEDIATION",
  "PLAN_READY",
  "NO_SAFE_REMEDIATION",
  "WAITING_PATCH_APPROVAL",
  "PATCHING",
  "VERIFYING",
  "PATCH_FAILED",
  "REVIEW_READY",
  "WAITING_PR_APPROVAL",
  "CREATING_PR",
  "PR_READY",
  "EXTERNAL_ACTION_FAILED",
  "RESOLUTION_DRAFTED",
  "CLOSED",
  "CANCELLED",
] as const;

export type WorkflowState = (typeof WORKFLOW_STATES)[number];

export const TERMINAL_STATES = [
  "CLOSED",
  "CANCELLED",
  "NO_SAFE_REMEDIATION",
] as const satisfies readonly WorkflowState[];

export const RECOVERABLE_STATES = [
  "NEEDS_INPUT",
  "PATCH_FAILED",
  "EXTERNAL_ACTION_FAILED",
] as const satisfies readonly WorkflowState[];

/** Mirror of services/api/app/workflow/state_machine.py TRANSITIONS. */
export const TRANSITIONS: Readonly<Record<WorkflowState, readonly WorkflowState[]>> = {
  RECEIVED: ["NORMALIZING", "CANCELLED"],
  NORMALIZING: ["COLLECTING_EVIDENCE", "CANCELLED"],
  COLLECTING_EVIDENCE: ["EVIDENCE_READY", "NEEDS_INPUT", "CANCELLED"],
  EVIDENCE_READY: ["INVESTIGATING", "CANCELLED"],
  INVESTIGATING: ["HYPOTHESES_READY", "NEEDS_INPUT", "CANCELLED"],
  HYPOTHESES_READY: ["PLANNING_REMEDIATION", "CANCELLED"],
  PLANNING_REMEDIATION: ["PLAN_READY", "NO_SAFE_REMEDIATION", "CANCELLED"],
  PLAN_READY: ["WAITING_PATCH_APPROVAL", "CANCELLED"],
  WAITING_PATCH_APPROVAL: ["PATCHING", "CANCELLED"],
  PATCHING: ["VERIFYING", "PATCH_FAILED", "CANCELLED"],
  VERIFYING: ["REVIEW_READY", "PATCHING", "PATCH_FAILED", "CANCELLED"],
  REVIEW_READY: ["WAITING_PR_APPROVAL", "RESOLUTION_DRAFTED", "CANCELLED"],
  WAITING_PR_APPROVAL: ["CREATING_PR", "REVIEW_READY", "CANCELLED"],
  CREATING_PR: ["PR_READY", "EXTERNAL_ACTION_FAILED", "CANCELLED"],
  PR_READY: ["RESOLUTION_DRAFTED", "CANCELLED"],
  EXTERNAL_ACTION_FAILED: ["WAITING_PR_APPROVAL", "CANCELLED"],
  RESOLUTION_DRAFTED: ["CLOSED", "CANCELLED"],
  NEEDS_INPUT: ["COLLECTING_EVIDENCE", "CANCELLED"],
  PATCH_FAILED: ["PLAN_READY", "CANCELLED"],
  NO_SAFE_REMEDIATION: [],
  CLOSED: [],
  CANCELLED: [],
};

export function isWorkflowState(value: string): value is WorkflowState {
  return (WORKFLOW_STATES as readonly string[]).includes(value);
}

export function isTerminalState(state: WorkflowState): boolean {
  return (TERMINAL_STATES as readonly WorkflowState[]).includes(state);
}

export function canTransition(from: WorkflowState, to: WorkflowState): boolean {
  return TRANSITIONS[from].includes(to);
}

export type Severity = "SEV1" | "SEV2" | "SEV3" | "SEV4";
export type Environment = "production" | "staging" | "development" | "demo";
export type RiskLevel = "low" | "medium" | "high";
export type ApprovalType = "APPLY_PATCH" | "CREATE_DRAFT_PR";
export type ApprovalStatus = "pending" | "approved" | "rejected" | "expired";
export type ApprovalDecision = "approved" | "rejected";
export type EvidenceKind = "log" | "metric" | "deploy" | "diff" | "config" | "manual";
export type ProviderMode = "simulated" | "live";

export interface SignalIn {
  provider: string;
  signal_type: string;
  payload: Record<string, unknown>;
}

export interface IncidentCreate {
  title: string;
  service: string;
  environment: Environment;
  severity: Severity;
  summary: string;
  signal?: SignalIn | null;
}

export interface Incident {
  id: string;
  title: string;
  service: string;
  environment: Environment;
  severity: Severity;
  summary: string;
  state: WorkflowState;
  provider_mode: ProviderMode;
  created_at: string;
  updated_at: string;
}

export interface IncidentList {
  items: Incident[];
  total: number;
}

export interface EvidenceItem {
  id: string;
  incident_id: string;
  kind: EvidenceKind;
  provider: string;
  source: string;
  summary: string;
  content: string;
  content_hash: string;
  display_ref: string;
  redaction_applied: boolean;
  redaction_rules?: string[];
  provenance?: Record<string, unknown>;
  captured_at: string;
  created_at: string;
}

export interface TimelineEvent {
  id: string;
  incident_id: string;
  at: string;
  kind: string;
  description: string;
  evidence_id: string | null;
}

export interface Hypothesis {
  id: string;
  incident_id: string;
  statement: string;
  confidence: number;
  supporting_evidence_ids: string[];
  contradictions: string[];
  unknowns: string[];
}

export interface RemediationPlan {
  id: string;
  incident_id: string;
  hypothesis_id: string;
  summary: string;
  steps: string[];
  risk_level: RiskLevel;
  max_files_changed: number;
  max_lines_changed: number;
}

export interface RemediationPlanArtifact {
  id: string;
  incident_id: string;
  investigation_report_id: string;
  hypothesis_id: string;
  version: number;
  summary: string;
  files_expected: string[];
  steps: string[];
  verification_commands: string[];
  allowed_commands: string[];
  prohibited_paths: string[];
  risk_level: RiskLevel;
  max_files_changed: number;
  max_lines_changed: number;
  max_attempts: number;
  timeout_seconds: number;
  network_allowed: boolean;
  rollback: string;
  rationale: string;
  artifact_hash: string;
  created_at: string;
}

export interface PatchAttempt {
  id: string;
  incident_id: string;
  plan_id: string;
  attempt: number;
  diff: string;
  files_changed: number;
  lines_changed: number;
  provider_mode: ProviderMode;
}

export interface VerificationCheck {
  name: string;
  passed: boolean;
  detail: string;
}

export interface VerificationRun {
  id: string;
  patch_id: string;
  passed: boolean;
  checks: VerificationCheck[];
}

export interface ApprovalRequest {
  id: string;
  incident_id: string;
  approval_type: ApprovalType;
  risk_level: RiskLevel;
  status: ApprovalStatus;
  reason: string;
  artifact_version: number;
  requested_at: string;
  expires_at: string;
  decided_at: string | null;
  decision_reason: string | null;
}

export interface ApprovalDecisionIn {
  decision: ApprovalDecision;
  reason: string;
  artifact_version?: number | null;
}

export interface WorkflowEvent {
  id: string;
  incident_id: string;
  sequence: number;
  from_state: WorkflowState | null;
  to_state: WorkflowState;
  trigger: string;
  at: string;
}

export interface HealthReady {
  status: string;
  demo_mode: boolean;
  provider_mode: ProviderMode;
}

export interface DependencyStatus {
  name: string;
  status: string;
}

export interface HealthDependencies {
  status: string;
  dependencies: DependencyStatus[];
}

export type InvestigationStatus = "complete" | "insufficient_evidence";

export type SpecialistKind = "telemetry" | "change_correlation" | "code_mapping" | "runbook";

export interface EvidenceCitation {
  evidence_id: string;
  note: string;
}

export interface SpecialistFinding {
  specialist: SpecialistKind;
  statement: string;
  citations: EvidenceCitation[];
}

export interface RejectedClaim {
  origin: string;
  statement: string;
  reason: string;
}

export interface FalsificationTest {
  description: string;
  steps: string[];
  expected_if_true: string;
  expected_if_false: string;
}

export interface AffectedFile {
  path: string;
  role: string;
  citations: EvidenceCitation[];
}

export interface CodeMapping {
  affected_files: AffectedFile[];
  suspect_commit: string;
  commit_citations: EvidenceCitation[];
  coverage_gap: string;
  coverage_gap_citations: EvidenceCitation[];
}

export interface RankedHypothesis {
  rank: number;
  hypothesis_id?: string | null;
  statement: string;
  confidence: number;
  supporting: EvidenceCitation[];
  contradicting: EvidenceCitation[];
  unknowns: string[];
  falsification_tests: FalsificationTest[];
  affected_files: string[];
  suspect_commit?: string | null;
  rationale: string;
}

export interface IncidentSummary {
  what_happened: string;
  impact: string;
  citations: EvidenceCitation[];
}

export interface InvestigationReport {
  id: string;
  incident_id: string;
  status: InvestigationStatus;
  gateway: string;
  remediation_enabled: boolean; // Wait, in typescript, it is boolean, not bool!
  summary: IncidentSummary | null;
  findings: SpecialistFinding[];
  hypotheses: RankedHypothesis[];
  code_mapping: CodeMapping | null;
  unknowns: string[];
  rejected_claims: RejectedClaim[];
  created_at: string;
}

export interface DraftPR {
  id: string;
  incident_id: string;
  status: string;
  url?: string;
  reference?: string;
  provider_mode: ProviderMode;
  idempotency_key?: string;
  error_message?: string;
  created_at: string;
}

export interface Communications {
  technical_update: string;
  stakeholder_update: string;
  resolution_note: string;
}

export interface PostmortemActionItem {
  description: string;
  owner: string;
  priority: string;
}

export interface Postmortem {
  id: string;
  incident_id: string;
  summary: string;
  impact: string;
  root_cause: string;
  resolution: string;
  timeline_json: TimelineEvent[];
  action_items_json: PostmortemActionItem[];
  markdown_uri?: string;
  created_at: string;
}

