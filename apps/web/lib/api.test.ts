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
});

