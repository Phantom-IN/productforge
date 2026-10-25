# Orchestrator prompt — tasklet-alt

Paste everything below into a fresh Claude Code session opened in this repository. It is the
parallel alternative to `STARTUP_PROMPT.md`: one session schedules every phase.

---

You are the orchestrator that builds **tasklet-alt** from the specification in this repository. Work through every phase in `plans/`:
- run independent phases in parallel through subagents, each in its own git worktree and branch;
- merge each finished phase into the local `main` branch;
- keep going until all phases are Done.

Spend tokens carefully at every step.

## 0. Ground rules

- **Sources of truth.** The specification is complete:
  - `CLAUDE.md` (golden rules, conventions, "Executing a phase");
  - `IMPLEMENTATION_PLAN.md`;
  - `plans/README.md` (phase table, dependency graph);
  - `plans/phase-*.md`;
  - `spec/` (product spec, architecture, decisions);
  - `DEVELOPMENT.md`.
- **Research is not a requirement.** `research/` is background only. A subagent opens it only when its phase file cites a path in it.
- **No pause between phases.** This prompt authorises you to run all phases one after another without asking between them. It replaces the "one phase per session" and "never start the next phase unasked" lines of `STARTUP_PROMPT.md`. Every other rule in `CLAUDE.md` and `STARTUP_PROMPT.md` still applies:
  - a missing provider key or vendor document means the phase finishes on its stub adapter with status "Done (stub adapter)";
  - stop and ask only for a rule the spec does not make.
- **Local only.** Never push, add a remote or open a pull request.

## 1. Setup

Do this once.

1. **Git.** If this folder is not a git repository:
   - run `git init -b main`;
   - add a `.gitignore` covering `node_modules/`, `dist/`, `.data/`, `infra/docker/.env`, `*.log` and `.DS_Store`;
   - commit everything as `spec: baseline`.
2. **Tools.** Check the runtime and services: `node -v` is 22.x and Docker is running. If a runtime is missing and a version manager is available, use it; otherwise note it in the log and continue.
3. **What you read.** Read only:
   - `CLAUDE.md`;
   - `plans/README.md`;
   - the "Accounts and keys" and "Environment variables" sections of `DEVELOPMENT.md`.

   Do not read phase files, decisions, the spec or the research yourself; subagents do that.
4. **Log.** Create `plans/ORCHESTRATION_LOG.md`, append-only, with one entry per phase:
   - phase and branch;
   - model used;
   - merge commit;
   - status (Done, or Done (stub adapter));
   - manual checks left for the owner;
   - keys or vendor documents needed.

   If this file already exists, you are resuming. Read it and the status column of `plans/README.md`, and continue from there.

## 2. Scheduling

- **Ready.** A phase is ready when every phase in its "Depends on" column is Done or "Done (stub adapter)" on `main`.
- **Parallel limit.** Run at most 3 ready phases at a time, preferring table order. Where phases form a chain, nothing runs in parallel until the chain ends.
- **Starting a phase:**
  - create its worktree with `git worktree add ../tasklet-alt-worktrees/phase-NN -b phase/NN-<slug> main`;
  - give it port slot k (1 to 3): `API_PORT=3000+10k`, `WORKER_HEALTH_PORT=3001+10k`, web port `5173+10k`, written into that worktree's `infra/docker/.env`.
- **Shared services.** These run as one Compose project, `-p tasklet-dev`, with the dev override.
  - The phase that first adds a service (01: `postgres`; 10: `objectstore`) may start it from its own worktree with `-p tasklet-dev`.
  - After each merge, restart the shared services from the main checkout.
  - All worktrees use these services. Tests create throwaway databases and unique storage key prefixes.
  - Never run `docker compose down -v`.

## 3. Phase subagents

Spawn one subagent per phase with the Agent tool.
- **sonnet** is the default.
- **haiku** is for mechanical helpers: summarising long test or lint output, formatting, small documentation tables.
- **opus** only if the same phase has failed twice on sonnet.

The brief gives paths, never file contents:

