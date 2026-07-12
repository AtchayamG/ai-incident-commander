// [SIMULATED FIXTURE] checkout-api test suite snapshot at version 2026.07.13.4.
// Every case constructs a session WITH a discount; no test exercises a
// session without one. This is the coverage gap the golden incident exposes.

import { applyDiscount, processCheckout } from "./checkout";

describe("applyDiscount", () => {
  it("applies SUMMER10 to the cart total", () => {
    const total = applyDiscount({
      id: "sess-1",
      cartTotal: 100,
      discount: { code: "SUMMER10", percent: 10 },
    });
    expect(total).toBe(90);
  });

  it("applies VIP20 to the cart total", () => {
    const total = applyDiscount({
      id: "sess-2",
      cartTotal: 200,
      discount: { code: "VIP20", percent: 20 },
    });
    expect(total).toBe(160);
  });

  it("ignores unknown discount codes", () => {
    const total = applyDiscount({
      id: "sess-3",
      cartTotal: 50,
      discount: { code: "NOPE", percent: 0 },
    });
    expect(total).toBe(50);
  });
});

describe("processCheckout", () => {
  it("returns the discounted total", () => {
    const result = processCheckout({
      id: "sess-4",
      cartTotal: 100,
      discount: { code: "SUMMER10", percent: 10 },
    });
    expect(result.total).toBe(90);
  });
});
