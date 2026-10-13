# Phase 07 — Board and polling

**Status:** Not started
**Depends on:** 06
**Goal:** The board shows tasks by status and stays current within 30 s.

## Context

Builds board and polling for tasklet-alt V1 (§12).

## Scope

**In:**
- The board shows tasks by status and stays current within 30 s.

**Out / deferred:**
- Anything the parity matrix defers.

## Tasks

1. `apps/web/app/board/`: board columns and drag between statuses.
2. `apps/api/src/tasks/changes.ts`: changes since a cursor.

## Data & schema changes

- As described in the tasks.

## API / contracts

- As described in the tasks.

## Acceptance criteria

- [ ] moving a task updates its status
- [ ] another browser sees the change within 30 s
- [ ] the board refetches on focus

## Test plan

- Unit/integration: the tests named in the tasks.
- Manual verification: walk the acceptance criteria locally.

## References

- IMPLEMENTATION_PLAN §12, R-002, ADR-006

## Open questions / risks

- None.

## Definition of done

- [ ] Code merged, tests green, lint clean
- [ ] Invariants upheld
- [ ] plans/README.md status updated to "Done"
