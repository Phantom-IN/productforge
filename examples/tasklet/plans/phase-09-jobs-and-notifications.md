# Phase 09 — Jobs and notifications

**Status:** Not started
**Depends on:** 08
**Goal:** Assignments and mentions notify members in the app.

## Context

Builds jobs and notifications for tasklet-alt V1 (§11).

## Scope

**In:**
- Assignments and mentions notify members in the app.

**Out / deferred:**
- Anything the parity matrix defers.

## Tasks

1. `apps/worker/src/jobs/`: outbox claim loop and notification handler.
2. `apps/api/src/notifications/`: notification list and read state.
3. `tests/integration/jobs.test.ts`: run-twice tests for every handler.

## Data & schema changes

- As described in the tasks.

## API / contracts

- As described in the tasks.

## Acceptance criteria

- [ ] assigning a task notifies the assignee within 5 s
- [ ] running a job twice creates one notification
- [ ] notifications are visible only to their recipient

## Test plan

- Unit/integration: the tests named in the tasks.
- Manual verification: walk the acceptance criteria locally.

## References

- IMPLEMENTATION_PLAN §11, R-006, ADR-007, INV-05

## Open questions / risks

- None.

## Definition of done

- [ ] Code merged, tests green, lint clean
- [ ] Invariants upheld
- [ ] plans/README.md status updated to "Done"
