# Phase 06 — Tasks and statuses

**Status:** Not started
**Depends on:** 05
**Goal:** Tasks move through To do, In progress and Done with a history.

## Context

Builds tasks and statuses for tasklet-alt V1 (§6).

## Scope

**In:**
- Tasks move through To do, In progress and Done with a history.

**Out / deferred:**
- Anything the parity matrix defers.

## Tasks

1. `apps/api/src/tasks/`: task endpoints with per-workspace numbers.
2. `packages/db/migrations/`: tasks and activity tables.
3. `tests/integration/tasks.test.ts`: one activity entry per mutation.

## Data & schema changes

- As described in the tasks.

## API / contracts

- As described in the tasks.

## Acceptance criteria

- [ ] a task is created in To do
- [ ] every task change appends one activity entry
- [ ] task numbers are never reused

## Test plan

- Unit/integration: the tests named in the tasks.
- Manual verification: walk the acceptance criteria locally.

## References

- IMPLEMENTATION_PLAN §6, §9, R-001, R-004, INV-03, INV-04

## Open questions / risks

- None.

## Definition of done

- [ ] Code merged, tests green, lint clean
- [ ] Invariants upheld
- [ ] plans/README.md status updated to "Done"
