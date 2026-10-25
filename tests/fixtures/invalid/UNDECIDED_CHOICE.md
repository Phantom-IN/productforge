<!--
base: ARCHITECTURE_LOCKED
target: spec/decisions/ADR-014-mailpost-for-transactional-email.md
mode: replace ADR-014
expect: UNDECIDED_CHOICE
-->
### ADR-014 — Mailpost for transactional email
- Topic: vendor
- Context: Sign-in links and invitations are emailed (R-007, R-009)
- Decision: Use Mailpost (https://mailpost.example) over its HTTPS API for transactional email. Pricing: free up to 3,000 messages a month, then per thousand. Sandbox: a sandbox domain that accepts mail and delivers nothing. Webhooks: delivery events are verified with the signature header. Fallback: any SMTP relay through the same mail port
- Alternatives: A generic SMTP relay; the identity provider's own mailer
- Reason: A single API with delivery events and a sandbox
- Trade-offs: Delivery depends on a verified sending domain; the library choice for the mail client is open
- Satisfies: R-007, R-009
- Status: accepted
