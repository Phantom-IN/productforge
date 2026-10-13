### ADR-006 — Polling instead of push in V1
- Topic: realtime
- Context: Boards should reflect others' changes (R-002, A-001); push was simplified (SC-009)
- Decision: Boards refetch on window focus and every 30 s; changes carry an updated_at cursor
- Alternatives: WebSockets; server-sent events; a hosted realtime service
- Reason: Meets the 30 s acceptance signal with no new infrastructure
- Trade-offs: Up to 30 s staleness; more requests per open board
- Satisfies: R-002, A-001
- Status: accepted
