# Autonomous mode

Read this when `pf.py status --json` shows `autonomy.active: true`. The user granted autonomy for
this workspace after reading the consent text (`pf.py autonomy show`); a grant is per workspace,
hashed against that text, and ends with `pf.py autonomy revoke`. Without an active grant none of
this applies and every confirmation is asked as usual.

## What changes

| Normal behaviour | Autonomous behaviour |
|---|---|
| Transition protocol asks, then `advance --confirmed` | `advance --to <target_stage> --auto` when the gate passed; a failing gate still stops and reports |
| AskUserQuestion, or any "stop and ask" step | the option marked (Recommended) (else the one keeping the most scope and evidence), applied through `pf.py` (`config set … --reason`), then `pf.py decide`; never end a session with a question |
| Capability offers | decline each: `deps use <capability> builtin`, `deps offered <capability>`, `decide` |
| `competitors` may be skipped | always runs before `scope` (also in SCOPE_DEFINED when the signal fails); names come from the discovery pass: the top `competitors.max` with at least one citing source, then `decide` |
| `observe` on request | skipped; `decide` records it |
| Parallel agent runs | the configured maximum (`agents.max_pending_runs`, `features.max_parallel_domains`) |
| `complete --confirmed` | `complete --auto` after the PHASE_PLAN_READY gate passed |

## Recording a decision

Right after each autonomous choice:

```bash
python3.11 "$PF" decide --question "<the question you would have asked>" \
  --choice "<the option taken>" --why "<Recommended / first option / default>" \
  --command <productforge command> --workspace <ws> --json
```

A procedure never stops to ask in autonomous mode: not at a question, and not at a "choose how to
proceed" step either (raise a cap, run a dedupe pass, run a targeted research pass for open research
requests, fix a validator finding). Take the option marked Recommended and carry it out through
`pf.py` right away, for example `python3.11 "$PF" config set model.max_workflows 12 --reason "<why>"
--workspace <ws>`, then record it with `decide`. When no option is marked Recommended, take the one
that keeps the most scope and the most evidence (raise the cap rather than trim; run the pass rather
than skip it). Never end an autonomous session with a question: the last message is the
end-of-command report, with the open items listed as decisions already taken or as the next command.

Defaults: domain split → "Use these domains"; scope recommendation → the first option;
"Accept this scope", "Accept the architecture", "Accept the plan" → accept; workflow candidates →
the Recommended set. A question with no option marked Recommended is decided by the rule above, never left open.
`merge` over unrepaired preflight errors is refused (`MERGE_BEFORE_REPAIR`); in autonomous mode run
the repair passes, and only then `merge --accept-findings` with a `decide` entry.

## Limits that still hold

- One transition per invocation, only after the gate passed, and `--auto` is refused without a grant
  (`AUTONOMY_NOT_GRANTED`). Never run `advance --auto` twice in one command.
- Guardrails, evidence rules and the stage-guard hook are unchanged; write nothing outside the
  workspace.
- Never consent to observe mode, never install a provider, never use `--confirmed` for something the
  grant does not cover.

- Autonomy guards against accidents, not against something that can write
  `.productforge/state.json` directly: a process (or agent) with that write access can forge a
  grant. The hook and the hash keep honest runs honest; they are not a security boundary.

## End-of-command report

Add the decisions made in this invocation (from `pf.py decide --list`: question, choice, why) to
the usual report, and the total `status.decisions`.

## The `auto` command

`/productforge auto <url> --scope "…" [--name …] [--stack …]` takes a product URL to a completed
plan. The driver `pf.py auto start` runs each stage command as a fresh headless
`claude -p "/productforge <cmd>"` session (with `--plugin-dir`, `auto.main_model`,
`CLAUDE_CODE_SUBAGENT_MODEL=<auto.subagent_model>` and `auto.permission_args`), advances on passing
gates with `advance --auto`, retries after usage limits and stops on a stall, the retry limit or
`auto.max_sessions`. Those sessions see an active grant and follow this file.

1. **Init or resume.** With no workspace, `init <url> [--scope …] [--out …] [--name …]` as for
   `/productforge <url>`; with one, `status` and continue. Remember `workspace`.
2. **Consent.** `python3.11 "$PF" autonomy show --workspace <ws> --json`, print `text` (it names
   the permission arguments from `config`, `auto.permission_args`, default
   `--dangerously-skip-permissions`, and the `claude` binary; the hash covers that rendered text). Ask with AskUserQuestion: "Run autonomously (Recommended)" or
   "Cancel". On Cancel stop. On yes:
   `python3.11 "$PF" autonomy grant --confirmed --text-sha256 <text_sha256> --workspace <ws> --json`.
3. **Start.** Run in the background with the Bash tool (`run_in_background`):
   `python3.11 "$PF" auto start --workspace <ws> [--stack "…"] --text-sha256 <text_sha256>
   --confirmed` (`auto start` refuses to grant without the hash of the text the user saw; the
   unconfirmed `auto start` prints the full command). `--stack` takes no quotes, backticks or line
   breaks. For a terminal run print it instead, wrapped in `caffeinate -is` on macOS.
4. **Report.** Tell the user to follow it with `python3.11 "$PF" auto status --workspace <ws>` or
   `.productforge/auto.log`, and to stop it with `auto stop` (checked between sessions). Re-running
   `auto start` resumes. Without AskUserQuestion, print the command and stop: the typed
   `--confirmed` with the hash is the consent.
5. When it ends, relay the summary the driver printed (stages, sessions, retries, decisions, next
   step: `ORCHESTRATOR_PROMPT.md` when present, else `STARTUP_PROMPT.md`).
