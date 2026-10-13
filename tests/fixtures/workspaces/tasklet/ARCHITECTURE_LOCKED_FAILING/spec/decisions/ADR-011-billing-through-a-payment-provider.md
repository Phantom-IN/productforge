### ADR-011 — Billing through a payment provider
- Topic: other
- Context: Owners and admins manage subscriptions; we never store card data (R-011)
- Decision: Use a payment provider's hosted checkout and subscription webhooks; we store only the plan and status
- Alternatives: build card processing; invoices by hand; a reseller
- Reason: Card data never touches our system
- Trade-offs: Webhook handling must be idempotent
- Satisfies: R-011
- Status: accepted
