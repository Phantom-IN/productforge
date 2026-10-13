### ADR-001 — UUIDv7 keys with per-workspace task numbers
- Topic: identity
- Context: Tasks need stable IDs in URLs and the API (R-001, R-007)
- Decision: Every record has a UUIDv7 primary key; tasks also get a per-workspace sequence number shown to users
- Alternatives: auto-increment integers; UUIDv4; ULID
- Reason: Time-ordered, unguessable and safe to expose; the sequence gives a human-readable key
- Trade-offs: Two identifiers per task; the sequence needs a per-workspace counter
- Satisfies: R-001, R-007
- Status: accepted
