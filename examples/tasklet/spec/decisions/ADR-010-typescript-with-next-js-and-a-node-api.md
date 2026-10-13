### ADR-010 — TypeScript with Next.js and a Node API
- Topic: other
- Context: One language across web, api and worker; the user prefers Next.js and PostgreSQL
- Decision: Next.js for the web app, a Node.js API service and worker sharing TypeScript packages
- Alternatives: Python API with a React SPA; Ruby on Rails; Go API
- Reason: Matches the preference and lets web, api and worker share types and the policy module
- Trade-offs: Node's single thread needs care for CPU-heavy work (none in V1)
- Satisfies: R-001, R-005
- Status: accepted
