# Phase 12 — Deployment and hardening

**Status:** Not started
**Depends on:** 07, 09, 10, 11
**Goal:** Production images, encrypted stores and observability.

## Context

Builds deployment and hardening for tasklet-alt V1 (§14).

## Scope

**In:**
- Production images, encrypted stores and observability.

**Out / deferred:**
- Anything the parity matrix defers.

## Tasks

1. `infra/docker/`: images for web, api and worker.
2. `docs/runbook.md`: deploy, rollback and secrets.
3. `tests/e2e/`: smoke test of the core flow.

## Data & schema changes

- As described in the tasks.

## API / contracts

- As described in the tasks.

## Acceptance criteria

- [ ] images build and start on the container platform
- [ ] stores are encrypted at rest
- [ ] the e2e smoke test passes against staging

## Test plan

- Unit/integration: the tests named in the tasks.
- Manual verification: walk the acceptance criteria locally.

## References

- IMPLEMENTATION_PLAN §14, §15, §17, ADR-009, INV-06

## Open questions / risks

- None.

## Definition of done

- [ ] Code merged, tests green, lint clean
- [ ] Invariants upheld
- [ ] plans/README.md status updated to "Done"
