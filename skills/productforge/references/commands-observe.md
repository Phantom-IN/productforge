# /productforge observe — procedure (v2)

Observe mode records the real product while **the user** drives it in their own account. Works
in DISCOVERY and PRODUCT_MODEL. `$PF` = `<base>/scripts/pf.py`; `<ws>` = the workspace.

## 1. Recorder (once per computer)

`python3.11 "$PF" deps --json`: if `browser.observe` resolves to `none`, run
`deps install browser.observe --json` (prints the commands and `consent_text`, installs
nothing), show the size and ask with AskUserQuestion; only on yes add `--confirmed`. Declined or
no AskUserQuestion → explain how to enable it later and stop: nothing has changed and the v1
commands are unaffected.

## 2. Consent (once per workspace, again when the text changes)

`python3.11 "$PF" observe consent --workspace <ws> --json`. If `consented` is false, show `text`
verbatim and ask with AskUserQuestion: "I consent — this is my own account (Recommended)" /
"Not now". Only on consent: `observe consent --confirmed`. Never consent for the user; without
AskUserQuestion show the text and stop.

## 3. Record

**Sign-in providers that refuse automated browsers.** Google (and some other single-sign-on
providers) block sign-in in any browser a program controls ("This browser or app may not be
secure"). ProductForge never hides that it controls the browser, so suggest instead: the product's
e-mail-and-password or GitHub sign-in, or a self-hosted instance of the product (open-source
products usually ship a Docker image). If none works, observe mode is not for that product.

Ask what the user will do and which role their account has (the domain pass needs it), then
`python3.11 "$PF" observe start [--url <start page>] --label "<first step>" --role "<role>"
--workspace <ws> --json`. Tell the user: the browser window that opened is theirs to drive; the
control panel (`panel_url`) shows the red recording dot, pause, stop and a "Now doing" box for
naming each step; ProductForge never clicks or types. Wait for the user to say they are done (or
check `observe status`), then `observe stop --workspace <ws> --json`.

## 4. Ingest

`python3.11 "$PF" observe ingest <session> --workspace <ws> --json` → one `observed-session`
source and its `OB` records (merged; `summary.json` written in the session folder). Report the
counts from the result, never typed ones.

## 5. Observation passes

Each run gets `pf.py brief --role <role> --task "Observation pass: <session>" --input
.productforge/observe/<session>/summary.json --input research/observations.md` plus the role's
usual inputs and templates; spawn the runs of one row in one message (at most
`agents.max_pending_runs`), then preflight, repair and merge them one at a time:

| Open stage | Roles (in order) |
|---|---|
| DISCOVERY | research-agent (claims) → product-analyst (surfaces) |
| PRODUCT_MODEL | product-analyst (features) → ux-analyst (workflows) → domain-architect (entities, permissions) → systems-architect (API and realtime inferences) |

## 6. Two roles for permissions

Permissions need a second session as a **lower role** (a member, a viewer): the same steps, a
second account. Offer it when `pf.py permission-gaps --json` lists unknown cells for a role the
user can sign in as. A 403 for an action is that cell's ✗; nothing else changes a cell.

Finish with the end-of-command report: `pf.py status --json` counts before and after, the new OB,
claim, step and permission-cell evidence by ID, and `pf.py check` for the open stage — the gate is
reported, never advanced.

## 7. Afterwards

`observe discard <session> --reason "…"` deletes the raw files (records keep their text; their
artifacts read as discarded); sessions older than `observe.retain_days` are pruned on start.
