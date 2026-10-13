<!--
base: PHASE_PLAN_READY
target: plans/phase-00-repository-foundation.md
mode: write
expect: PHASE00_HAS_DEPS
-->
# Phase 00 — Repository foundation

**Status:** Not started
**Depends on:** the design documents
**Goal:** A runnable monorepo skeleton with web, api and worker apps and a test harness.

## Context

Builds repository foundation for tasklet-alt V1 (§3).

## Scope

**In:**
- A runnable monorepo skeleton with web, api and worker apps and a test harness.

**Out / deferred:**
- Anything the parity matrix defers.

## Tasks

1. `package.json`: workspace scripts for build, test and lint.
2. `apps/web/`: Next.js app shell.
3. `apps/api/`: Node API shell with a health route.
4. `apps/worker/`: worker process shell.
5. `tests/integration/`: test harness against a disposable database.

## Data & schema changes

- As described in the tasks.

## API / contracts

- As described in the tasks.

## Acceptance criteria

- [ ] `npm test` runs and passes on a clean checkout
- [ ] web, api and worker start locally
- [ ] CI-ready lint passes

## Test plan

- Unit/integration: the tests named in the tasks.
- Manual verification: walk the acceptance criteria locally.

## References

- IMPLEMENTATION_PLAN §3, §4, §5, ADR-010

## Open questions / risks

- None.

## Definition of done

- [ ] Code merged, tests green, lint clean
- [ ] Invariants upheld
- [ ] plans/README.md status updated to "Done"
