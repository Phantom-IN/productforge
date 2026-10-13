### ADR-007 — A PostgreSQL-backed job queue with an outbox
- Topic: async
- Context: Notifications and future digests run outside requests (R-006, A-003, A-009)
- Decision: Mutations write outbox rows in the same transaction; a worker process claims jobs with SKIP LOCKED and runs idempotent handlers
- Alternatives: a hosted queue; Redis-backed jobs; cron scripts
- Reason: No extra service, transactional with the change that caused it
- Trade-offs: Throughput is bounded by the database; fine at V1 scale
- Satisfies: R-006, A-003, A-009
- Status: accepted
