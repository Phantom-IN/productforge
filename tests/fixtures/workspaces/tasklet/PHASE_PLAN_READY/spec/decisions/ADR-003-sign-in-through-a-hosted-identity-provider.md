### ADR-003 — Sign-in through a hosted identity provider
- Topic: authn
- Context: Magic links and Google sign-in are expected (R-009, A-014)
- Decision: Use a hosted identity provider for emailed one-time links and Google OIDC; our API verifies its tokens
- Alternatives: build magic links ourselves; passwords plus Google; Google only
- Reason: Sign-in is security-critical and commodity; the provider covers both methods
- Trade-offs: A vendor dependency and per-user cost
- Satisfies: R-009, A-014
- Status: accepted
