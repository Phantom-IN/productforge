### ADR-004 — Role checks in one policy module
- Topic: authz
- Context: Owner, admin, member and guest rights follow the permissions matrix (R-008, A-005)
- Decision: Every API handler calls a single policy module that maps role × resource × action from the permissions matrix
- Alternatives: per-handler checks; an external policy engine; database-only policies
- Reason: One place to read, test and change rights; RLS stays the tenancy backstop
- Trade-offs: The module must be called everywhere — enforced by an invariant
- Satisfies: R-008, A-005
- Status: accepted
