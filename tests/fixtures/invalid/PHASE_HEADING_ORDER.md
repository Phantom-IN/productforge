<!--
base: PHASE_PLAN_READY
target: plans/phase-05-projects.md
mode: write
expect: PHASE_HEADING_ORDER
-->
# Phase 05 — Projects

**Status:** Not started
**Depends on:** 04
**Goal:** Members group tasks into projects with an owner.

## Context

Builds projects for tasklet-alt V1 (§9).

## Scope

**In:**
- Members group tasks into projects with an owner.

**Out / deferred:**
- Anything the parity matrix defers.

## Tasks

1. `apps/api/src/projects/`: project endpoints.
2. `apps/web/app/projects/`: project list and detail pages.

## Data & schema changes

- As described in the tasks.

## API / contracts

- As described in the tasks.

## Acceptance criteria

- [ ] a member creates a project
- [ ] a project has exactly one owner
- [ ] archived projects are hidden but restorable

## References

- Unit/integration: the tests named in the tasks.
- Manual verification: walk the acceptance criteria locally.

## Test plan

- IMPLEMENTATION_PLAN §9, R-003, ADR-005

## Open questions / risks

- None.

## Definition of done

- [ ] Code merged, tests green, lint clean
- [ ] Invariants upheld
- [ ] plans/README.md status updated to "Done"
