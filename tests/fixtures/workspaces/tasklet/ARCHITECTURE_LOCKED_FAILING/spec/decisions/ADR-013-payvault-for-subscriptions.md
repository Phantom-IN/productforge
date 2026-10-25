### ADR-013 — Payvault for subscriptions
- Topic: vendor
- Context: Owners manage subscriptions and we never store card data (R-011, ADR-011)
- Decision: Use Payvault (https://payvault.example) hosted checkout and subscription webhooks. Pricing: a percentage per successful charge, no monthly fee. Sandbox: test mode keys and test card numbers. Webhooks: every delivery is verified with the HMAC signature header and the endpoint secret before it is processed. Fallback: Stripe-compatible checkout behind the same billing module
- Alternatives: A second hosted payment provider; invoicing by bank transfer
- Reason: Hosted checkout keeps card data out of our systems
- Trade-offs: Fees scale with revenue; webhook handling must be idempotent
- Satisfies: R-011
- Status: accepted
