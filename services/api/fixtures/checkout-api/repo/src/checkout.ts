// [SIMULATED FIXTURE] checkout-api source snapshot at deployed version 2026.07.13.4.
// Demo fixture data for Incident Commander; this file is never executed.

export interface Discount {
  code: string;
  percent: number;
}

export interface CheckoutSession {
  id: string;
  cartTotal: number;
  discount?: Discount;
}

const DISCOUNTS: Record<string, number> = {
  SUMMER10: 10,
  VIP20: 20,
};

export function applyDiscount(session: CheckoutSession): number {
  // Regression introduced by commit c7f2e9a ("refactor: simplify discount
  // code lookup"). The safe optional access used to be:
  //   const code = session.discount?.code ?? null;
  // Direct property access throws a TypeError for sessions without a
  // discount, which surfaces as HTTP 500 on POST /v1/checkout.
  const code = session.discount.code;
  if (code == null) {
    return session.cartTotal;
  }
  const percent = DISCOUNTS[code] ?? 0;
  return session.cartTotal * (1 - percent / 100);
}

export function processCheckout(session: CheckoutSession): { total: number } {
  const total = applyDiscount(session);
  return { total };
}
