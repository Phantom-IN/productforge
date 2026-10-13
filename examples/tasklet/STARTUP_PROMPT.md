# Startup prompt — tasklet-alt

Paste everything below into a fresh Claude Code session opened in this repository.

---

You are implementing tasklet-alt from its specification. Everything you need is in this
repository; you need no chat history.

## Step 0 — Read

Read, in order: `CLAUDE.md`, `IMPLEMENTATION_PLAN.md`, `plans/README.md`. Skim `spec/` and
`research/` only when a phase cites them.

## Step 1 — Wait

Reply with a short summary of the project and the phase list, then wait. Start work only when the
user says **"execute phase NN"**.

## Execution protocol

For "execute phase NN": follow the "Executing a phase" section of `CLAUDE.md` — one phase per
session, only that phase's tasks, tests and lint green, manual verification done, its
Definition-of-done ticked and its status set to **Done** in `plans/README.md`. Never start the next
phase unasked.
