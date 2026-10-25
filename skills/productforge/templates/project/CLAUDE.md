# CLAUDE.md — {{our_name}}

Working guide for Claude Code in this repository. `IMPLEMENTATION_PLAN.md` is the architecture;
this file is the day-to-day contract. When they disagree, the plan wins — fix this file.

## Golden rules

<!-- One numbered rule per INV record in spec/ARCHITECTURE.md, in INV order:
     "N. **<rule>** — <reason>. Enforced by: <mechanism> (INV-NN)." -->

## Stack

<!-- The stack table from IMPLEMENTATION_PLAN §4, briefly, then one row per external service
     (vendor, ADR) and one per toolchain concern (choice, pinned version) from
     spec/ARCHITECTURE.md. -->

## Layout

<!-- The repository tree from IMPLEMENTATION_PLAN §5. -->

## Commands

<!-- Install, run, test, lint and migrate commands for the stack. -->

## Conventions

## Security

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
