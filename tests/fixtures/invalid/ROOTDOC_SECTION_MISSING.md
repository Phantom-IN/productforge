<!--
base: PHASE_PLAN_READY
target: CLAUDE.md
mode: write
expect: ROOTDOC_SECTION_MISSING
-->
# CLAUDE.md — tasklet-alt

Working guide for Claude Code in this repository. `IMPLEMENTATION_PLAN.md` is the architecture;
this file is the day-to-day contract. When they disagree, the plan wins — fix this file.

## Golden rules

1. **Every query is scoped to one workspace** — tenancy is the product's boundary. Enforced by: db-constraint (INV-01).
2. **Every request is authorized** — roles decide what members may do. Enforced by: middleware (INV-02).
3. **Every task change is recorded** — history is a product promise. Enforced by: test (INV-03).
4. **IDs are stable and never reused** — URLs and API clients rely on them. Enforced by: db-constraint (INV-04).
5. **Jobs are idempotent** — workers retry after crashes. Enforced by: test (INV-05).
6. **Secrets stay encrypted** — a leak must not expose working credentials. Enforced by: review (INV-06).
7. **Files are served only after a policy check** — attachments are private to task readers. Enforced by: test (INV-07).

<!-- One numbered rule per INV record in spec/ARCHITECTURE.md, in INV order:
     "N. **<rule>** — <reason>. Enforced by: <mechanism> (INV-NN)." -->

## Stack

<!-- The stack table from IMPLEMENTATION_PLAN §4, briefly. -->

## Layout

<!-- The repository tree from IMPLEMENTATION_PLAN §5. -->

## Commands

<!-- Install, run, test, lint and migrate commands for the stack. -->

## Conventions

## Extension recipes

## Architecture constraints

<!-- Decisions that must not be changed without a new ADR (cite ADR IDs). -->

## Anti-patterns

## Testing expectations

## Executing a phase

When told **"execute phase NN"**: read `plans/phase-NN-*.md`, `IMPLEMENTATION_PLAN.md` and this
file; implement every task of that phase only; run the test and lint commands until green; do the
phase's manual verification; tick its Definition-of-done boxes; set its status to **Done** in
`plans/README.md`; summarise what changed and how to verify.
