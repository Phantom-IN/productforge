### ADR-005 — PostgreSQL as the primary store
- Topic: storage
- Context: Tasks, projects, comments and an append-only history (R-001, R-003, R-004, A-004, A-012)
- Decision: PostgreSQL holds all relational data, the activity history and the job queue
- Alternatives: MySQL; a document database; SQLite
- Reason: Relational model, row-level security and a job queue in one managed service; matches the stack preference
- Trade-offs: Vertical scaling limits are far beyond V1
- Satisfies: R-001, R-003, R-004, A-004, A-012
- Status: accepted
