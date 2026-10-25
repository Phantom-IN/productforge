<!--
base: ARCHITECTURE_LOCKED
target: spec/decisions/ADR-011-billing-through-a-payment-provider.md
mode: replace ADR-011
expect: REQUIREMENT_UNADDRESSED
-->
### ADR-011 — Billing through a payment provider
- Topic: other
- Context: Owners and admins manage subscriptions; we never store card data (R-011)
- Decision: Use a payment provider's hosted checkout and subscription webhooks; we store only the plan and status
- Alternatives: build card processing; invoices by hand; a reseller
- Reason: Card data never touches our system
- Trade-offs: Webhook handling must be idempotent
- Satisfies: R-009
- Status: accepted
<!-- next target: spec/decisions/ADR-013-payvault-for-subscriptions.md mode: write -->
### ADR-013 — Payvault for subscriptions
- Topic: vendor
- Context: Owners manage subscriptions and we never store card data (R-011, ADR-011)
- Decision: Use Payvault (https://payvault.example) hosted checkout and subscription webhooks. Pricing: a percentage per successful charge, no monthly fee. Sandbox: test mode keys and test card numbers. Webhooks: every delivery is verified with the HMAC signature header and the endpoint secret before it is processed. Fallback: Stripe-compatible checkout behind the same billing module
- Alternatives: A second hosted payment provider; invoicing by bank transfer
- Reason: Hosted checkout keeps card data out of our systems
- Trade-offs: Fees scale with revenue; webhook handling must be idempotent
- Satisfies: R-009
- Status: accepted
