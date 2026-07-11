import { afterEach, describe, expect, it, vi } from "vitest";

import { buildUrl, getHealthReady, listIncidents } from "./api";

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
});
