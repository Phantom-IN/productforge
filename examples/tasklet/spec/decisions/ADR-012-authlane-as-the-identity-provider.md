### ADR-012 — Authlane as the identity provider
- Topic: vendor
- Context: Sign-in needs emailed one-time links and Google sign-in (R-009, ADR-003)
- Decision: Use Authlane (https://authlane.example) for hosted sign-in; the API verifies its signed tokens. Pricing: free tier up to 1,000 monthly active members, then per active member. Sandbox: a separate Authlane tenant per developer. Webhooks: none used; tokens are verified against the tenant's published keys. Fallback: any OpenID Connect provider, because the API depends only on the token format
- Alternatives: Keycloak; Auth0-style hosted providers; building magic links ourselves
- Reason: A hosted tenant removes password storage and token issuing from V1
- Trade-offs: A vendor dependency for sign-in; a migration needs a member re-invite
- Satisfies: R-009
- Status: accepted
