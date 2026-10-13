# Phase 02 — Sign-in

**Status:** Not started
**Depends on:** 01
**Goal:** Members sign in through the identity provider.

## Context

Builds sign-in for tasklet-alt V1 (§7).

## Scope

**In:**
- Members sign in through the identity provider.

**Out / deferred:**
- Anything the parity matrix defers.

## Tasks

1. `apps/api/src/auth/`: token verification and sessions.
2. `apps/web/app/sign-in/`: magic-link and Google sign-in pages.

## Data & schema changes

- As described in the tasks.

## API / contracts

- As described in the tasks.

## Acceptance criteria

- [ ] a magic link signs a member in once
- [ ] Google sign-in works
- [ ] unauthenticated API calls are refused

## Test plan

- Unit/integration: the tests named in the tasks.
- Manual verification: walk the acceptance criteria locally.

## References

- IMPLEMENTATION_PLAN §7, ADR-003, R-009

## Open questions / risks

- None.

## Definition of done

- [ ] Code merged, tests green, lint clean
- [ ] Invariants upheld
- [ ] plans/README.md status updated to "Done"
