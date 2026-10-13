# Phase 03 — Authorization policy

**Status:** Not started
**Depends on:** 02
**Goal:** One policy module enforces the permissions matrix.

## Context

Builds authorization policy for tasklet-alt V1 (§8).

## Scope

**In:**
- One policy module enforces the permissions matrix.

**Out / deferred:**
- Anything the parity matrix defers.

## Tasks

1. `packages/shared/src/policy.ts`: role × resource × action table.
2. `apps/api/src/policy/`: router middleware requiring a policy per handler.
3. `tests/integration/policy.test.ts`: one test per permission cell.

## Data & schema changes

- As described in the tasks.

## API / contracts

- As described in the tasks.

## Acceptance criteria

- [ ] handlers without a policy declaration fail to register
- [ ] every permission cell has a passing test
- [ ] guests cannot create tasks

## Test plan

- Unit/integration: the tests named in the tasks.
- Manual verification: walk the acceptance criteria locally.

## References

- IMPLEMENTATION_PLAN §8, ADR-004, INV-02, R-008

## Open questions / risks

- None.

## Definition of done

- [ ] Code merged, tests green, lint clean
- [ ] Invariants upheld
- [ ] plans/README.md status updated to "Done"
