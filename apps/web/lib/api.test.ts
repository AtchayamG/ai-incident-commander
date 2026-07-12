import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildUrl,
  getHealthReady,
  listIncidents,
  cancelIncident,
  resetDemo,
  getIncidentEvidence,
  getIncidentTimeline,
  getIncidentHypotheses,
  getIncidentPlans,
  getIncidentPatches,
  getIncidentApprovals,
  getIncidentInvestigation,
  getIncidentVerifications,
} from "./api";

describe("buildUrl", () => {
  it("joins base and path", () => {
    expect(buildUrl("http://localhost:8000", "health/ready")).toBe(
      "http://localhost:8000/health/ready",
    );
  });

  it("tolerates trailing slash on base", () => {
    expect(buildUrl("http://localhost:8000/", "api/v1/incidents")).toBe(
      "http://localhost:8000/api/v1/incidents",
    );
  });

  it("appends defined query params only", () => {
    const url = buildUrl("http://localhost:8000", "api/v1/incidents", {
      service: "checkout-api",
      limit: 10,
      status: undefined,
    });
    expect(url).toBe("http://localhost:8000/api/v1/incidents?service=checkout-api&limit=10");
  });

  it("escapes path segments via encodeURIComponent usage upstream", () => {
    expect(buildUrl("http://localhost:8000", `api/v1/incidents/${encodeURIComponent("a/b")}`)).toContain(
      "a%2Fb",
    );
  });
});

describe("request handling", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns ok result with parsed data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ status: "ok", demo_mode: true, provider_mode: "simulated" }), { status: 200 })),
    );
    const result = await getHealthReady();
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.provider_mode).toBe("simulated");
    }
  });

  it("returns error result on HTTP failure without throwing", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("boom", { status: 500 })),
    );
    const result = await listIncidents();
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.status).toBe(500);
      expect(result.error).toBe("boom");
    }
  });

  it("returns error result on network failure without throwing", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("ECONNREFUSED");
      }),
    );
    const result = await getHealthReady();
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.status).toBeNull();
      expect(result.error).toContain("ECONNREFUSED");
    }
  });

  it("cancelIncident calls correct endpoint", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ id: "inc-1" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await cancelIncident("inc-1");
    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalled();
    const [url, init] = fetchMock.mock.calls[0] as any;
    expect(url).toContain("api/v1/incidents/inc-1/cancel");
    expect(init?.method).toBe("POST");
  });

  it("resetDemo calls endpoint with admin key header", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ status: "reset" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await resetDemo("key-123");
    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalled();
    const [url, init] = fetchMock.mock.calls[0] as any;
    expect(url).toContain("api/v1/incidents/reset-demo");
    expect(init?.method).toBe("POST");
    expect((init?.headers as Record<string, string>)?.["X-Demo-Admin-Key"]).toBe("key-123");
  });

  it("getIncidentEvidence fetches sub-resource", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await getIncidentEvidence("inc-1");
    expect(result.ok).toBe(true);
    const [url] = fetchMock.mock.calls[0] as any;
    expect(url).toContain("api/v1/incidents/inc-1/evidence");
  });

  it("getIncidentTimeline fetches sub-resource", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await getIncidentTimeline("inc-1");
    expect(result.ok).toBe(true);
    const [url] = fetchMock.mock.calls[0] as any;
    expect(url).toContain("api/v1/incidents/inc-1/timeline");
  });

  it("getIncidentHypotheses fetches sub-resource", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await getIncidentHypotheses("inc-1");
    expect(result.ok).toBe(true);
    const [url] = fetchMock.mock.calls[0] as any;
    expect(url).toContain("api/v1/incidents/inc-1/hypotheses");
  });

  it("getIncidentPlans fetches sub-resource", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await getIncidentPlans("inc-1");
    expect(result.ok).toBe(true);
    const [url] = fetchMock.mock.calls[0] as any;
    expect(url).toContain("api/v1/incidents/inc-1/remediation-plan");
  });

  it("getIncidentPatches fetches sub-resource", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await getIncidentPatches("inc-1");
    expect(result.ok).toBe(true);
    const [url] = fetchMock.mock.calls[0] as any;
    expect(url).toContain("api/v1/incidents/inc-1/patches");
  });

  it("getIncidentApprovals fetches sub-resource", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await getIncidentApprovals("inc-1");
    expect(result.ok).toBe(true);
    const [url] = fetchMock.mock.calls[0] as any;
    expect(url).toContain("api/v1/incidents/inc-1/approvals");
  });

  it("getIncidentInvestigation fetches investigation report", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ id: "inv-1" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await getIncidentInvestigation("inc-1");
    expect(result.ok).toBe(true);
    const [url] = fetchMock.mock.calls[0] as any;
    expect(url).toContain("api/v1/incidents/inc-1/investigation");
  });

  it("getIncidentVerifications fetches authoritative incident verification runs", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify([{ id: "vr-1", passed: true, checks: [] }]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await getIncidentVerifications("inc/1");
    expect(result.ok).toBe(true);
    const [url] = fetchMock.mock.calls[0] as any;
    expect(url).toContain("api/v1/incidents/inc%2F1/verifications");
  });
});

