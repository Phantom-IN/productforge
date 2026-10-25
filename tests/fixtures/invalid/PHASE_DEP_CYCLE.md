<!--
base: PHASE_PLAN_READY
target: plans/phase-05-projects.md
mode: write
expect: PHASE_DEP_CYCLE
-->
# Phase 05 — Projects

**Status:** Not started
**Depends on:** 04, 11
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

## Test plan

- Unit/integration: the tests named in the tasks.
- Manual verification: walk the acceptance criteria locally.

## References

- IMPLEMENTATION_PLAN §9, R-003, ADR-005

## Open questions / risks

- None.

## Definition of done

- [ ] Code merged, tests green, lint clean
- [ ] Invariants upheld
- [ ] plans/README.md status updated to "Done"
<!-- next target: plans/phase-11-billing.md mode: write -->
# Phase 11 — Billing

**Status:** Not started
**Depends on:** 04, 05
**Goal:** Owners manage the subscription through the payment provider.

## Context

Builds billing for tasklet-alt V1 (§10).

## Scope

**In:**
- Owners manage the subscription through the payment provider.

**Out / deferred:**
- Anything the parity matrix defers.

## Tasks

1. `apps/api/src/billing/`: checkout session and subscription webhooks.
2. `apps/web/app/settings/billing/`: plan and billing page.

## Data & schema changes

- As described in the tasks.

## API / contracts

- As described in the tasks.

## Acceptance criteria

- [ ] an owner upgrades through hosted checkout
- [ ] subscription webhooks are idempotent
- [ ] no card data reaches our servers

## Test plan

- Unit/integration: the tests named in the tasks.
- Manual verification: walk the acceptance criteria locally.

## References

- IMPLEMENTATION_PLAN §10, R-011, ADR-011, ADR-013

## Open questions / risks

- None.

## Definition of done

- [ ] Code merged, tests green, lint clean
- [ ] Invariants upheld
- [ ] plans/README.md status updated to "Done"
