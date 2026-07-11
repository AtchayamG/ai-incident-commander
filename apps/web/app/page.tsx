"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import type {
  Incident,
  Severity,
  Environment,
  WorkflowState,
  IncidentCreate,
  HealthReady,
} from "@incident-commander/contracts";
import {
  listIncidents,
  createIncident,
  resetDemo,
  getHealthReady,
} from "@/lib/api";

const SERVICES = ["checkout-api", "payment-gateway", "auth-service", "notification-worker"] as const;
const SEVERITIES: Severity[] = ["SEV1", "SEV2", "SEV3", "SEV4"];
const ENVIRONMENTS: Environment[] = ["production", "staging", "development", "demo"];
const STATUS_OPTIONS: WorkflowState[] = [
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
];

export default function DashboardPage() {
  const router = useRouter();

  // API Status & List
  const [health, setHealth] = useState<HealthReady | null>(null);
  const [apiDown, setApiDown] = useState(false);
  const [loading, setLoading] = useState(true);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters (State Persisted)
  const [filterService, setFilterService] = useState<string>("");
  const [filterSeverity, setFilterSeverity] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");

  // Manual Intake Modal Form State
  const [showModal, setShowModal] = useState(false);
  const [formTitle, setFormTitle] = useState("");
  const [formService, setFormService] = useState<string>(SERVICES[0]);
  const [formEnvironment, setFormEnvironment] = useState<Environment>("production");
  const [formSeverity, setFormSeverity] = useState<Severity>("SEV2");
  const [formSummary, setFormSummary] = useState("");
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Demo Admin Key
  const [adminKey, setAdminKey] = useState("demo-admin-key");
  const [isResetting, setIsResetting] = useState(false);

  // Load Filters from LocalStorage on Mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem("incident_commander_filters");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.service) setFilterService(parsed.service);
        if (parsed.severity) setFilterSeverity(parsed.severity);
        if (parsed.status) setFilterStatus(parsed.status);
      }
    } catch (e) {
      console.error("Failed to load saved filters", e);
    }
  }, []);

  // Save Filters to LocalStorage when they change
  useEffect(() => {
    try {
      const filters = {
        service: filterService,
        severity: filterSeverity,
        status: filterStatus,
      };
      localStorage.setItem("incident_commander_filters", JSON.stringify(filters));
    } catch (e) {
      console.error("Failed to save filters", e);
    }
  }, [filterService, filterSeverity, filterStatus]);

  // Fetch initial data
  const fetchData = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    
    // Check Health
    const healthRes = await getHealthReady();
    if (!healthRes.ok) {
      setApiDown(true);
      setLoading(false);
      return;
    }
    setHealth(healthRes.data);
    setApiDown(false);

    // List Incidents
    const incidentsRes = await listIncidents({
      service: filterService || undefined,
      severity: filterSeverity || undefined,
      status: filterStatus || undefined,
    });

    if (!incidentsRes.ok) {
      setErrorMsg(`Failed to load incidents: ${incidentsRes.error}`);
    } else {
      setIncidents(incidentsRes.data.items);
    }
    setLoading(false);
  }, [filterService, filterSeverity, filterStatus]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle manual incident creation
  const handleCreateIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormErrors({});
    
    // Validation
    const errors: Record<string, string> = {};
    if (!formTitle.trim()) {
      errors.title = "Incident title is required.";
    }
    if (!formSummary.trim()) {
      errors.summary = "A brief summary of the issue is required.";
    }

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    setIsSubmitting(true);
    const body: IncidentCreate = {
      title: formTitle.trim(),
      service: formService,
      environment: formEnvironment,
      severity: formSeverity,
      summary: formSummary.trim(),
    };

    const res = await createIncident(body);
    setIsSubmitting(false);

    if (res.ok) {
      // Clear and Close Modal
      setFormTitle("");
      setFormSummary("");
      setShowModal(false);
      // Reload Data
      fetchData();
      // Redirect to the newly created incident detail page
      router.push(`/incidents/${res.data.id}`);
    } else {
      setFormErrors({ submit: res.error });
    }
  };

  // Reset Demo to Golden Incident state
  const handleResetDemo = async () => {
    if (!confirm("Are you sure you want to reset the demo store? This will seed the Golden Incident state (inc-demo-0001).")) {
      return;
    }
    setIsResetting(true);
    const res = await resetDemo(adminKey);
    setIsResetting(false);
    
    if (res.ok) {
      fetchData();
      alert("Demo reset successfully! Seeded incident inc-demo-0001.");
      router.push("/incidents/inc-demo-0001");
    } else {
      alert(`Reset failed: ${res.error}`);
    }
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

  const getStatusSymbol = (state: WorkflowState) => {
    switch (state) {
      case "RECEIVED": return "📥";
      case "NORMALIZING": return "⚙️";
      case "COLLECTING_EVIDENCE": return "🔍";
      case "EVIDENCE_READY": return "📊";
      case "NEEDS_INPUT": return "⚠️";
      case "INVESTIGATING": return "🧠";
      case "HYPOTHESES_READY": return "💡";
      case "PLANNING_REMEDIATION": return "🛠️";
      case "PLAN_READY": return "📋";
      case "WAITING_PATCH_APPROVAL": return "⏱️";
      case "PATCHING": return "⚡";
      case "VERIFYING": return "🧪";
      case "REVIEW_READY": return "👀";
      case "WAITING_PR_APPROVAL": return "⌛";
      case "PR_READY": return "✅";
      case "CLOSED": return "🔒";
      case "CANCELLED": return "🚫";
      default: return "●";
    }
  };

  return (
    <main className="container">
      {/* Value Proposition Header */}
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "2.5rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>
            <span className="gradient-text">Incident Commander AI</span>
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "1.1rem", maxWidth: "700px" }}>
            The autonomous incident commander for engineering teams.
            Collects telemetry evidence, formulates hypotheses, proposes bounded remediation patches, and executes them with human-in-the-loop approvals.
          </p>
        </div>

        {/* Demo Mode / Value State Info */}
        <div className="card" style={{ maxWidth: "380px", padding: "1rem", background: "rgba(21, 29, 48, 0.6)" }}>
          <h2 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>🚀 Golden Incident Demo</h2>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "0.75rem" }}>
            Pre-configured environment with simulated telemetry, source code analysis, and approval processes.
          </p>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button 
              className="btn btn-primary" 
              style={{ padding: "0.5rem 0.75rem", fontSize: "0.85rem" }}
              onClick={() => router.push("/incidents/inc-demo-0001")}
            >
              View inc-demo-0001
            </button>
            <button 
              className="btn btn-secondary" 
              style={{ padding: "0.5rem 0.75rem", fontSize: "0.85rem" }}
              onClick={handleResetDemo}
              disabled={isResetting}
            >
              {isResetting ? "Resetting..." : "Reset Demo Store"}
            </button>
          </div>
        </div>
      </header>

      {/* Main Grid: API status, Filters, Incidents Table */}
      <div className="grid grid-main-detail">
        {/* Left Side: Incidents & Controls */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Controls: New Incident & Filters */}
          <div className="card" style={{ padding: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem", marginBottom: "1rem" }}>
              <h2 style={{ fontSize: "1.25rem" }}>Incident Management</h2>
              <button 
                onClick={() => setShowModal(true)} 
                className="btn btn-primary"
                aria-haspopup="dialog"
                aria-expanded={showModal}
              >
                ➕ Intake New Incident
              </button>
            </div>

            {/* Filter controls */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem", borderTop: "1px solid var(--border-color)", paddingTop: "1rem" }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="filter-service" className="form-label">Filter by Service</label>
                <select 
                  id="filter-service" 
                  className="form-select" 
                  value={filterService}
                  onChange={(e) => setFilterService(e.target.value)}
                >
                  <option value="">All Services</option>
                  {SERVICES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="filter-severity" className="form-label">Filter by Severity</label>
                <select 
                  id="filter-severity" 
                  className="form-select" 
                  value={filterSeverity}
                  onChange={(e) => setFilterSeverity(e.target.value)}
                >
                  <option value="">All Severities</option>
                  {SEVERITIES.map(s => <option key={s} value={s}>{getSeverityLabel(s)}</option>)}
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="filter-status" className="form-label">Filter by Status</label>
                <select 
                  id="filter-status" 
                  className="form-select" 
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                >
                  <option value="">All Statuses</option>
                  {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                </select>
              </div>
            </div>
          </div>

          {/* Incidents List Container */}
          <div className="card">
            <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>Active & Past Incidents</h2>

            {apiDown ? (
              <div role="alert" style={{ background: "var(--error-light)", color: "var(--error)", border: "1px solid var(--error)", borderRadius: "6px", padding: "1.5rem", textAlign: "center" }}>
                <h3 style={{ marginBottom: "0.5rem" }}>⚠️ Backend API Connection Offline</h3>
                <p style={{ fontSize: "0.95rem", marginBottom: "1rem" }}>
                  Unable to establish connection to the Incident Commander backend service at <code>{process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}</code>.
                </p>
                <button className="btn btn-secondary" onClick={fetchData}>
                  🔄 Retry Connection
                </button>
              </div>
            ) : loading ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                {[1, 2, 3].map(i => (
                  <div key={i} className="card" style={{ height: "70px", background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-color)", display: "flex", alignItems: "center", padding: "1rem", animation: "pulse 1.5s infinite" }}>
                    <div style={{ width: "80px", height: "16px", background: "var(--border-color)", borderRadius: "4px", marginRight: "1rem" }}></div>
                    <div style={{ flex: 1, height: "16px", background: "var(--border-color)", borderRadius: "4px" }}></div>
                  </div>
                ))}
              </div>
            ) : errorMsg ? (
              <div role="alert" style={{ color: "var(--error)", background: "var(--error-light)", padding: "1rem", borderRadius: "6px", border: "1px solid var(--error)" }}>
                {errorMsg}
              </div>
            ) : incidents.length === 0 ? (
              <div style={{ textAlign: "center", padding: "3rem 1.5rem", color: "var(--text-muted)" }}>
                <p style={{ fontSize: "1.1rem", marginBottom: "1rem" }}>No incidents match the active filters.</p>
                <button 
                  className="btn btn-secondary" 
                  onClick={() => {
                    setFilterService("");
                    setFilterSeverity("");
                    setFilterStatus("");
                  }}
                >
                  Clear Filters
                </button>
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-color)", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                      <th style={{ textAlign: "left", padding: "0.75rem 0.5rem" }}>ID</th>
                      <th style={{ textAlign: "left", padding: "0.75rem 0.5rem" }}>Incident Title</th>
                      <th style={{ textAlign: "left", padding: "0.75rem 0.5rem" }}>Service</th>
                      <th style={{ textAlign: "left", padding: "0.75rem 0.5rem" }}>Severity</th>
                      <th style={{ textAlign: "left", padding: "0.75rem 0.5rem" }}>Workflow State</th>
                    </tr>
                  </thead>
                  <tbody>
                    {incidents.map((inc) => (
                      <tr 
                        key={inc.id} 
                        onClick={() => router.push(`/incidents/${inc.id}`)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            router.push(`/incidents/${inc.id}`);
                          }
                        }}
                        tabIndex={0}
                        style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", cursor: "pointer", transition: "background 0.2s" }}
                        className="incident-row"
                        aria-label={`Incident ${inc.id}: ${inc.title}, Service: ${inc.service}, Severity: ${inc.severity}, State: ${inc.state}`}
                      >
                        <td style={{ padding: "1rem 0.5rem", fontWeight: "700" }}>{inc.id}</td>
                        <td style={{ padding: "1rem 0.5rem" }}>
                          <div style={{ fontWeight: "600" }}>{inc.title}</div>
                          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: "300px" }}>{inc.summary}</div>
                        </td>
                        <td style={{ padding: "1rem 0.5rem" }}>
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}>{inc.service}</span>
                        </td>
                        <td style={{ padding: "1rem 0.5rem" }}>
                          <span className={`badge badge-${inc.severity.toLowerCase()}`}>
                            {getSeverityLabel(inc.severity)}
                          </span>
                        </td>
                        <td style={{ padding: "1rem 0.5rem" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.9rem" }}>
                            <span>{getStatusSymbol(inc.state)}</span>
                            <span style={{ fontWeight: "600" }}>{inc.state.replace(/_/g, " ")}</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Health check and System settings */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Health check card */}
          <div className="card">
            <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>System Health Status</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-color)", paddingBottom: "0.5rem" }}>
                <span style={{ color: "var(--text-muted)" }}>API Connection</span>
                <span style={{ color: apiDown ? "var(--error)" : "var(--success)", fontWeight: "bold" }}>
                  {apiDown ? "● OFFLINE" : "● ONLINE"}
                </span>
              </div>
              {health && (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-color)", paddingBottom: "0.5rem" }}>
                    <span style={{ color: "var(--text-muted)" }}>Demo Mode</span>
                    <span style={{ fontWeight: "bold" }}>{health.demo_mode ? "Enabled" : "Disabled"}</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-color)", paddingBottom: "0.5rem" }}>
                    <span style={{ color: "var(--text-muted)" }}>Provider Mode</span>
                    <span style={{ fontWeight: "bold", textTransform: "uppercase" }}>{health.provider_mode}</span>
                  </div>
                </>
              )}
            </div>

            <div style={{ marginTop: "1.5rem" }}>
              <h3 style={{ fontSize: "0.95rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>⚙️ Demo Admin Controls</h3>
              <div className="form-group">
                <label htmlFor="admin-key" className="form-label">X-Demo-Admin-Key</label>
                <input 
                  id="admin-key" 
                  type="password" 
                  className="form-input" 
                  value={adminKey} 
                  onChange={(e) => setAdminKey(e.target.value)} 
                />
              </div>
            </div>
          </div>

          {/* Quick-Start Value proposition documentation panel */}
          <div className="card" style={{ borderLeft: "4px solid var(--primary)" }}>
            <h2 style={{ fontSize: "1.1rem", marginBottom: "0.75rem" }}>Workflow Mechanics</h2>
            <ol style={{ paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: "0.5rem", fontSize: "0.9rem", color: "var(--text-muted)" }}>
              <li><strong>Intake</strong>: Incidents are created manually or via simulated monitoring signals.</li>
              <li><strong>Telemetry Collection</strong>: Telemetry is gathered and processed by the system.</li>
              <li><strong>Hypothesis Generation</strong>: AI agent formulates potential causes.</li>
              <li><strong>Remediation Plan</strong>: Detailed patch is generated.</li>
              <li><strong>Human Approval Gate</strong>: Engineers review the patch and approve or reject it.</li>
              <li><strong>Verification</strong>: Tests run to guarantee correctness before closing.</li>
            </ol>
          </div>
        </div>
      </div>

      {/* Manual Intake Modal */}
      {showModal && (
        <div 
          className="modal-overlay" 
          role="dialog" 
          aria-labelledby="modal-title" 
          aria-modal="true"
          style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.75)", display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1000, padding: "1rem" }}
        >
          <div 
            className="card" 
            style={{ width: "100%", maxWidth: "600px", maxHeight: "90vh", overflowY: "auto", border: "1px solid var(--primary)" }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
              <h2 id="modal-title" style={{ fontSize: "1.5rem" }}>Manual Incident Intake</h2>
              <button 
                onClick={() => setShowModal(false)}
                className="btn btn-secondary"
                style={{ padding: "0.25rem 0.5rem" }}
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateIncident}>
              {formErrors.submit && (
                <div role="alert" style={{ background: "var(--error-light)", color: "var(--error)", border: "1px solid var(--error)", padding: "0.75rem", borderRadius: "4px", marginBottom: "1rem" }}>
                  {formErrors.submit}
                </div>
              )}

              <div className="form-group">
                <label htmlFor="form-title" className="form-label">Incident Title <span style={{ color: "var(--error)" }}>*</span></label>
                <input 
                  id="form-title" 
                  type="text" 
                  className="form-input" 
                  placeholder="e.g. Memory leak in auth router"
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  aria-invalid={!!formErrors.title}
                  aria-describedby={formErrors.title ? "title-error" : undefined}
                />
                {formErrors.title && (
                  <span id="title-error" role="alert" style={{ color: "var(--error)", fontSize: "0.85rem" }}>
                    {formErrors.title}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2" style={{ gap: "1rem" }}>
                <div className="form-group">
                  <label htmlFor="form-service" className="form-label">Affected Service</label>
                  <select 
                    id="form-service" 
                    className="form-select"
                    value={formService}
                    onChange={(e) => setFormService(e.target.value)}
                  >
                    {SERVICES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="form-environment" className="form-label">Environment</label>
                  <select 
                    id="form-environment" 
                    className="form-select"
                    value={formEnvironment}
                    onChange={(e) => setFormEnvironment(e.target.value as Environment)}
                  >
                    {ENVIRONMENTS.map(env => <option key={env} value={env}>{env}</option>)}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="form-severity" className="form-label">Severity Level</label>
                <select 
                  id="form-severity" 
                  className="form-select"
                  value={formSeverity}
                  onChange={(e) => setFormSeverity(e.target.value as Severity)}
                >
                  {SEVERITIES.map(sev => <option key={sev} value={sev}>{getSeverityLabel(sev)}</option>)}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="form-summary" className="form-label">Incident Summary <span style={{ color: "var(--error)" }}>*</span></label>
                <textarea 
                  id="form-summary" 
                  className="form-input" 
                  rows={4}
                  placeholder="Provide a detailed description of the incident symptoms, logs, or metrics observed..."
                  value={formSummary}
                  onChange={(e) => setFormSummary(e.target.value)}
                  aria-invalid={!!formErrors.summary}
                  aria-describedby={formErrors.summary ? "summary-error" : undefined}
                />
                {formErrors.summary && (
                  <span id="summary-error" role="alert" style={{ color: "var(--error)", fontSize: "0.85rem" }}>
                    {formErrors.summary}
                  </span>
                )}
              </div>

              {/* Simulated Provider Notification Badge */}
              <div style={{ background: "var(--info-light)", border: "1px solid rgba(59,130,246,0.3)", borderRadius: "6px", padding: "0.75rem", marginBottom: "1.5rem", fontSize: "0.85rem", display: "flex", gap: "0.5rem" }}>
                <span>💡</span>
                <p style={{ color: "var(--text-main)" }}>
                  <strong>Demo Mode Indicator:</strong> Creating this incident manually triggers the simulated agent pipeline. Telemetry signals and hypotheses will generate automatically.
                </p>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "1rem" }}>
                <button 
                  type="button" 
                  onClick={() => setShowModal(false)} 
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="btn btn-primary"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Creating..." : "Intake Incident"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
