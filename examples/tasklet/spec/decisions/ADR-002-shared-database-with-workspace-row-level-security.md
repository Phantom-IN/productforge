### ADR-002 — Shared database with workspace row-level security
- Topic: tenancy
- Context: Every record belongs to exactly one workspace (R-007, A-006)
- Decision: One PostgreSQL database; every tenant table has workspace_id and a row-level security policy
- Alternatives: database per workspace; schema per workspace; application-only filtering
- Reason: Isolation enforced by the database at small-team scale without per-tenant operations
- Trade-offs: All queries run with a workspace session setting; cross-workspace reports need a privileged role
- Satisfies: R-007, R-008, A-006
- Status: accepted
