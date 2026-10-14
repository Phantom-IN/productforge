# Interactive checklist (v1.1 phase 04)

Every live run so far was headless, where AskUserQuestion does not exist. This checklist clicks
through the dialogs once in a real Claude Code session, about 15 minutes, on copies of the
synthetic Tasklet fixtures (no network, no real product). Each check says what to type, the
dialog you should see, and how to confirm the effect with `pf.py`, which is the authority, not
the chat.

## Setup (once)

`REPO` is this repository. The Python step leaves `ck-disc` with no accepted scope, nine major
areas and two recommended scopes. The block has no `#` comments, so it pastes into zsh as is.

```bash
REPO=~/Documents/productforge
PF=$REPO/skills/productforge/scripts/pf.py
mkdir -p ~/pf-checklist && cd ~/pf-checklist
cp -R $REPO/tests/fixtures/workspaces/tasklet/PRODUCT_MODEL ck-model
cp -R $REPO/tests/fixtures/workspaces/tasklet/SCOPE_DEFINED ck-scope
cp -R $REPO/tests/fixtures/workspaces/tasklet/DISCOVERY ck-disc
python3.11 - ck-disc <<'EOF'
import json, pathlib, sys
ws = pathlib.Path(sys.argv[1])
st = ws / ".productforge/state.json"
d = json.loads(st.read_text()); d["scope"] = {"text": None, "source": None, "accepted": False}
st.write_text(json.dumps(d, indent=2) + "\n")
ov = ws / "research/product-overview.md"
t = ov.read_text()
t = t.replace("- Developer API (S-003)\n", "- Developer API (S-003)\n- Time tracking (S-001)\n"
              "- Reporting (S-002)\n- Automations (S-018)\n", 1)
start = t.index("## Recommended scope"); end = t.index("## Accepted scope")
t = t[:start] + ("## Recommended scope\n\n- Task tracking for small teams — tasks, boards, "
                 "projects, notifications\n- Team administration — workspaces, members, roles, "
                 "integrations\n\n") + t[end:]
ov.write_text(t)
EOF
python3.11 $PF research-plan --workspace ck-disc --json | grep -E '"(recommend|needs)_scope"'
```

The last line must print `"recommend_scope": true` and `"needs_scope": true`.

Start each check with `cd ~/pf-checklist/<copy> && claude --plugin-dir $REPO`. The workspace is
found from the current directory. Once the dialog has been checked, press **Esc** whenever a check
goes on to spawn agents; nothing after the dialog is being tested.

## Checks

### 1. Advancing asks once and moves exactly one stage (`ck-model`)

1. `/productforge scope`. Expected: the PRODUCT_MODEL gate summary (10/10), then a dialog
   **"Close PRODUCT_MODEL and open SCOPE_DEFINED?"** with "Advance to SCOPE_DEFINED
   (Recommended)" and "Stay in PRODUCT_MODEL".
2. Choose **Stay**. Expected: it stops without advancing. Confirm in a shell:
   `python3.11 $PF status --workspace ck-model --json | grep '"open_stage"'` → `PRODUCT_MODEL`.
3. `/productforge scope` again and choose **Advance**. Expected: one `advance` call, then the scope
   section starts (Esc here is fine). Confirm: `open_stage` is `SCOPE_DEFINED`, **not**
   `ARCHITECTURE_LOCKED`, and `.productforge/history.log` has exactly one new `advance` event.

### 2. The scope recommendation appears without `--scope` (`ck-disc`)

1. `/productforge research`. Expected: a dialog offering the two recommended scopes from
   `product-overview.md` plus Other, **before** any source pass.
2. Pick "Task tracking for small teams". Expected: a `set-scope … --accepted --source
   recommended` call, then research continues (Esc). Confirm:
   `python3.11 $PF status --workspace ck-disc --json` shows the scope text with `accepted: true`.

### 3. A scope adjustment becomes an override with your reason (`ck-scope`)

1. `/productforge scope`. Expected: the score summary (counts per decision, overrides, R1 rows),
   then **"Accept this scope (Recommended)"** / **"Adjust"**.
2. Choose **Adjust** and type, for example, "move F-010 Activity history to DEFER — not needed for
   the first release". Expected: a `pf.py override F-010 --decision "DEFER" --reason "…"` call
   with your words, a new summary, and the same dialog again.
3. Confirm: `python3.11 $PF score --workspace ck-scope --json` lists F-010 under `overrides` with
   decision `DEFER` and your reason. Choose **Accept** (the requirements pass may start; Esc).

### 4. Install offers ask and record the answer (fresh workspace)

1. In an empty directory: `/productforge https://tasklet.example --scope "task tracking"`.
   Expected: `init`, then capability resolution. Only if a capability is offered (for example
   `repo.intel`, when contributor-scout is not installed): a dialog with "Install now",
   "Continue with built-in" and "Don't ask again".
2. Choose **Continue with built-in**. Expected: nothing is installed; `deps offered <capability>`
   is recorded, so the offer does not repeat. Research then tries the network (Esc;
   `tasklet.example` does not exist).
3. If nothing was offered, note "no offer: every capability resolved" and skip.

### 5. (Optional) Architecture and plan acceptance

On `ck-scope` (its gate passes): `/productforge architect` shows the SCOPE_DEFINED → ARCHITECTURE_LOCKED
dialog (as in check 1) and, after the design pass, "Accept the architecture (Recommended)" /
"Change a decision". This spawns agents and costs tokens; skip it if checks 1–4 passed.

## Results

| Check | Dialog seen as described? | Effect confirmed with `pf.py`? | Notes |
|---|---|---|---|
| 1 Advance once |  |  |  |
| 2 Scope recommendation |  |  |  |
| 3 Override with reason |  |  |  |
| 4 Install offer |  |  |  |
| 5 Architecture (optional) |  |  |  |

Copy the table into `plans/v1.1/phase-04-interactive-verification.md` when you are done. A failure
becomes a small fix in `skills/productforge/SKILL.md` or `references/`, or a v1.2 item.