```
You implement phase NN of tasklet-alt in the git worktree <ABS_PATH> on branch phase/NN-<slug>.
Run every shell command as `cd <ABS_PATH> && …`, and edit files only inside that worktree.

Read, in order:
- <ABS_PATH>/CLAUDE.md
- <ABS_PATH>/plans/phase-NN-*.md
- only the spec sections, decisions and DEVELOPMENT.md sections that the phase file cites

Do not read research/ unless the phase cites a research path. Do not read other phase files
unless the phase names them.

Do:
- implement every task of this phase and nothing outside it (CLAUDE.md "Executing a phase");
- run `npm ci` first;
- get `npm run ci` green, plus the phase's end-to-end tests if it adds any (`npx playwright install chromium` the first time);
- carry out the scriptable parts of the manual verification;
- tick the phase file's Definition-of-done boxes, except the plans/README.md one.

Do not edit plans/README.md or plans/ORCHESTRATION_LOG.md.

Environment: the ports given for this slot. Use the shared services of Compose project
tasklet-dev and a throwaway database.

Missing provider key or vendor docs: finish on the stub adapter (DEVELOPMENT.md "Accounts and
keys") and say so.

Migrations: use the next free number on your branch in `packages/db/migrations/`; the orchestrator
renumbers on merge if two branches collide.

Helper agents: if you can spawn them, use them only for independent chunks, on sonnet or haiku,
in this same worktree, never editing the same file at the same time.

Commit in small logical commits named "phase NN: …".
If the spec lacks a rule you need, stop and report instead of guessing.

Final report, at most 12 lines:
- status (green or red);
- number of commits and files changed;
- tests run and their results;
- deviations from the phase file;
- manual checks left for the owner;
- keys or documents needed.
```

## 4. Merging

Merge one branch at a time. When a phase subagent reports green:

1. **Rebase.** In its worktree run `git rebase main`.
   - Resolve mechanical conflicts by keeping both sides: dependency manifests, route and policy registries, example env files, Compose and CI files. After any manifest or lockfile conflict, run `npm ci`.
   - Hand non-mechanical conflicts to a sonnet subagent, with only the conflicting paths.
2. **Migrations.** If the branch's new migrations in `packages/db/migrations/` collide in number with ones already on `main`, rename the branch's files to the next free numbers and commit. They have never run outside throwaway test databases.
3. **Check.** Run `npm run ci` in the worktree. A haiku helper may run it and return a summary of at most 10 lines.
   - **Red, first time:** send the summary back to the same phase subagent with SendMessage, so it fixes the problem with its context intact.
   - **Red again:** retry once on opus.
   - **Still red:** stop and ask me.
4. **Merge.**
   - Run `git checkout main && git merge --no-ff phase/NN-<slug> -m "Merge phase NN — <name>"`.
   - Then, on `main`, set the phase status in `plans/README.md` to Done or "Done (stub adapter)", append the log entry, and commit `plans: phase NN done`.
   - Run `npm run ci` on `main`. If it is red, fix it on a short-lived branch with a sonnet subagent before merging anything else.
5. **Clean up.** Run `git worktree remove ../tasklet-alt-worktrees/phase-NN` and `git branch -d phase/NN-<slug>`. If the phase changed Compose files, restart the shared services.
6. **Next.** Work out which phases are now ready and start them, up to the parallel limit.

## 5. Token discipline

- **Keep your own context lean.** Never read source code, full diffs or full test logs. Use `git log --oneline`, `git diff --stat` and exit codes. Delegate any large read to a haiku helper and ask for a summary of at most 10 lines.
- **Trust the reports.** Verify only with the CI exit code on the rebased branch and on `main`. Do not redo a subagent's work.
- **Reuse subagents.** Send fixes to the existing subagent with SendMessage instead of spawning a new one.
- **Wait, don't poll.** Background agents notify you when they finish.
- **Short updates.** After each merge, report to me in at most 5 lines.

## 6. Stop conditions

Stop and ask me when:
- a phase stays red after the fix and the opus retry;
- the spec does not make a rule that a phase needs;
- a merge conflict would change the behaviour of an already merged phase;
- Docker, disk or tooling problems block progress.

Otherwise continue until every phase in `plans/README.md` is Done. Then finish with:
- the phases done, and which of them are on stub adapters;
- the keys and vendor documents still needed;
- the manual checks left for the owner (from the log);
- the commands to run the app locally: `docker compose -p tasklet-dev up -d`, then `npm run dev`.

Begin with step 1.
