"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import type {
  Incident,
  EvidenceItem,
  TimelineEvent,
  Hypothesis,
  RemediationPlan,
  RemediationPlanArtifact,
  PatchAttempt,
  ApprovalRequest,
  WorkflowState,
  Severity,
  InvestigationReport,
} from "@incident-commander/contracts";
import {
  getIncident,
  getIncidentEvidence,
  getIncidentTimeline,
  getIncidentHypotheses,
  getIncidentPlans,
  getIncidentPlanArtifact,
  getIncidentPatches,
  getIncidentApprovals,
  startIncident,
  cancelIncident,
  decideApproval,
  getIncidentInvestigation,
} from "@/lib/api";

export default function IncidentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const incidentId = typeof params["id"] === "string" ? params["id"] : "";

  // UI States
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Entities
  const [incident, setIncident] = useState<Incident | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [plans, setPlans] = useState<RemediationPlan[]>([]);
  const [planArtifact, setPlanArtifact] = useState<RemediationPlanArtifact | null>(null);
  const [patches, setPatches] = useState<PatchAttempt[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [investigation, setInvestigation] = useState<InvestigationReport | null>(null);
  const [investigationError, setInvestigationError] = useState<string | null>(null);
  const [investigationStatus, setInvestigationStatus] = useState<number | null>(null);
  const [investigationLoading, setInvestigationLoading] = useState<boolean>(true);

  // Interactive UI States
  const [expandedEvidence, setExpandedEvidence] = useState<Record<string, boolean>>({});
  const [approvalReason, setApprovalReason] = useState("");
  const [approvalSubmitError, setApprovalSubmitError] = useState<string | null>(null);
  const [isSubmittingApproval, setIsSubmittingApproval] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Errors for sub-resources
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const [timelineError, setTimelineError] = useState<string | null>(null);
  const [hypothesesError, setHypothesesError] = useState<string | null>(null);
  const [plansError, setPlansError] = useState<string | null>(null);
  const [patchesError, setPatchesError] = useState<string | null>(null);
  const [approvalsError, setApprovalsError] = useState<string | null>(null);

  // Pipeline execution progress state
  const [pipelineProgress, setPipelineProgress] = useState<string | null>(null);
  const [pipelineStateIndex, setPipelineStateIndex] = useState<number>(-1);

  const PIPELINE_STAGES = [
    "Initializing incident commander pipeline...",
    "Normalizing incident signal...",
    "Querying telemetry sources for logs, metrics and events...",
    "Validating evidence provenance data...",
    "Analyzing failure correlation metrics...",
    "Formulating ranked hypotheses...",
    "Designing bounded remediation patch...",
    "Requesting approval for patch execution..."
  ];

  // Scroll to and focus evidence card
  const scrollToEvidence = (evidenceId: string) => {
    // Expand card if collapsed
    setExpandedEvidence(prev => ({
      ...prev,
      [evidenceId]: true
    }));
    setTimeout(() => {
      const el = document.getElementById(`evidence-${evidenceId}`);
      if (el) {
        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        el.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "center" });
        el.focus();
        el.classList.add("evidence-highlighted");
        setTimeout(() => {
          el.classList.remove("evidence-highlighted");
        }, reduceMotion ? 1 : 2000);
      }
    }, 100);
  };

  // Fetch all incident-related resources
  const loadIncidentData = useCallback(async (isSilent = false) => {
    if (!incidentId) return;
    if (!isSilent) {
      setLoading(true);
      setInvestigationLoading(true);
    } else {
      setRefreshing(true);
    }
    
    setErrorMsg(null);

    const [
      incidentRes,
      evidenceRes,
      timelineRes,
      hypothesesRes,
      plansRes,
      planArtifactRes,
      patchesRes,
      approvalsRes,
      investigationRes,
    ] = await Promise.all([
      getIncident(incidentId),
      getIncidentEvidence(incidentId),
      getIncidentTimeline(incidentId),
      getIncidentHypotheses(incidentId),
      getIncidentPlans(incidentId),
      getIncidentPlanArtifact(incidentId),
      getIncidentPatches(incidentId),
      getIncidentApprovals(incidentId),
      getIncidentInvestigation(incidentId),
    ]);

    if (!incidentRes.ok) {
      setErrorMsg(`Failed to fetch incident details: ${incidentRes.error}`);
      setLoading(false);
      setInvestigationLoading(false);
      setRefreshing(false);
      return;
    }

    setIncident(incidentRes.data);

    if (evidenceRes.ok) {
      setEvidence(evidenceRes.data);
      setEvidenceError(null);
    } else {
      setEvidenceError(`Failed to fetch evidence: ${evidenceRes.error || "Unknown error"}`);
    }

    if (timelineRes.ok) {
      setTimeline(timelineRes.data);
      setTimelineError(null);
    } else {
      setTimelineError(`Failed to fetch timeline: ${timelineRes.error || "Unknown error"}`);
    }

    if (hypothesesRes.ok) {
      setHypotheses(hypothesesRes.data);
      setHypothesesError(null);
    } else {
      setHypothesesError(`Failed to fetch hypotheses: ${hypothesesRes.error || "Unknown error"}`);
    }

    if (plansRes.ok) {
      setPlans(plansRes.data);
      setPlansError(null);
    } else {
      setPlansError(`Failed to fetch remediation plans: ${plansRes.error || "Unknown error"}`);
    }

    if (planArtifactRes.ok) {
      setPlanArtifact(planArtifactRes.data);
    } else if (planArtifactRes.status === 404) {
      setPlanArtifact(null);
    } else {
      setPlansError(`Failed to fetch bounded remediation artifact: ${planArtifactRes.error || "Unknown error"}`);
    }

    if (patchesRes.ok) {
      setPatches(patchesRes.data);
      setPatchesError(null);
    } else {
      setPatchesError(`Failed to fetch patch attempts: ${patchesRes.error || "Unknown error"}`);
    }

    if (approvalsRes.ok) {
      setApprovals(approvalsRes.data);
      setApprovalsError(null);
    } else {
      setApprovalsError(`Failed to fetch approvals: ${approvalsRes.error || "Unknown error"}`);
    }

    if (investigationRes.ok) {
      setInvestigation(investigationRes.data);
      setInvestigationError(null);
      setInvestigationStatus(200);
    } else {
      setInvestigation(null);
      setInvestigationStatus(investigationRes.status);
      setInvestigationError(investigationRes.error || "Failed to fetch investigation");
    }

    setLoading(false);
    setInvestigationLoading(false);
    setRefreshing(false);
  }, [incidentId]);

  // Initial Load
  useEffect(() => {
    loadIncidentData();
  }, [loadIncidentData]);

  // Auto-refresh poll loop
  useEffect(() => {
    if (!autoRefresh || loading || !incident) return;
    
    // Check if incident is in terminal state
    const terminalStates: WorkflowState[] = ["CLOSED", "CANCELLED", "NO_SAFE_REMEDIATION"];
    if (terminalStates.includes(incident.state)) {
      return; // Stop polling on terminal states
    }

    const interval = setInterval(() => {
      loadIncidentData(true);
    }, 5000);

    return () => clearInterval(interval);
  }, [autoRefresh, loading, incident, loadIncidentData]);

  // Actions
  const handleStartIncident = async () => {
    if (!incident) return;
    setActionError(null);
    setPipelineProgress("Starting pipeline...");
    setPipelineStateIndex(0);

    const apiPromise = startIncident(incident.id);

    // Step-by-step UI progression sequence
    for (let i = 0; i < PIPELINE_STAGES.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 300));
      setPipelineStateIndex(i);
      setPipelineProgress(PIPELINE_STAGES[i]!);
    }

    const res = await apiPromise;
    setPipelineProgress(null);
    setPipelineStateIndex(-1);

    if (res.ok) {
      loadIncidentData(true);
    } else {
      setActionError(`Failed to start pipeline: ${res.error}`);
    }
  };

  const handleCancelIncident = async () => {
    if (!incident) return;
    if (!confirm("Are you sure you want to cancel this incident process?")) return;
    setActionError(null);
    const res = await cancelIncident(incident.id);
    if (res.ok) {
      loadIncidentData(true);
    } else {
      setActionError(`Failed to cancel incident: ${res.error}`);
    }
  };

  const handleDecision = async (approvalId: string, decision: "approved" | "rejected") => {
    if (!approvalReason.trim()) {
      setApprovalSubmitError("A reason is required to decide on this request.");
      return;
    }

    setApprovalSubmitError(null);
    setIsSubmittingApproval(true);

    const res = await decideApproval(approvalId, {
      decision,
      reason: approvalReason.trim(),
    });

    setIsSubmittingApproval(false);

    if (res.ok) {
      setApprovalReason("");
      loadIncidentData(true);
    } else {
      setApprovalSubmitError(`Failed to submit decision: ${res.error}`);
    }
  };

  const toggleEvidence = (id: string) => {
    setExpandedEvidence(prev => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const getSeverityLabel = (sev: Severity) => {
    switch (sev) {
      case "SEV1": return "SEV1 - Critical";
      case "SEV2": return "SEV2 - Major";
      case "SEV3": return "SEV3 - Minor";
      case "SEV4": return "SEV4 - Low";
      default: return sev;
    }
  };

  const getStatusBadgeClass = (state: WorkflowState) => {
    const terminalStates: WorkflowState[] = ["CLOSED", "CANCELLED", "NO_SAFE_REMEDIATION"];
    const needsInputStates: WorkflowState[] = ["NEEDS_INPUT", "PATCH_FAILED", "EXTERNAL_ACTION_FAILED"];
    
    if (terminalStates.includes(state)) {
      return "badge-sev4"; // muted gray
    }
    if (needsInputStates.includes(state)) {
      return "badge-sev2"; // warning yellow
    }
    if (state === "WAITING_PATCH_APPROVAL" || state === "WAITING_PR_APPROVAL") {
      return "badge-sev1"; // critical red/amber
    }
    return "badge-sev3"; // blue info
  };

  const renderDiff = (diffText: string) => {
    const lines = diffText.split("\n");
    return (
      <div className="diff-container" style={{ maxHeight: "350px", overflowY: "auto" }}>
        {lines.map((line, idx) => {
          let className = "diff-line";
          if (line.startsWith("+")) className = "diff-line diff-line-added";
          else if (line.startsWith("-")) className = "diff-line diff-line-removed";
          return (
            <span key={idx} className={className}>
              {line}
            </span>
          );
        })}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="container" style={{ textAlign: "center", paddingTop: "5rem" }}>
        <h1 style={{ marginBottom: "1rem" }} className="gradient-text">Incident War Room Loading...</h1>
        <div style={{ width: "50px", height: "50px", border: "5px solid var(--border-color)", borderTopColor: "var(--primary)", borderRadius: "50%", margin: "0 auto", animation: "spin 1s linear infinite" }}></div>
        <style jsx>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  if (errorMsg || !incident) {
    return (
      <div className="container" style={{ padding: "3rem 1.5rem" }}>
        <div role="alert" style={{ background: "#1e131d", border: "1px solid rgba(239, 68, 68, 0.4)", color: "#fca5a5", borderRadius: "12px", padding: "2rem", textAlign: "center" }}>
          <h2>⚠️ Error Loading War Room</h2>
          <p style={{ margin: "1rem 0" }}>{errorMsg || "Incident not found in active database."}</p>
          <div style={{ display: "flex", justifyContent: "center", gap: "1rem" }}>
            <button className="btn btn-secondary" onClick={() => router.push("/")}>Back to Dashboard</button>
            <button className="btn btn-primary" onClick={() => loadIncidentData()}>Retry</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <main className="container">
      {/* Back button and status refresh bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "1rem" }}>
        <button className="btn btn-secondary" onClick={() => router.push("/")}>
          ⬅ Back to Incident Dashboard
        </button>
        
        <div style={{ display: "flex", alignContent: "center", gap: "1rem" }}>
          <label style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", fontSize: "0.9rem", color: "var(--text-muted)", cursor: "pointer" }}>
            <input 
              type="checkbox" 
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              style={{ cursor: "pointer" }}
            />
            Auto-refresh (5s)
          </label>
          <button 
            className="btn btn-secondary" 
            style={{ padding: "0.5rem 0.75rem", fontSize: "0.85rem" }}
            onClick={() => loadIncidentData(true)}
            disabled={refreshing}
          >
            {refreshing ? "Refreshing..." : "🔄 Refresh Now"}
          </button>
        </div>
      </div>

      {/* Incident Header Info Card */}
      <header className="card" style={{ marginBottom: "1.5rem", borderLeft: "4px solid var(--primary)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem", flexWrap: "wrap" }}>
              <span style={{ fontSize: "0.95rem", fontWeight: "bold", background: "var(--bg-main)", padding: "0.25rem 0.5rem", borderRadius: "4px", color: "var(--text-muted)" }}>
                {incident.id}
              </span>
              <span className={`badge badge-${incident.severity.toLowerCase()}`}>
                {getSeverityLabel(incident.severity)}
              </span>
              <span className={`badge badge-state ${getStatusBadgeClass(incident.state)}`}>
                State: {incident.state.replace(/_/g, " ")}
              </span>
              {incident.provider_mode === "simulated" && (
                <span className="badge badge-sev4" style={{ border: "1px solid rgba(255,255,255,0.15)" }}>
                  🤖 SIMULATED DATA
                </span>
              )}
            </div>
            <h1 style={{ fontSize: "1.85rem", marginBottom: "0.5rem" }}>{incident.title}</h1>
            <p style={{ color: "var(--text-muted)", fontSize: "0.95rem" }}>
              Service: <strong style={{ color: "var(--text-main)", fontFamily: "var(--font-mono)" }}>{incident.service}</strong> | Environment: <strong>{incident.environment}</strong>
            </p>
          </div>

          {/* Action buttons on Incident */}
          <div style={{ display: "flex", gap: "0.5rem" }}>
            {incident.state === "RECEIVED" && (
              <button className="btn btn-primary" onClick={handleStartIncident}>
                🚀 Start Diagnosing Pipeline
              </button>
            )}
            
            {incident.state !== "CLOSED" && incident.state !== "CANCELLED" && incident.state !== "NO_SAFE_REMEDIATION" && (
              <button className="btn btn-danger" onClick={handleCancelIncident}>
                🚫 Cancel Incident Process
              </button>
            )}
          </div>
        </div>

        {actionError && (
          <div role="alert" style={{ background: "#1e131d", color: "#fca5a5", border: "1px solid rgba(239, 68, 68, 0.4)", padding: "0.75rem", borderRadius: "4px", marginTop: "1rem", fontSize: "0.9rem" }}>
            {actionError}
          </div>
        )}

        {pipelineProgress && (
          <div 
            className="card" 
            style={{ 
              marginTop: "1rem", 
              border: "1px solid var(--primary)", 
              background: "rgba(139, 92, 246, 0.05)", 
              padding: "1rem" 
            }} 
            data-testid="pipeline-progress-panel"
            aria-live="polite"
          >
            <h3 style={{ fontSize: "1.05rem", marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span className="spin-indicator" style={{ display: "inline-block", width: "14px", height: "14px", border: "2px solid var(--border-color)", borderTopColor: "var(--primary)", borderRadius: "50%", animation: "spin 1s linear infinite" }}></span>
              Autonomous Investigation Pipeline Active: <span style={{ color: "var(--primary-hover)" }}>{pipelineProgress}</span>
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "0.5rem", marginTop: "0.5rem" }}>
              {PIPELINE_STAGES.map((stage, idx) => {
                let statusIcon = "⚪";
                let textColor = "var(--text-muted)";
                let fontWeight = "normal";
                if (idx < pipelineStateIndex) {
                  statusIcon = "✅";
                  textColor = "var(--success)";
                } else if (idx === pipelineStateIndex) {
                  statusIcon = "⚡";
                  textColor = "var(--primary-hover)";
                  fontWeight = "600";
                }
                return (
                  <div key={idx} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem", color: textColor, fontWeight }}>
                    <span>{statusIcon}</span>
                    <span>{stage}</span>
                  </div>
                );
              })}
            </div>
            <style jsx>{`
              @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
              }
            `}</style>
          </div>
        )}

        <div style={{ marginTop: "1rem", background: "rgba(0,0,0,0.15)", padding: "1rem", borderRadius: "6px", border: "1px solid var(--border-color)" }}>
          <h3 style={{ fontSize: "0.95rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>Intake Description Summary:</h3>
          <p style={{ fontSize: "0.95rem", whiteSpace: "pre-wrap" }}>{incident.summary}</p>
        </div>
      </header>

      {/* Main Grid: Left Column Timeline & Evidence. Right Column: Hypotheses, Remediation, Approvals */}
      <div className="grid grid-main-detail">
        {/* Left Column: Investigation Evidence & Event Log */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          
          {/* Timeline Event Log */}
          <div className="card">
            <h2 style={{ fontSize: "1.25rem", marginBottom: "1.25rem" }}>🕒 Chronological Timeline</h2>
            
            {timelineError && (
              <div role="alert" style={{ background: "#1e131d", color: "#fca5a5", border: "1px solid rgba(239, 68, 68, 0.4)", padding: "1rem", borderRadius: "8px", marginBottom: "1rem" }}>
                <strong>⚠️ Timeline Fetch Error:</strong> {timelineError}
              </div>
            )}

            {timeline.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: "0.95rem" }}>No events logged in the timeline yet.</p>
            ) : (
              <div className="timeline">
                {[...timeline]
                  .sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime())
                  .map((evt) => (
                    <div key={evt.id} className="timeline-item" aria-label={`Timeline event: ${evt.description} at ${evt.at}`}>
                      <div className="timeline-time">{new Date(evt.at).toLocaleString()}</div>
                      <div style={{ fontWeight: "600", fontSize: "0.95rem", color: "#ffffff" }}>{evt.kind.replace(/\./g, " ").toUpperCase()}</div>
                      <p style={{ fontSize: "0.9rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>{evt.description}</p>
                      {evt.evidence_id && (
                        <button
                           onClick={() => scrollToEvidence(evt.evidence_id!)}
                           style={{
                             background: "none",
                             border: "none",
                             padding: 0,
                             fontSize: "0.8rem",
                             color: "var(--primary-hover)",
                             textDecoration: "underline",
                             display: "inline-block",
                             marginTop: "0.25rem",
                             cursor: "pointer",
                             fontFamily: "inherit",
                             textAlign: "left"
                           }}
                           data-testid={`timeline-link-${evt.evidence_id}`}
                        >
                          View Supporting Evidence
                        </button>
                      )}
                    </div>
                  ))}
              </div>
            )}
          </div>

          {/* Evidence Panel with Provenance */}
          <div className="card">
            <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>🔍 Telemetry & Evidence Provenance</h2>
            
            {evidenceError && (
              <div role="alert" style={{ background: "#1e131d", color: "#fca5a5", border: "1px solid rgba(239, 68, 68, 0.4)", padding: "1rem", borderRadius: "8px", marginBottom: "1rem" }}>
                <strong>⚠️ Evidence Fetch Error:</strong> {evidenceError}
              </div>
            )}

            {evidence.length === 0 ? (
              <div style={{ padding: "1.5rem 1rem", border: "1px dashed var(--border-color)", borderRadius: "6px", textAlign: "center", color: "var(--text-muted)" }}>
                <p>No telemetry or logs gathered yet.</p>
                <p style={{ fontSize: "0.8rem", marginTop: "0.25rem" }}>
                  Telemetry collection starts automatically once the diagnosing pipeline begins.
                </p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                {evidence.map((item) => {
                  const isSimulated = item.provenance?.simulated === true || (incident && incident.provider_mode === "simulated");
                  return (
                    <div 
                      key={item.id} 
                      id={`evidence-${item.id}`} 
                      tabIndex={-1}
                      className="evidence-card"
                      data-testid={`evidence-card-${item.kind}`}
                      data-evidence-id={item.id}
                      style={{ border: "1px solid var(--border-color)", borderRadius: "8px", background: "rgba(0,0,0,0.1)" }}
                    >
                      {/* Header bar */}
                      <div 
                        onClick={() => toggleEvidence(item.id)}
                        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleEvidence(item.id); } }}
                        tabIndex={0}
                        role="button"
                        data-testid={`evidence-expand-${item.id}`}
                        aria-expanded={expandedEvidence[item.id] || false}
                        style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.75rem 1rem", cursor: "pointer", userSelect: "none" }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                          <span className="badge badge-sev3" style={{ background: "rgba(59,130,246,0.15)", color: "var(--info)" }}>
                            {item.kind}
                          </span>
                          
                          {isSimulated && (
                            <span className="badge badge-sev4" data-testid="evidence-simulated-label" style={{ background: "rgba(245, 158, 11, 0.1)", color: "var(--warning)", border: "1px solid rgba(245, 158, 11, 0.3)" }}>
                              🤖 SIMULATED
                            </span>
                          )}

                          {item.redaction_applied && (
                            <span className="badge" data-testid="evidence-redacted-label" style={{ background: "rgba(239,68,68,0.1)", color: "var(--error)", border: "1px solid rgba(239,68,68,0.3)" }}>
                              🔒 REDACTED
                            </span>
                          )}

                          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                            provider: <strong data-testid="evidence-provider">{item.provider}</strong>
                          </span>

                          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                            source: <strong data-testid="evidence-source">{item.source}</strong>
                          </span>
                        </div>
                        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                          {expandedEvidence[item.id] ? "Collapse ▲" : "Expand ▼"}
                        </div>
                      </div>

                      {/* Summary row */}
                      <div style={{ padding: "0 1rem 0.75rem 1rem", fontSize: "0.95rem" }}>
                        <p style={{ fontWeight: "600" }}>{item.summary}</p>
                      </div>

                      {/* High-density Metadata Row */}
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.5rem", padding: "0.75rem 1rem", borderTop: "1px dashed var(--border-color)", fontSize: "0.8rem", color: "var(--text-muted)", background: "rgba(0,0,0,0.05)" }}>
                        <div><strong>Captured:</strong> <span data-testid="evidence-captured-at">{new Date(item.captured_at).toLocaleString()}</span></div>
                        <div><strong>Ref:</strong> <code data-testid="evidence-display-ref" style={{ color: "var(--text-main)" }}>{item.display_ref || "N/A"}</code></div>
                        <div><strong>Hash:</strong> <code data-testid="evidence-hash" style={{ color: "var(--text-muted)", fontSize: "0.75rem" }} title={item.content_hash}>{item.content_hash || "N/A"}</code></div>
                      </div>

                      {/* Collapsible raw content */}
                      {expandedEvidence[item.id] && (
                        <div style={{ borderTop: "1px solid var(--border-color)", padding: "1rem", background: "#050811", borderBottomLeftRadius: "8px", borderBottomRightRadius: "8px" }}>
                          <h4 style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.5rem", fontFamily: "var(--font-mono)" }}>
                            RAW SANITIZED EVIDENCE CONTENT:
                          </h4>
                          <pre data-testid="evidence-content" style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", overflowX: "auto", whiteSpace: "pre-wrap", color: "#e2e8f0", background: "rgba(0,0,0,0.3)", padding: "0.75rem", borderRadius: "4px", border: "1px solid #101827" }}>
                            {item.content}
                          </pre>
                          
                          {item.redaction_applied && item.redaction_rules && item.redaction_rules.length > 0 && (
                            <div style={{ marginTop: "0.75rem", fontSize: "0.78rem", color: "var(--error)", background: "rgba(239, 68, 68, 0.05)", padding: "0.5rem", borderRadius: "4px", border: "1px solid rgba(239, 68, 68, 0.15)" }}>
                              <strong>Applied Redaction Rules:</strong> <span data-testid="evidence-redaction-rules">{item.redaction_rules.join(", ")}</span>
                            </div>
                          )}
                          
                          <div style={{ marginTop: "0.75rem", fontSize: "0.75rem", color: "var(--text-muted)", borderTop: "1px dashed var(--border-color)", paddingTop: "0.5rem" }}>
                            <strong>Provenance Metadata:</strong>
                            <pre data-testid="evidence-provenance" style={{ marginTop: "0.25rem", color: "#a0aec0", fontSize: "0.75rem", overflowX: "auto", background: "rgba(0,0,0,0.2)", padding: "0.5rem", borderRadius: "4px" }}>
                              {JSON.stringify(item.provenance, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>

        {/* Right Column: Hypotheses, Remediation Plans, Approval Form */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {approvalsError && (
            <div role="alert" style={{ background: "#1e131d", color: "#fca5a5", border: "1px solid rgba(239, 68, 68, 0.4)", padding: "1rem", borderRadius: "8px" }}>
              <strong>⚠️ Approvals Fetch Error:</strong> {approvalsError}
            </div>
          )}
          {hypothesesError && (
            <div role="alert" style={{ background: "#1e131d", color: "#fca5a5", border: "1px solid rgba(239, 68, 68, 0.4)", padding: "1rem", borderRadius: "8px" }}>
              <strong>⚠️ Hypotheses Fetch Error:</strong> {hypothesesError}
            </div>
          )}

          {/* Active Approvals Gate Card (Highest Priority Action Item) */}
          {(investigation?.remediation_enabled ?? true) && approvals.length > 0 && approvals.some(a => a.status === "pending") && (
            <div className="card" style={{ border: "2px solid var(--warning)", background: "rgba(245, 158, 11, 0.05)" }}>
              <h2 style={{ fontSize: "1.25rem", color: "var(--warning)", marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                ⚠️ Action Required: Human Approval Gate
              </h2>
              {approvals.filter(a => a.status === "pending").map((approval) => {
                const plan = plans.find(p => p.incident_id === approval.incident_id) || plans[0];
                const hyp = investigation?.hypotheses?.[0];
                return (
                <div key={approval.id} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  <div style={{ background: "rgba(245, 158, 11, 0.1)", padding: "0.75rem", borderRadius: "6px", border: "1px solid rgba(245, 158, 11, 0.2)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem" }}>
                      <span><strong>Type:</strong> {approval.approval_type}</span>
                      <span className="badge badge-sev2">Risk: {approval.risk_level.toUpperCase()}</span>
                    </div>
                    <div><strong>Request rationale:</strong> {approval.reason}</div>
                    <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
                      Requested at: {new Date(approval.requested_at).toLocaleTimeString()} (Expires: {new Date(approval.expires_at).toLocaleTimeString()})
                    </div>
                  </div>

                  <div style={{ border: "1px solid var(--primary-light)", padding: "1rem", borderRadius: "6px", background: "rgba(139, 92, 246, 0.05)" }}>
                    <h3 style={{ fontSize: "1rem", color: "var(--primary-hover)", marginBottom: "0.75rem" }}>
                      📦 Bounded Remediation Artifact (v{planArtifact?.version ?? approval.artifact_version})
                    </h3>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", fontSize: "0.85rem", marginBottom: "1rem" }}>
                      <div>
                        <strong>Exact Files & Budgets:</strong><br />
                        <span style={{ color: "var(--text-muted)" }}>Files: {planArtifact?.files_expected.join(", ") ?? "Unavailable"}</span><br />
                        <span style={{ color: "var(--text-muted)" }}>Budget: {planArtifact?.max_files_changed ?? plan?.max_files_changed ?? "N/A"} files / {planArtifact?.max_lines_changed ?? plan?.max_lines_changed ?? "N/A"} lines</span><br />
                        <span style={{ color: "var(--text-muted)" }}>Network: {planArtifact ? (planArtifact.network_allowed ? "Allowed" : "Denied") : "Unavailable"}</span>
                      </div>
                      <div>
                        <strong>Hash & Provenance:</strong><br />
                        <code data-testid="remediation-artifact-hash" style={{ fontSize: "0.75rem", color: "var(--text-main)", overflowWrap: "anywhere" }}>{planArtifact?.artifact_hash ?? "Unavailable"}</code><br />
                        <span style={{ color: "var(--text-muted)" }}>Artifact: {planArtifact?.id ?? "Unavailable"} · created {planArtifact ? new Date(planArtifact.created_at).toLocaleString() : "N/A"}</span>
                      </div>
                    </div>

                    <div style={{ marginBottom: "1rem", fontSize: "0.9rem" }}>
                      <strong>Diagnosis Link:</strong>{" "}
                      <a href={`#evidence-${hyp?.supporting?.[0]?.evidence_id ?? ""}`} style={{ color: "var(--primary-hover)", textDecoration: "underline" }} onClick={(e) => { e.preventDefault(); if (hyp?.supporting?.[0]?.evidence_id) scrollToEvidence(hyp.supporting[0].evidence_id); }}>
                        View Primary Evidence ({hyp?.supporting?.[0]?.evidence_id ?? "N/A"})
                      </a>
                    </div>

                    <div style={{ marginBottom: "1rem", fontSize: "0.9rem" }}>
                      <strong>Verification Commands:</strong>
                      {planArtifact?.verification_commands.length ? (
                         <div style={{ padding: "0.5rem", background: "rgba(0,0,0,0.2)", borderRadius: "4px", marginTop: "0.25rem" }}>
                           {planArtifact.verification_commands.map(command => <div key={command}><code style={{ color: "var(--success)" }}>{command}</code></div>)}
                         </div>
                      ) : (
                         <div style={{ color: "var(--text-muted)" }}>No deterministic verification steps generated.</div>
                      )}
                    </div>

                    <div style={{ marginBottom: "1rem", fontSize: "0.9rem" }}>
                      <strong>Rollback Procedure:</strong>
                      <div style={{ color: "var(--text-muted)", fontSize: "0.8rem", marginTop: "0.25rem" }}>
                        <span>{planArtifact?.rollback ?? "Unavailable"}</span>
                      </div>
                    </div>

                    <div style={{ marginTop: "1rem", borderTop: "1px dashed var(--border-color)", paddingTop: "0.75rem" }}>
                      <strong>Intended Changes:</strong>
                      {planArtifact?.steps.length ? <ol>{planArtifact.steps.map(step => <li key={step}>{step}</li>)}</ol> : <div style={{ color: "var(--text-muted)", fontStyle: "italic", fontSize: "0.85rem" }}>No immutable artifact is available.</div>}
                    </div>
                  </div>

                  {approvalSubmitError && (
                    <div role="alert" style={{ color: "#fca5a5", fontSize: "0.85rem", background: "#1e131d", border: "1px solid rgba(239, 68, 68, 0.4)", padding: "0.5rem", borderRadius: "4px" }}>
                      {approvalSubmitError}
                    </div>
                  )}

                  <div className="form-group">
                    <label htmlFor="reason-input" className="form-label">Provide justification for approval or rejection:</label>
                    <input 
                      id="reason-input"
                      type="text" 
                      className="form-input" 
                      placeholder="e.g. Bounded path looks correct, approving apply."
                      value={approvalReason}
                      onChange={(e) => setApprovalReason(e.target.value)}
                    />
                  </div>

                  <div style={{ display: "flex", gap: "0.75rem" }}>
                    <button 
                      className="btn btn-primary" 
                      style={{ background: "#065f46", color: "#ffffff" }}
                      onClick={() => handleDecision(approval.id, "approved")}
                      disabled={isSubmittingApproval}
                    >
                      {isSubmittingApproval ? "Submitting..." : "✓ Approve & Execute Patch"}
                    </button>
                    <button 
                      className="btn btn-danger"
                      onClick={() => handleDecision(approval.id, "rejected")}
                      disabled={isSubmittingApproval}
                    >
                      {isSubmittingApproval ? "Submitting..." : "✕ Reject Patch"}
                    </button>
                  </div>
                </div>
              )})}
            </div>
          )}

          {/* Resolved/Decided approvals history */}
          {approvals.length > 0 && approvals.some(a => a.status !== "pending") && (
            <div className="card">
              <h2 style={{ fontSize: "1.1rem", marginBottom: "0.75rem" }}>Approval Decision Record</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {approvals.filter(a => a.status !== "pending").map((approval) => (
                  <div key={approval.id} style={{ padding: "0.75rem", background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-color)", borderRadius: "6px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.25rem" }}>
                      <span style={{ fontSize: "0.85rem", fontWeight: "700" }}>{approval.approval_type}</span>
                      <span className={`badge ${approval.status === "approved" ? "badge-sev3" : "badge-sev1"}`} style={{ background: approval.status === "approved" ? "var(--success-light)" : "var(--error-light)", color: approval.status === "approved" ? "var(--success)" : "var(--error)" }}>
                        {approval.status.toUpperCase()}
                      </span>
                    </div>
                    <div style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
                      <strong>Rationale:</strong> {approval.decision_reason || "No explanation provided."}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                      Decided at: {approval.decided_at ? new Date(approval.decided_at).toLocaleTimeString() : "N/A"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* M3 Investigation Report Panel */}
          {investigationLoading ? (
            <div className="card" data-testid="investigation-loading">
              <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>💡 Investigation & Root Cause</h2>
              <div style={{ padding: "2rem", textAlign: "center" }}>
                <div className="spin-indicator" style={{ display: "inline-block", width: "30px", height: "30px", border: "3px solid var(--border-color)", borderTopColor: "var(--primary)", borderRadius: "50%", animation: "spin 1s linear infinite" }}></div>
                <p style={{ marginTop: "1rem", color: "var(--text-muted)" }}>Loading investigation report...</p>
              </div>
            </div>
          ) : investigationStatus === 404 ? (
            <div className="card" data-testid="investigation-not-found">
              <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>💡 Investigation & Root Cause</h2>
              <div style={{ padding: "1.5rem 1rem", border: "1px dashed var(--border-color)", borderRadius: "6px", textAlign: "center", color: "var(--text-muted)" }}>
                <p>No active investigation report.</p>
                <p style={{ fontSize: "0.8rem", marginTop: "0.25rem" }}>
                  Start the diagnosing pipeline to formulate hypotheses and map the root cause.
                </p>
              </div>
            </div>
          ) : investigationError ? (
            <div className="card" data-testid="investigation-error">
              <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>💡 Investigation & Root Cause</h2>
              <div role="alert" style={{ background: "#1e131d", color: "#fca5a5", border: "1px solid rgba(239, 68, 68, 0.4)", padding: "1rem", borderRadius: "8px" }}>
                <p><strong>⚠️ Error loading investigation report:</strong> {investigationError}</p>
              </div>
            </div>
          ) : investigation ? (
            <div data-testid="investigation-report-panel" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
              {/* Status and Remediation Enable Gate Banner */}
              <div className="card" style={{ borderLeft: `4px solid ${investigation.status === "complete" ? "var(--success)" : "var(--warning)"}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
                  <h2 style={{ fontSize: "1.25rem" }}>💡 Root Cause Investigation</h2>
                  <span className={`badge ${investigation.status === "complete" ? "badge-sev3" : "badge-sev2"}`} style={{ background: investigation.status === "complete" ? "var(--success-light)" : "var(--warning-light)", color: investigation.status === "complete" ? "var(--success)" : "var(--warning)" }}>
                    Status: {investigation.status.toUpperCase().replace(/_/g, " ")}
                  </span>
                </div>
                <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
                  Gateway: <code>{investigation.gateway}</code> | Created: {new Date(investigation.created_at).toLocaleString()}
                </p>
                <div data-testid="remediation-status" style={{ marginTop: "0.75rem", padding: "0.5rem 0.75rem", background: "rgba(0,0,0,0.2)", borderRadius: "4px", fontSize: "0.9rem" }}>
                  <strong>Remediation Gate:</strong>{" "}
                  <span style={{ color: investigation.remediation_enabled ? "var(--success)" : "var(--error)", fontWeight: "bold" }}>
                    {investigation.remediation_enabled ? "Enabled (COMPLETE)" : "Disabled (INSUFFICIENT EVIDENCE)"}
                  </span>
                </div>
              </div>

              {/* Insufficient Evidence State Banner and Requested Actions */}
              {investigation.status === "insufficient_evidence" && (
                <div className="card" style={{ border: "2px solid var(--warning)", background: "rgba(245, 158, 11, 0.05)" }}>
                  <h3 style={{ color: "var(--warning)", marginBottom: "0.5rem", fontSize: "1.1rem" }}>⚠️ Safe Insufficient-Evidence State</h3>
                  <p style={{ fontSize: "0.9rem", color: "var(--text-main)", marginBottom: "0.75rem" }}>
                    Remediation has been disabled. The automated agent requires additional telemetry or documentation input to ground the root cause hypotheses.
                  </p>
                  <div>
                    <strong style={{ fontSize: "0.85rem", color: "var(--warning)" }}>Requested Evidence / Actions to Resolve Unknowns:</strong>
                    {investigation.unknowns && investigation.unknowns.length > 0 ? (
                      <ul style={{ margin: "0.25rem 0 0 0", paddingLeft: "1.25rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                        {investigation.unknowns.map((unk, idx) => (
                          <li key={idx} data-testid="requested-evidence-item">{unk}</li>
                        ))}
                      </ul>
                    ) : (
                      <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontStyle: "italic" }}>No specific unknowns listed. Verify telemetry sources and restart the diagnosing pipeline.</p>
                    )}
                  </div>
                </div>
              )}

              {/* Incident Summary Section */}
              {investigation.summary && (
                <div className="card">
                  <h3 style={{ fontSize: "1.1rem", marginBottom: "0.75rem" }}>📝 Executive Summary</h3>
                  <div style={{ fontSize: "0.95rem", lineHeight: "1.6" }}>
                    <p>
                      <strong>What Happened:</strong> {investigation.summary.what_happened}
                      {investigation.summary.citations.map((cit, idx) => (
                        <button
                          key={idx}
                          onClick={() => scrollToEvidence(cit.evidence_id)}
                          className="citation-link"
                          data-testid={`citation-link-${cit.evidence_id}`}
                          style={{
                            background: "var(--primary-light)",
                            border: "1px solid rgba(139, 92, 246, 0.3)",
                            borderRadius: "4px",
                            padding: "1px 5px",
                            fontSize: "0.75rem",
                            color: "var(--primary-hover)",
                            cursor: "pointer",
                            marginLeft: "4px"
                          }}
                          title={cit.note}
                        >
                          🔍 {cit.evidence_id}
                        </button>
                      ))}
                    </p>
                    <p style={{ marginTop: "0.5rem" }}>
                      <strong>Impact:</strong> {investigation.summary.impact}
                    </p>
                  </div>
                </div>
              )}

              {/* Code Mapping Section */}
              {investigation.code_mapping && (
                <div className="card" data-testid="code-mapping-section">
                  <h3 style={{ fontSize: "1.1rem", marginBottom: "0.75rem" }}>🛠️ Root Cause Code Mapping</h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                    <div>
                      <strong>Suspect Commit:</strong>{" "}
                      <code data-testid="code-mapping-commit" style={{ color: "var(--primary-hover)" }}>{investigation.code_mapping.suspect_commit}</code>
                      {investigation.code_mapping.commit_citations.map((cit, idx) => (
                        <button
                          key={idx}
                          onClick={() => scrollToEvidence(cit.evidence_id)}
                          className="citation-link"
                          data-testid={`citation-link-${cit.evidence_id}`}
                          style={{
                            background: "var(--primary-light)",
                            border: "1px solid rgba(139, 92, 246, 0.3)",
                            borderRadius: "4px",
                            padding: "1px 5px",
                            fontSize: "0.75rem",
                            color: "var(--primary-hover)",
                            cursor: "pointer",
                            marginLeft: "4px"
                          }}
                          title={cit.note}
                        >
                          🔍 {cit.evidence_id}
                        </button>
                      ))}
                    </div>

                    <div>
                      <strong>Coverage Gap:</strong>{" "}
                      <span data-testid="code-mapping-gap" style={{ fontSize: "0.9rem" }}>{investigation.code_mapping.coverage_gap}</span>
                      {investigation.code_mapping.coverage_gap_citations.map((cit, idx) => (
                        <button
                          key={idx}
                          onClick={() => scrollToEvidence(cit.evidence_id)}
                          className="citation-link"
                          data-testid={`citation-link-${cit.evidence_id}`}
                          style={{
                            background: "var(--primary-light)",
                            border: "1px solid rgba(139, 92, 246, 0.3)",
                            borderRadius: "4px",
                            padding: "1px 5px",
                            fontSize: "0.75rem",
                            color: "var(--primary-hover)",
                            cursor: "pointer",
                            marginLeft: "4px"
                          }}
                          title={cit.note}
                        >
                          🔍 {cit.evidence_id}
                        </button>
                      ))}
                    </div>

                    <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "0.75rem" }}>
                      <strong>Affected Files:</strong>
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.25rem" }}>
                        {investigation.code_mapping.affected_files.map((file, idx) => (
                          <div key={idx} data-testid="code-mapping-file" style={{ padding: "0.5rem", background: "rgba(0,0,0,0.15)", border: "1px solid var(--border-color)", borderRadius: "6px" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.9rem", color: "#ffffff" }}>{file.path}</span>
                              <div>
                                {file.citations.map((cit, cIdx) => (
                                  <button
                                    key={cIdx}
                                    onClick={() => scrollToEvidence(cit.evidence_id)}
                                    className="citation-link"
                                    data-testid={`citation-link-${cit.evidence_id}`}
                                    style={{
                                      background: "var(--primary-light)",
                                      border: "1px solid rgba(139, 92, 246, 0.3)",
                                      borderRadius: "4px",
                                      padding: "1px 5px",
                                      fontSize: "0.75rem",
                                      color: "var(--primary-hover)",
                                      cursor: "pointer",
                                      marginLeft: "4px"
                                    }}
                                    title={cit.note}
                                  >
                                    🔍 {cit.evidence_id}
                                  </button>
                                ))}
                              </div>
                            </div>
                            <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                              Role: {file.role}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Ranked Hypotheses list */}
              {investigation.hypotheses && (
                <div className="card">
                  <h3 style={{ fontSize: "1.1rem", marginBottom: "0.75rem" }}>💡 Root Cause Hypotheses</h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                    {investigation.hypotheses.map((hyp) => (
                      <div
                        key={hyp.rank}
                        data-testid={`hypothesis-rank-${hyp.rank}`}
                        style={{
                          border: "1px solid var(--border-color)",
                          padding: "1rem",
                          borderRadius: "8px",
                          background: "rgba(255,255,255,0.01)"
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                          <span style={{ fontSize: "0.85rem", fontWeight: "700", textTransform: "uppercase", color: hyp.rank === 1 ? "var(--warning)" : "var(--text-muted)" }}>
                            Rank {hyp.rank} - {hyp.rank === 1 ? "Top Hypothesis" : "Alternative"}
                          </span>
                          <span style={{ fontSize: "0.85rem", color: hyp.confidence > 0.7 ? "var(--success)" : "var(--warning)", fontWeight: "600" }}>
                            Confidence: {Math.round(hyp.confidence * 100)}%
                          </span>
                        </div>

                        <p data-testid="hypothesis-statement" style={{ fontWeight: "600", fontSize: "0.95rem", marginBottom: "0.5rem" }}>{hyp.statement}</p>

                        {/* Rationale - concise narrative */}
                        <div style={{ background: "rgba(0,0,0,0.15)", padding: "0.5rem 0.75rem", borderRadius: "4px", fontSize: "0.85rem", marginBottom: "0.75rem" }}>
                          <strong>Concise Rationale:</strong> {hyp.rationale}
                        </div>

                        {/* Citations - Supporting / Contradicting */}
                        <div data-testid="hypothesis-supporting" style={{ fontSize: "0.85rem", marginBottom: "0.5rem" }}>
                          <span style={{ fontWeight: "600", color: "var(--success)" }}>Supporting:</span>
                          {hyp.supporting.length > 0 ? (
                            <ul style={{ margin: "0.25rem 0 0 0", paddingLeft: "1.25rem", color: "var(--text-muted)" }}>
                              {hyp.supporting.map((cit, idx) => (
                                <li key={idx}>
                                  {cit.note}
                                  <button
                                    onClick={() => scrollToEvidence(cit.evidence_id)}
                                    className="citation-link"
                                    data-testid={`citation-link-${cit.evidence_id}`}
                                    style={{
                                      background: "var(--primary-light)",
                                      border: "1px solid rgba(139, 92, 246, 0.3)",
                                      borderRadius: "4px",
                                      padding: "1px 5px",
                                      fontSize: "0.7rem",
                                      color: "var(--primary-hover)",
                                      cursor: "pointer",
                                      marginLeft: "4px"
                                    }}
                                  >
                                    🔍 {cit.evidence_id}
                                  </button>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <span style={{ color: "var(--text-muted)", marginLeft: "0.5rem" }}>None</span>
                          )}
                        </div>

                        <div data-testid="hypothesis-contradictions" style={{ fontSize: "0.85rem", marginBottom: "0.5rem" }}>
                          <span style={{ fontWeight: "600", color: "var(--error)" }}>Contradictions:</span>
                          {hyp.contradicting.length > 0 ? (
                            <ul style={{ margin: "0.25rem 0 0 0", paddingLeft: "1.25rem", color: "var(--text-muted)" }}>
                              {hyp.contradicting.map((cit, idx) => (
                                <li key={idx}>
                                  {cit.note}
                                  <button
                                    onClick={() => scrollToEvidence(cit.evidence_id)}
                                    className="citation-link"
                                    data-testid={`citation-link-${cit.evidence_id}`}
                                    style={{
                                      background: "var(--primary-light)",
                                      border: "1px solid rgba(139, 92, 246, 0.3)",
                                      borderRadius: "4px",
                                      padding: "1px 5px",
                                      fontSize: "0.7rem",
                                      color: "var(--primary-hover)",
                                      cursor: "pointer",
                                      marginLeft: "4px"
                                    }}
                                  >
                                    🔍 {cit.evidence_id}
                                  </button>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <span style={{ color: "var(--text-muted)", marginLeft: "0.5rem" }}>None</span>
                          )}
                        </div>

                        {/* Unknowns */}
                        <div data-testid="hypothesis-unknowns" style={{ borderTop: "1px dashed var(--border-color)", paddingTop: "0.5rem", marginTop: "0.5rem", fontSize: "0.85rem" }}>
                          <span style={{ color: "var(--warning)", fontWeight: "600" }}>Explicit Unknowns:</span>
                          <ul style={{ paddingLeft: "1.25rem", listStyleType: "square", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                            {hyp.unknowns.map((unk, idx) => (
                              <li key={idx}>{unk}</li>
                            ))}
                          </ul>
                        </div>

                        {/* Falsification tests */}
                        {hyp.falsification_tests && hyp.falsification_tests.length > 0 && (
                          <div data-testid="hypothesis-falsification" style={{ borderTop: "1px dashed var(--border-color)", paddingTop: "0.5rem", marginTop: "0.5rem" }}>
                            <span style={{ fontWeight: "600", fontSize: "0.85rem", color: "var(--primary-hover)" }}>Bounded Falsification Steps:</span>
                            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.25rem" }}>
                              {hyp.falsification_tests.map((test, idx) => (
                                <div key={idx} style={{ padding: "0.5rem", background: "rgba(0,0,0,0.2)", borderRadius: "4px" }}>
                                  <p style={{ fontSize: "0.85rem", fontWeight: "600", color: "var(--text-main)" }}>{test.description}</p>
                                  <ol style={{ fontSize: "0.8rem", paddingLeft: "1.25rem", margin: "0.25rem 0", color: "var(--text-muted)" }}>
                                    {test.steps.map((step, sIdx) => <li key={sIdx}>{step}</li>)}
                                  </ol>
                                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", fontSize: "0.75rem", marginTop: "0.25rem" }}>
                                    <span style={{ color: "var(--success)" }}><strong>If true:</strong> {test.expected_if_true}</span>
                                    <span style={{ color: "var(--error)" }}><strong>If false:</strong> {test.expected_if_false}</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Audit Log of Rejected Claims (Security / Citation check) */}
              {investigation.rejected_claims && investigation.rejected_claims.length > 0 && (
                <details className="card" style={{ cursor: "pointer", background: "rgba(0,0,0,0.1)" }}>
                  <summary style={{ fontSize: "0.95rem", fontWeight: "600", color: "var(--error)" }}>
                    🔒 Rejected Claims Audit Log ({investigation.rejected_claims.length})
                  </summary>
                  <div style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    {investigation.rejected_claims.map((claim, idx) => (
                      <div key={idx} style={{ padding: "0.5rem", border: "1px solid var(--error-light)", borderRadius: "4px", background: "var(--error-light)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", fontWeight: "bold" }}>
                          <span>Origin: {claim.origin}</span>
                          <span style={{ color: "var(--error)" }}>REJECTED</span>
                        </div>
                        <p style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}><strong>Statement:</strong> &ldquo;{claim.statement}&rdquo;</p>
                        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.25rem" }}><strong>Reason:</strong> {claim.reason}</p>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          ) : (
            <div className="card">
              <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>💡 Investigation & Root Cause</h2>
              <div style={{ padding: "1.5rem 1rem", border: "1px dashed var(--border-color)", borderRadius: "6px", textAlign: "center", color: "var(--text-muted)" }}>
                <p>Waiting for investigation data...</p>
              </div>
            </div>
          )}

          {/* Remediation Plans & Code Patches */}
          <div className="card">
            <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>🛠️ Remediation plans & patches</h2>
            {plansError && (
              <div role="alert" style={{ background: "#1e131d", color: "#fca5a5", border: "1px solid rgba(239, 68, 68, 0.4)", padding: "1rem", borderRadius: "8px", marginBottom: "1rem" }}>
                <strong>⚠️ Remediation Plans Fetch Error:</strong> {plansError}
              </div>
            )}
            {patchesError && (
              <div role="alert" style={{ background: "#1e131d", color: "#fca5a5", border: "1px solid rgba(239, 68, 68, 0.4)", padding: "1rem", borderRadius: "8px", marginBottom: "1rem" }}>
                <strong>⚠️ Patches Fetch Error:</strong> {patchesError}
              </div>
            )}
            {investigation?.status === "insufficient_evidence" ? (
              <div style={{ padding: "1.5rem 1rem", border: "1px dashed var(--border-color)", borderRadius: "6px", textAlign: "center", color: "var(--error)", fontSize: "0.9rem", background: "var(--error-light)" }}>
                <p><strong>Remediation Disabled:</strong> The investigation failed to find sufficient evidence to generate a safe remediation plan.</p>
              </div>
            ) : plans.length === 0 ? (
              <div style={{ padding: "1.5rem 1rem", border: "1px dashed var(--border-color)", borderRadius: "6px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.9rem" }}>
                <p>⚙️ Formulation phase: telemetry and logs are being analyzed by the AI agent to formulate hypotheses. Remediation plan will appear once hypotheses are ready.</p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                {plans.map((plan) => {
                  const matchingPatch = patches.find(p => p.plan_id === plan.id);
                  return (
                    <div key={plan.id} style={{ border: "1px solid var(--border-color)", padding: "1rem", borderRadius: "8px", background: "rgba(255,255,255,0.01)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem", marginBottom: "0.5rem" }}>
                        <h3 style={{ fontSize: "1rem", color: "var(--primary-hover)" }}>Remediation Proposal</h3>
                        <span className={`badge ${plan.risk_level === "low" ? "badge-sev3" : plan.risk_level === "medium" ? "badge-sev2" : "badge-sev1"}`}>
                          Risk: {plan.risk_level.toUpperCase()}
                        </span>
                      </div>
                      <p style={{ fontSize: "0.95rem", fontWeight: "600", marginBottom: "0.5rem" }}>{plan.summary}</p>
                      
                      <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "0.75rem" }}>
                        <strong>Bounds:</strong> max files changed: {plan.max_files_changed} | max lines changed: {plan.max_lines_changed}
                      </div>

                      {/* Display steps if any */}
                      {plan.steps.length > 0 && (
                        <div style={{ margin: "0.5rem 0", background: "rgba(0,0,0,0.1)", padding: "0.75rem", borderRadius: "4px" }}>
                          <span style={{ fontSize: "0.85rem", fontWeight: "700" }}>Implementation Steps:</span>
                          <ol style={{ paddingLeft: "1.25rem", fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                            {plan.steps.map((step, sIdx) => <li key={sIdx}>{step}</li>)}
                          </ol>
                        </div>
                      )}

                      {/* Patch Attempt File Diff section */}
                      {matchingPatch ? (
                        <div style={{ marginTop: "1rem" }}>
                          <h4 style={{ fontSize: "0.85rem", fontWeight: "700", marginBottom: "0.5rem", color: "var(--success)" }}>
                            Generated Diff Patch (Attempt #{matchingPatch.attempt})
                          </h4>
                          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>
                            Files Changed: {matchingPatch.files_changed} | Lines Changed: {matchingPatch.lines_changed}
                          </div>
                          {matchingPatch.diff ? (
                            renderDiff(matchingPatch.diff)
                          ) : (
                            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontStyle: "italic" }}>No diff text available for this patch attempt.</p>
                          )}
                        </div>
                      ) : (
                        <div style={{ marginTop: "1rem", border: "1px dashed var(--border-color)", padding: "0.75rem", borderRadius: "6px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                          Drafting patch attempt... Patch will generate once the agent enters the WAITING PATCH APPROVAL phase.
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>
      </div>
    </main>
  );
}
