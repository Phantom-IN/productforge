# ProductForge v1.1 — real-product dogfood report

v1.1 phase 03: one real product taken through **every** stage, from `init` to `complete`, then a
fresh session given only `STARTUP_PROMPT.md`. Only aggregate numbers and paraphrased findings
are recorded here. The workspace itself (`.dogfood/umami/`) is git-ignored and not committed.

## What was run

| | |
|---|---|
| Product | Umami (open-source web analytics; public docs and repository) |
| Scope | "event tracking, goals and funnels" |
| Our name | Beacon Stats |
| Commands | `init` → `research` (×n) → `features` → `workflows` → `model` (×n) → `scope` (×2, then accepted) → `architect` → `finalize` → `trace --write` → `complete`, each in a headless `claude --plugin-dir` session; stage transitions confirmed as the user with `pf.py advance --confirmed` |

## Result per stage (all from `pf.py status` / `check`)

| Stage | Gate | Output |
|---|---|---|
| DISCOVERY | 10/10 | 128 sources · 390 claims (320 CONFIRMED / 50 PROBABLE / 9 INFERRED / 11 UNKNOWN) · 144 unknowns · 19 surfaces |
| PRODUCT_MODEL | 10/10 | 126 features · 9 workflows · 34 entities · 6 roles · 87 permission rules · 17 integrations · 55 inferences (48 active) |
| SCOPE_DEFINED | 10/10 | 124 score cards · 77 features in V1 (63 NOW, 9 SIMPLIFIED, 5 EXTERNAL) · 27 requirements · 144 V1 defaults · 0 overrides |
| ARCHITECTURE_LOCKED | 9/9 | 23 ADRs (all 10 mandatory topics decided) · 18 invariants, each enforced · 48 proposals · 27/27 requirements addressed |
| PHASE_PLAN_READY | 7/7 | 19 phases, `lint-phases` 0 findings · `trace`: 27/27 requirements traced from a source to a phase · `complete` recorded |

`pf.py validate` reported 0 errors and 0 warnings at every stage close. Merge history: 64 merges,
26 amendments, 2 discarded runs (interrupted sessions), 4 confirmed transitions.

## Fresh-session test

A new session given only `STARTUP_PROMPT.md` (read-only tools, told not to write) correctly named
the product and stack, gave the 19-phase order and all ten phase-00 tasks with their files, and
wrote nothing. As the prompt instructs, it **stopped and asked** about seven spec gaps instead of
guessing:
- no decision on the toolchain (test runner, linter, CI service);
- an undefined size-budget measurement;
- phase paths outside the declared tree;
- conflicting per-app config lists;
- a self-defeating drift check;
- two gate commands;
- a bundler target the chosen tool cannot reach.

The planners had already raised four of them in finalize's open questions.

## Bugs found and fixed during the run (all on main, with tests)

| Found in | Problem | Fix |
|---|---|---|
| `model` | `### REVISE` staged in a records artifact was taken as prose; seven corrections vanished and preflight said ok | merge refuses it with `BAD_REVISION` and the stage-and-supersede recipe; SKILL.md says which mechanism applies where |
| `scope` | nine sub-features landed in V1 under deferred parents (an API's calls without the API) | **R1 parent floor**: a deferred or dropped parent of a V1 feature is built, up the chain; an override wins |
| `scope` pass 2 | parents kept by the floor lacked a `Simplification` | the requirements pass amends one onto every BUILD SIMPLIFIED card that lacks it |
| `scope` merge report | `over_cap: 48` on a run that staged no sources | `over_cap` counts only the run's own new sources |
| interactive checklist | re-running `scope` on a finished workspace skipped Accept/Adjust | the summary and the user's decision run every time the stage is open; only agent passes resume |

Earlier in the run (already in the v1.1 changelog):
- keyed Coverage merging;
- `status` following the first failing condition;
- `### REVISE` for record files;
- workflow observed-step counts;
- near-duplicate titles that differ only by a number;
- memoised validation.

## Open items (v1.2)

1. **Toolchain as a mandatory architecture topic.** Build, test, lint and CI are decided nowhere,
   yet two ADRs require CI gates; phase 00 had to choose them itself. Add the topic to
   `architecture.MANDATORY_TOPICS` (with "not applicable" for spec-only projects).
2. **Measurable budgets need a measurement.** A requirement such as "≤ 5 KB transferred" should
   name its method (compression, tool) before it reaches a phase; a scope-editor rule plus a warn
   check.
3. **Phase paths vs. the declared tree.** Phases created `infra/ci/` while the tree listed only
   `infra/compose/` and `infra/docker/`; `lint-phases` accepted it because `infra/` is declared.
   Match at the deepest declared level.
4. **Permission unknowns stay high.** 144 of 510 cells (28 %) are `?`, above
   `model.max_unknown_permission_ratio` (20 %). The one gap-loop pass found no new public evidence;
   observe mode's two-role sessions (v2) are the intended answer.
5. No competitor pass on this run (PRODUCT_MODEL closed without `research/COMPETITORS.md`), so the
   table-stakes input to scoring was zero throughout.
