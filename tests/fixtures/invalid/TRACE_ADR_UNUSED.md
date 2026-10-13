<!--
base: PHASE_PLAN_READY
target: plans/phase-11-billing.md
mode: write
expect: TRACE_ADR_UNUSED
-->
# Phase 11 — Billing

**Status:** Not started
**Depends on:** 04
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

- IMPLEMENTATION_PLAN §10, R-011

## Open questions / risks

- None.

## Definition of done

- [ ] Code merged, tests green, lint clean
- [ ] Invariants upheld
- [ ] plans/README.md status updated to "Done"
