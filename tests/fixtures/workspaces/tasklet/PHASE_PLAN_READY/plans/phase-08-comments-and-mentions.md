# Phase 08 — Comments and mentions

**Status:** Not started
**Depends on:** 06
**Goal:** Members discuss tasks and mention each other.

## Context

Builds comments and mentions for tasklet-alt V1 (§9).

## Scope

**In:**
- Members discuss tasks and mention each other.

**Out / deferred:**
- Anything the parity matrix defers.

## Tasks

1. `apps/api/src/comments/`: comment endpoints with mention parsing.
2. `apps/web/app/board/comments/`: comment thread on the task panel.

## Data & schema changes

- As described in the tasks.

## API / contracts

- As described in the tasks.

## Acceptance criteria

- [ ] a member comments on a task
- [ ] a mention is stored with the comment
- [ ] comments follow the task's permissions

## Test plan

- Unit/integration: the tests named in the tasks.
- Manual verification: walk the acceptance criteria locally.

## References

- IMPLEMENTATION_PLAN §9, R-005

## Open questions / risks

- None.

## Definition of done

- [ ] Code merged, tests green, lint clean
- [ ] Invariants upheld
- [ ] plans/README.md status updated to "Done"
