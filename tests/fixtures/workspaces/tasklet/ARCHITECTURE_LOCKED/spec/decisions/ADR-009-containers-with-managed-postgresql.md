### ADR-009 — Containers with managed PostgreSQL
- Topic: deployment
- Context: Small-team scale; data encrypted at rest (A-011)
- Decision: Docker images for web, api and worker on a container platform; managed PostgreSQL and object storage with encryption at rest
- Alternatives: Kubernetes; serverless functions; a single VM
- Reason: Fewest moving parts that still separate web, api and worker
- Trade-offs: Platform lock-in for networking and secrets
- Satisfies: A-011, R-007
- Status: accepted
