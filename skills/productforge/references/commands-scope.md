# SCOPE_DEFINED command

`/productforge scope` reduces the reconstructed product to our V1 (`references/prioritisation-model.md`).
`SKILL.md` owns dispatch (closing PRODUCT_MODEL needs the user's confirmation), the Agent run
protocol and the end-of-command report; `$PF` and `<ws>` are as defined there. **Scripts compute
every priority and decision** — never state a number or a decision that `pf.py score` did not print.

### `/productforge scope`

Re-running the command resumes: skip a step whose output exists (counts from `pf.py status --json`,
gaps from `pf.py check --json`).

1. **Score pass** (when there are no score cards, or `G-SC-ALL-SCORED` names unscored features):
   scope-editor run(s): `brief --role scope-editor --task "Pass 1: score cards for <all features |
   these features: IDs>." --input research/FEATURE_MATRIX.md --input research/workflows --input
   research/architecture-inference.md --input spec/DOMAIN_MODEL.md --input spec/PERMISSIONS_MATRIX.md
   --input spec/INTEGRATIONS.md --input research/COMPETITORS.md --input spec/PARITY_MATRIX.md
   --template spec/PARITY_MATRIX.md`. More than 60 features: one run per domain (`feature-plan`,
   `--partition "<domain>"`) in batches of at most `agents.max_pending_runs`. Preflight, repair,
   merge.
2. **Score.** `python3.11 "$PF" score --write --workspace <ws> --json`. Show a compact summary:
   `counts` per decision; every override; every DEFER/DROP of a feature with `table_stakes` > 0;
   every row whose `rule` starts with `R1` (kept because other features depend on it, or — "R1
   parent floor" — because one of its sub-features is in V1).
3. **The user decides.** Ask with AskUserQuestion: "Accept this scope (Recommended)" or "Adjust".
   On **Adjust**, ask which features move to which decision and why; record each with
   `python3.11 "$PF" override <F-ID> --decision "<DECISION>" --reason "<the user's words>"
   --workspace <ws> --json` (`--clear` removes one), show the new summary, and ask again.
   **Requirements are written only after the user accepts.** Without AskUserQuestion: show the
   summary, explain how to adjust, and stop here.
4. **Requirements pass**, one scope-editor run: `brief --role scope-editor --task "Pass 2: review
   the computed decisions (overrides only with reasons; keep the user's), amend a Simplification
   onto every BUILD SIMPLIFIED card that lacks one (R1 parent-floor rows: only what their V1
   children need), write requirements for every V1 feature, a V1 default for every unknown, and
   the product spec narrative."
   --input spec/PARITY_MATRIX.md --input research/FEATURE_MATRIX.md --input research/workflows
   --input research/architecture-inference.md --input research/UNKNOWNS.md --input
   spec/PRODUCT_SPEC.md --template spec/PRODUCT_SPEC.md --template research/UNKNOWNS.md`.
   Preflight, repair, merge; then `pf.py score --write` again.
5. **Gate.** `python3.11 "$PF" check --workspace <ws> --json`: report the SCOPE_DEFINED gate as a
   compact table and the reduction funnel (from `spec/PRODUCT_SPEC.md`) — **never advance here**.
   If the gate passes the next command is `/productforge architect` (it asks before closing
   SCOPE_DEFINED); otherwise the step each failing condition names.
