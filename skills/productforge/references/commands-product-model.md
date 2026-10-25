# PRODUCT_MODEL commands

Procedures for the PRODUCT_MODEL stage commands. `SKILL.md` owns dispatch, transitions, the Agent
run protocol, the Delegated run protocol and the end-of-command report; `$PF` and `<ws>` are as
defined there. Run the stage's commands in this order: `features` → `workflows` → `model`
→ `competitors` (the default before `scope`); `/productforge scope` closes the stage.

### `/productforge features`

PRODUCT_MODEL: the feature hierarchy in `research/FEATURE_MATRIX.md`. Views (`## Hierarchy`,
`## Matrix`, the surfaces' `## Surface → features`) are rendered by merge — never by hand.

1. **Plan.** `python3.11 "$PF" feature-plan --workspace <ws> --json`.
2. **Domain split** when `domains` is empty (or the user asks to redo it): one product-analyst run —
   `brief --role product-analyst --task "Domain split: propose 4-10 non-overlapping domains for
   <scope> in a ## Domains section." --input research/product-surfaces.md
   --input research/product-overview.md --input research/DISCOVERY_LEDGER.md
   --template research/FEATURE_MATRIX.md`. Preflight, repair, merge. Show the domains and ask with
   AskUserQuestion: "Use these domains" or Other (their changes). On changes, re-run the domain
   split with the user's instruction in the task. Without AskUserQuestion, continue and list the
   domains in the report so the user can rerun.
3. **Feature passes**, in batches of at most `max_parallel` domains from `empty_domains` (brief only
   the current batch): `brief --role product-analyst --task "Feature pass for domain <name>:
   record every user-visible capability in this domain (hierarchy at most 3 levels)." --partition
   "<name>" --input research/DISCOVERY_LEDGER.md --input research/sources.md
   --input research/product-surfaces.md --input research/FEATURE_MATRIX.md
   --input research/UNKNOWNS.md --template research/FEATURE_MATRIX.md --budget "at most
   <per_domain_budget> features; group minor capabilities as sub-features"`. Spawn the batch in one
   message; preflight, repair and merge each run one at a time; then brief the next batch.
4. **Coverage.** Plan again. If `surfaces_without_features` is not empty, one product-analyst run
   mapping features for those surfaces; report `features_in_unlisted_domains` if any.
5. **Dedupe pass** if `pf.py validate` shows `NEAR_DUPLICATE_TITLE` warnings for features: one
   product-analyst run with the warnings and the instruction to supersede the weaker feature by
   amendment. Preflight, repair, merge.
6. Report features per domain (`feature-plan`), surfaces without features, validation, and the next
   command (`/productforge workflows`, Phase 09).

### `/productforge workflows`

PRODUCT_MODEL: core user workflows in `research/workflows/`, each separating `[observed]` steps (with
evidence) from `[implied-system]` steps (what our system must do). The index in `research/README.md`
is rendered by merge.

1. **Candidates.** `python3.11 "$PF" workflow-candidates --workspace <ws> --json` — deterministic
   proposals from the feature matrix. Payload: `candidates` (name, domain, features, reason),
   `cap`, `effective_cap`, `existing_workflows`, `required_domains`, `remaining_candidates`,
   `features_covered`, and `cap_below_required` (the number of required candidates) only when the
   cap is too low. Selection: first one candidate for every domain with at least 3 active features
   and no workflow yet (`required_domains`, largest domain first, never dropped by the cap), then
   extras round-robin over the domains ordered by feature count, up to `model.max_workflows`. When
   `cap_below_required` is present, `model.max_workflows` can never satisfy
   `G-PM-WORKFLOW-PER-DOMAIN`: raise it to `effective_cap` (`config set model.max_workflows
   <effective_cap> --reason "…"`, with the user's agreement; autonomous mode just does it and logs
   a `decide` entry) and run the candidates again.
2. **Trim.** Show the candidates grouped by domain and ask with AskUserQuestion: "Use all
   (Recommended)", "Only one per domain", or Other (the user's list). Without AskUserQuestion, use
   all and list them in the report.
3. **Workflow passes**, one ux-analyst run per domain, in batches of at most
   `agents.max_pending_runs` (brief only the current batch): `brief --role ux-analyst --task
   "Workflow pass for domain <name>: reconstruct these workflows: <names and their F IDs>."
   --partition "<name>" --input research/FEATURE_MATRIX.md --input research/DISCOVERY_LEDGER.md
   --input research/sources.md --input research/product-surfaces.md --input research/UNKNOWNS.md
   --template research/workflow.md`. Spawn the batch in one message; preflight, repair and merge
   one at a time; then the next batch.
4. **Research requests** per the Agent run protocol.
5. Report: workflows per domain, the observed vs implied step counts (from the index in
   `research/README.md`), validation, and the next command (`/productforge model`).

### `/productforge model`

PRODUCT_MODEL: the target's domain model (`spec/DOMAIN_MODEL.md`, `E-`), permissions
(`spec/PERMISSIONS_MATRIX.md`, `RL-`/`PR-`), integrations (`spec/INTEGRATIONS.md`, `I-`) and
architecture inference (`research/architecture-inference.md`, `A-`). Merge renders every view.
Read `references/product-model-playbook.md`. Run the passes in order, **skipping a pass whose
records exist** (counts from `pf.py status --json`) unless the user asks to redo it:

1. **Domain pass** (when `entities` is 0), one domain-architect run: `brief --role domain-architect
   --task "Domain and permissions pass: reconstruct the entities, roles and permission rules."
   --input research/FEATURE_MATRIX.md --input research/workflows --input research/DISCOVERY_LEDGER.md
   --input research/UNKNOWNS.md --input research/sources.md --input spec/DOMAIN_MODEL.md --input
   spec/PERMISSIONS_MATRIX.md --template spec/DOMAIN_MODEL.md --template spec/PERMISSIONS_MATRIX.md`.
   When `feature-plan` reports `over_soft_cap`, split it: a core run (tenancy, users, memberships,
   roles) first, then one run per domain (`--partition "<domain>"`, the core entities listed in the
   task) in batches of at most `agents.max_pending_runs`.
   **Permission gaps.** After the domain pass, `python3.11 "$PF" permission-gaps --workspace <ws>
   --json`. When `over_limit` is true (more than `model.max_unknown_permission_ratio` of the cells
   are `?`), run the Research-request protocol once for the listed gaps — one targeted
   research-agent pass ("Find what the documentation says about who may <action> <resource>: …",
   the unknowns' questions) — then one domain-architect pass that **supersedes** a rule only where
   new evidence settles its `?` cells (a new rule plus `### AMEND PR-NNN` · `Status: superseded-by
   PR-?1`). Cells nothing settles stay `?`.
2. **Integration pass** (when `integrations` is 0), one product-analyst run: `brief --role
   product-analyst --task "Integration pass: one I record per provider or mechanism."
   --input research/DISCOVERY_LEDGER.md --input research/sources.md --input research/FEATURE_MATRIX.md
   --input spec/INTEGRATIONS.md --input research/UNKNOWNS.md --template spec/INTEGRATIONS.md`.
3. **Inference pass** (when `inferences` is 0, or the gate's `G-PM-INFERENCE-COMPLETE` names
   uncovered workflows — then the task lists them), one systems-architect run: `brief --role
   systems-architect --task "Inference pass: …" --input research/workflows --input
   spec/DOMAIN_MODEL.md --input spec/PERMISSIONS_MATRIX.md --input spec/INTEGRATIONS.md --input
   research/DISCOVERY_LEDGER.md --input research/sources.md --input
   research/architecture-inference.md --template research/architecture-inference.md`.
4. After each run: preflight, repair and merge per the Agent run protocol; then its **research
   requests** (these agents have no network, so missing evidence always arrives this way).
5. **Gate.** `python3.11 "$PF" check --workspace <ws> --json`: report the PRODUCT_MODEL gate as a
   compact table — **never advance here**. Also report `entities`, `roles`, `permission_rules`,
   `unknown_permission_cells`, `integrations`, `inferences` from `pf.py status --json`, the root of
   the relationship tree, and any `TECH_ASSERTION_IN_OBSERVATION` / `REQUIREMENT_NOT_MEASURABLE`
   warnings for the user to review. If the gate passes the next command is `/productforge scope`
   (it asks before closing PRODUCT_MODEL); otherwise the command each failing condition names.

### `/productforge competitors`

PRODUCT_MODEL (also allowed while SCOPE_DEFINED is open, as an evidence-adding command; refused from
ARCHITECTURE_LOCKED on): a shallow category lens in `research/COMPETITORS.md` (`C-`, `FS-`). It is the
default step before `scope`: `G-SC-COMPETITOR-SIGNAL` needs `competitors.min_researched`
competitors, or a user waiver (`pf.py waive competitors --confirmed`, see `commands-scope.md`); a waived
pass leaves scoring signals neutral.

1. **Candidates.** `python3.11 "$PF" competitor-candidates --workspace <ws> --json` (names from
   comparison/review source titles, capped by `competitors.max`). **Never research a competitor the
   user has not confirmed** or add names yourself: ask with AskUserQuestion (multi-select + Other).
   No answer — or no AskUserQuestion — means list the candidates and stop.
   **Discovery pass.** Comparison and directory sites (`competitors.aggregator_names`) and generic
   words are already filtered out. When fewer than `competitors.min_researched` names remain, brief
   one research-agent run: `brief --role research-agent --task "Competitor discovery: from the
   comparison sources <comparison_sources> and one web search for '<product> alternatives', list
   the direct alternatives most often named, each with its citing source; add those comparison
   sources if missing." --partition "competitor discovery" --input research/sources.md
   --template research/sources.md` (sources and names only, no C records yet; the names go in the
   run summary with their S IDs), then preflight, repair, merge, and re-run `competitor-candidates`.
   Never invent a name without a citing source. Interactive: the user picks from the result.
   Autonomous: take the top `competitors.max` names that have at least one citation and log
   `pf.py decide`.
2. **Per competitor**, in batches of at most 3: `python3.11 "$PF" discover <its homepage>
   --max-pages 20 --workspace <ws>` (only when the user gave or confirmed its URL; otherwise the
   analyst finds it), then `brief --role product-analyst --task "Competitor pass for <name>: at most
   10 sources." --partition "<name>" --input research/FEATURE_MATRIX.md --input
   research/COMPETITORS.md --input research/sources.md --template research/COMPETITORS.md
   --template research/sources.md`. If `research.deep` resolves to a real provider, delegate one
   pass per competitor (positioning, features, pricing, complaints) first. Preflight, repair, merge.
   Research requests count toward the competitor's `competitors.max_sources` budget: once it is
   spent, report them instead of running a targeted pass.
3. Report the generated landscape and the table-stakes, rare and differentiator counts (from
   `research/COMPETITORS.md`), plus validation. Next: `/productforge scope` once the PRODUCT_MODEL
   gate passes.
