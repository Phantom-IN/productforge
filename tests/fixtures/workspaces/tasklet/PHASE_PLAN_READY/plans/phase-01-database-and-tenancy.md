# Phase 01 — Database and tenancy

**Status:** Not started
**Depends on:** 00
**Goal:** PostgreSQL schema with workspace row-level security.

## Context

Builds database and tenancy for tasklet-alt V1 (§6).

## Scope

**In:**
- PostgreSQL schema with workspace row-level security.

**Out / deferred:**
- Anything the parity matrix defers.

## Tasks

1. `packages/db/migrations/`: workspaces, members and RLS policies with drizzle-kit 0.28.0 against `postgres:16.4`, read from `DATABASE_URL`.
2. `packages/db/src/session.ts`: per-request workspace setting.
3. `tests/integration/tenancy.test.ts`: cross-workspace reads are denied.

## Data & schema changes

- As described in the tasks.

## API / contracts

- As described in the tasks.

## Acceptance criteria

- [ ] every tenant table has workspace_id and an RLS policy
- [ ] a query without a workspace setting returns no rows
- [ ] UUIDv7 keys are generated

## Test plan

- Unit/integration: the tests named in the tasks.
- Manual verification: walk the acceptance criteria locally.

## References

- IMPLEMENTATION_PLAN §6, §18, ADR-001, ADR-002, ADR-005, INV-01, INV-04, R-007

## Open questions / risks

- None.

## Definition of done

- [ ] Code merged, tests green, lint clean
- [ ] Invariants upheld
- [ ] plans/README.md status updated to "Done"
