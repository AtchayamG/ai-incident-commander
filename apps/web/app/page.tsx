import { isTerminalState } from "@incident-commander/contracts";

import { getHealthReady, listIncidents } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const [health, incidents] = await Promise.all([getHealthReady(), listIncidents()]);

  return (
    <main style={{ padding: "2rem", fontFamily: "system-ui, sans-serif", maxWidth: 960 }}>
      <h1>Incident Commander AI</h1>
      <p>M0 foundation — deterministic demo mode, no external credentials required.</p>

      <section aria-label="API status">
        <h2>API status</h2>
        {health.ok ? (
          <p>
            API reachable — mode: <strong>{health.data.provider_mode}</strong>
            {health.data.demo_mode ? " (demo)" : ""}
          </p>
        ) : (
          <p role="alert">
            API unreachable ({health.error}). Start it with <code>make dev-api</code>.
          </p>
        )}
      </section>

      <section aria-label="Incidents">
        <h2>Incidents</h2>
        {!incidents.ok ? (
          <p>No incident data available.</p>
        ) : incidents.data.items.length === 0 ? (
          <p>No incidents yet.</p>
        ) : (
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: "0.5rem" }}>ID</th>
                <th style={{ textAlign: "left", padding: "0.5rem" }}>Title</th>
                <th style={{ textAlign: "left", padding: "0.5rem" }}>Service</th>
                <th style={{ textAlign: "left", padding: "0.5rem" }}>Severity</th>
                <th style={{ textAlign: "left", padding: "0.5rem" }}>State</th>
              </tr>
            </thead>
            <tbody>
              {incidents.data.items.map((incident) => (
                <tr key={incident.id}>
                  <td style={{ padding: "0.5rem" }}>{incident.id}</td>
                  <td style={{ padding: "0.5rem" }}>{incident.title}</td>
                  <td style={{ padding: "0.5rem" }}>{incident.service}</td>
                  <td style={{ padding: "0.5rem" }}>{incident.severity}</td>
                  <td style={{ padding: "0.5rem" }}>
                    {incident.state}
                    {isTerminalState(incident.state) ? " (terminal)" : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}
