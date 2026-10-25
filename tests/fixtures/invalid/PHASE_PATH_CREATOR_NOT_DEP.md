<!--
base: PHASE_PLAN_READY
target: plans/phase-10-attachments.md
mode: write
expect: PHASE_PATH_CREATOR_NOT_DEP
-->
# Phase 10 — Attachments

**Status:** Not started
**Depends on:** 06
**Goal:** Members attach files stored in object storage.

## Context

Builds attachments for tasklet-alt V1 (§16).

## Scope

**In:**
- Members attach files stored in object storage.

**Out / deferred:**
- Anything the parity matrix defers.

## Tasks

1. `apps/api/src/files/`: upload and signed-URL endpoints.
2. `apps/api/src/comments/`: attachments are listed with a comment.
3. `tests/integration/files.test.ts`: direct storage access is denied.

## Data & schema changes

- As described in the tasks.

## API / contracts

- As described in the tasks.

## Acceptance criteria

- [ ] a member attaches a file to a task
- [ ] downloads use signed URLs that expire in 5 minutes
- [ ] a non-reader cannot download the file

## Test plan

- Unit/integration: the tests named in the tasks.
- Manual verification: walk the acceptance criteria locally.

## References

- IMPLEMENTATION_PLAN §16, R-010, ADR-008, ADR-015, INV-07

## Open questions / risks

- None.

## Definition of done

- [ ] Code merged, tests green, lint clean
- [ ] Invariants upheld
- [ ] plans/README.md status updated to "Done"
