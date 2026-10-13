# Phase 04 — Workspaces and members

**Status:** Not started
**Depends on:** 03
**Goal:** Owners create workspaces and invite members.

## Context

Builds workspaces and members for tasklet-alt V1 (§6).

## Scope

**In:**
- Owners create workspaces and invite members.

**Out / deferred:**
- Anything the parity matrix defers.

## Tasks

1. `apps/api/src/workspaces/`: workspace and invitation endpoints.
2. `apps/web/app/settings/members/`: member list and invite form.

## Data & schema changes

- As described in the tasks.

## API / contracts

- As described in the tasks.

## Acceptance criteria

- [ ] an owner invites a member by email
- [ ] the invited member joins with the member role
- [ ] members of another workspace see nothing

## Test plan

- Unit/integration: the tests named in the tasks.
- Manual verification: walk the acceptance criteria locally.

## References

- IMPLEMENTATION_PLAN §6, §8, R-007, ADR-002

## Open questions / risks

- None.

## Definition of done

- [ ] Code merged, tests green, lint clean
- [ ] Invariants upheld
- [ ] plans/README.md status updated to "Done"
