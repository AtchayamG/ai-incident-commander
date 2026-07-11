/**
 * Typed API client for the Incident Commander backend.
 *
 * All response shapes come from @incident-commander/contracts. The client
 * never throws on transport errors; callers receive a discriminated result
 * so the UI can degrade gracefully when the API is down.
 */

import type {
  ApprovalDecisionIn,
  ApprovalRequest,
  HealthDependencies,
  HealthReady,
  Incident,
  IncidentCreate,
  IncidentList,
} from "@incident-commander/contracts";

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; status: number | null; error: string };

export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

export function buildUrl(
  base: string,
  path: string,
  params?: Record<string, string | number | undefined>,
): string {
  const url = new URL(path, base.endsWith("/") ? base : `${base}/`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

async function request<T>(
  path: string,
  init?: RequestInit,
  params?: Record<string, string | number | undefined>,
): Promise<ApiResult<T>> {
  const url = buildUrl(apiBaseUrl(), path, params);
  try {
    const response = await fetch(url, { cache: "no-store", ...init });
    if (!response.ok) {
      const body = await response.text();
      return { ok: false, status: response.status, error: body || response.statusText };
    }
    const data = (await response.json()) as T;
    return { ok: true, data };
  } catch (error) {
    return { ok: false, status: null, error: error instanceof Error ? error.message : "fetch failed" };
  }
}

export function getHealthReady(): Promise<ApiResult<HealthReady>> {
  return request<HealthReady>("health/ready");
}

export function getHealthDependencies(): Promise<ApiResult<HealthDependencies>> {
  return request<HealthDependencies>("health/dependencies");
}

export function listIncidents(params?: {
  status?: string;
  severity?: string;
  service?: string;
  limit?: number;
}): Promise<ApiResult<IncidentList>> {
  return request<IncidentList>("api/v1/incidents", undefined, params);
}

export function getIncident(incidentId: string): Promise<ApiResult<Incident>> {
  return request<Incident>(`api/v1/incidents/${encodeURIComponent(incidentId)}`);
}

export function createIncident(body: IncidentCreate): Promise<ApiResult<Incident>> {
  return request<Incident>("api/v1/incidents", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function startIncident(incidentId: string): Promise<ApiResult<Incident>> {
  return request<Incident>(`api/v1/incidents/${encodeURIComponent(incidentId)}/start`, {
    method: "POST",
  });
}

export function decideApproval(
  approvalId: string,
  body: ApprovalDecisionIn,
): Promise<ApiResult<ApprovalRequest>> {
  return request<ApprovalRequest>(
    `api/v1/approvals/${encodeURIComponent(approvalId)}/decision`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}
