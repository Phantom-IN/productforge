# PHASE_PLAN_READY command

`/productforge finalize` writes the generated project (`references/phase-plan-method.md`).
`SKILL.md` owns dispatch (closing ARCHITECTURE_LOCKED needs the user's confirmation), the Agent run
protocol and the end-of-command report; `$PF` and `<ws>` are as defined there.

### `/productforge finalize`

Re-running resumes: skip a pass whose output exists and lints clean (`pf.py lint-phases --json`).

1. **Root documents**, one phase-planner run: `brief --role phase-planner --task "Pass 1: root
   documents." --input spec/PRODUCT_SPEC.md --input spec/PARITY_MATRIX.md --input
   spec/ARCHITECTURE.md --input spec/decisions --input spec/DOMAIN_MODEL.md --input
   spec/PERMISSIONS_MATRIX.md --input spec/INTEGRATIONS.md --template project/README.md --template
   project/IMPLEMENTATION_PLAN.md --template project/CLAUDE.md --template project/DEVELOPMENT.md
   --template project/STARTUP_PROMPT.md`. Preflight (the root-document checks run there), repair,
   merge.
2. **Phases**, phase-planner run(s): `brief --role phase-planner --task "Pass 2: the phase list,
   §19, plans/README.md and every phase file." --input IMPLEMENTATION_PLAN.md --input CLAUDE.md
   --input spec/PRODUCT_SPEC.md --input spec/ARCHITECTURE.md --input spec/decisions --template
   plans/plans-README.md --template plans/phase.md`. For more than ~10 phases: one run fixes the
   list (§19 + index + files with headers), then runs of at most 5 phases fill them, each reading
   only the sections its phases cite. Preflight, repair, merge.
3. **Lint.** `python3.11 "$PF" lint-phases --workspace <ws> --json`; findings go back to the
   planner as a repair brief (`--run-id`) until clean or `max_repair_loops` is spent.
4. **Review.** Show the phase list (number · name · depends on, from `lint-phases`). Ask with
   AskUserQuestion: "Accept the plan (Recommended)", "Split a phase", "Merge phases", "Reorder". On
   a change, brief the planner with the user's request, merge, lint, and show the list again.
   Without AskUserQuestion, report and stop.
5. **Gate.** `python3.11 "$PF" check --workspace <ws> --json`: report the PHASE_PLAN_READY gate
   (the traceability conditions arrive with `pf.py trace`). Finish with the exact next step:
   "Open a new Claude Code session in `<ws>`, paste `STARTUP_PROMPT.md`, then say
   `execute phase 00`."