describe('API Contract - decideApproval', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('should format approval decision request according to contracts', async () => {
    const mockFetch = vi.fn(async () => new Response(JSON.stringify({ id: 'app-1', status: 'approved' }), { status: 200 }));
    vi.stubGlobal('fetch', mockFetch);
    const { decideApproval } = await import('./api');

    const res = await decideApproval('app-1', {
      decision: 'approved',
      reason: 'Looks good',
      artifact_version: 1,
    });

    expect(mockFetch).toHaveBeenCalled();
    const [url, init] = mockFetch.mock.calls[0] as any;
    expect(url).toContain('/api/v1/approvals/app-1/decision');
    expect(init.method).toBe('POST');
    expect(init.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(init.body)).toEqual({
      decision: 'approved',
      reason: 'Looks good',
      artifact_version: 1,
    });
    
    expect(res.ok).toBe(true);
    if (res.ok) {
      expect(res.data.status).toBe('approved');
    }
  });

  it('should gracefully handle HTTP 409 stale errors', async () => {
    const mockFetch = vi.fn(async () => new Response(JSON.stringify({ detail: 'Approval request is stale or already consumed.' }), { status: 409 }));
    vi.stubGlobal('fetch', mockFetch);
    const { decideApproval } = await import('./api');

    const res = await decideApproval('app-1', {
      decision: 'approved',
      reason: 'Conflict',
    });

    expect(res.ok).toBe(false);
    if (!res.ok) {
      expect(res.status).toBe(409);
      // The API client stringifies the error object from JSON bodies if not ok
      expect(res.error).toContain('Approval request is stale or already consumed.');
    }
  });
});

describe('API Contract - bounded remediation artifact', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('requests the immutable artifact endpoint without synthesizing plan fields', async () => {
    const artifact = {
      id: 'plan-artifact-1',
      artifact_hash: 'sha256:abc',
      verification_commands: ['pnpm test'],
      rollback: 'Restore the prior checkout implementation.',
    };
    const mockFetch = vi.fn(async () => new Response(JSON.stringify(artifact), { status: 200 }));
    vi.stubGlobal('fetch', mockFetch);
    const { getIncidentPlanArtifact } = await import('./api');

    const result = await getIncidentPlanArtifact('inc/demo');

    const [url] = mockFetch.mock.calls[0] as any;
    expect(url).toContain(
      '/api/v1/incidents/inc%2Fdemo/remediation-plan/artifact',
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.artifact_hash).toBe('sha256:abc');
      expect(result.data.verification_commands).toEqual(['pnpm test']);
    }
  });
});
