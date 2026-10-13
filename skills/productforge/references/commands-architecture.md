# ARCHITECTURE_LOCKED command

`/productforge architect [--stack "…"] [--deployment docker|serverless|k8s]` designs our V1
architecture (`references/architecture-playbook.md`). `SKILL.md` owns dispatch (closing
SCOPE_DEFINED needs the user's confirmation), the Agent run protocol and the end-of-command report;
`$PF` and `<ws>` are as defined there.

### `/productforge architect`

Re-running resumes: skip a step whose output exists (`pf.py check --json` names the gaps).

1. **Preferences.** `python3.11 "$PF" set-preferences [--stack "<list>"] [--deployment <target>]
   --workspace <ws> --json` — with the user's `--stack` / `--deployment` when given; without them it
   only reports the stored preferences. Use its `architecture` output in the brief.
2. **Design pass**, one systems-architect run: `brief --role systems-architect --task "Design pass:
   our architecture for V1. Stack preferences: <list or none>; deployment: <target>."
   --input spec/PRODUCT_SPEC.md --input spec/PARITY_MATRIX.md --input
   research/architecture-inference.md --input spec/DOMAIN_MODEL.md --input spec/PERMISSIONS_MATRIX.md
   --input spec/INTEGRATIONS.md --input research/UNKNOWNS.md --input spec/ARCHITECTURE.md
   --template spec/ARCHITECTURE.md --template spec/adr.md`. Preflight, repair, merge.
3. **Review.** Show the stack table, the generated `## Decisions` list (ADR · decision · topic),
   the invariants and the requirement coverage. If `diagram.render` resolves to a real provider you
   may render `## Overview` for the user (the workspace copy stays text). Ask with
   AskUserQuestion: "Accept the architecture (Recommended)" or "Change a decision". On a change:
   ask which ADR and what should change, then brief the systems-architect for **that ADR only**
   (`--task "Change ADR-NNN: <the user's request>. Supersede it; re-point proposals."`); preflight,
   repair, merge, and show the result. Without AskUserQuestion, report and stop.
4. **Gate.** `python3.11 "$PF" check --workspace <ws> --json`: report the ARCHITECTURE_LOCKED gate
   as a compact table plus any `UNJUSTIFIED_COMPONENT` / `SUPERSEDED_DECISION_CITED` warnings —
   **never advance here**. If it passes the next command is `/productforge finalize` (it asks before
   closing ARCHITECTURE_LOCKED).
