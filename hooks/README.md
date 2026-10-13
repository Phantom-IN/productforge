# Hooks

`hooks.json` registers one **PreToolUse** hook, `stage_guard.py`, for `Write|Edit|MultiEdit|NotebookEdit`
(IMPLEMENTATION_PLAN.md §2, §7).

**Scope.** It acts only when the file being written lies inside a ProductForge workspace — a
directory with `.productforge/state.json`. Everywhere else it does nothing.

**What it blocks** (with a reason that names the right command):

- direct writes to canonical **record files** (`research/sources.md`, `spec/PRODUCT_SPEC.md`,
  `spec/decisions/ADR-*.md`, …) — changes are staged in `.productforge/staging/<run>/` and applied
  with `pf.py merge`;
- writes to artifacts owned by a **stage that is not open** — `pf.py reopen <STAGE> --reason "…"`;
- **generated** documents (`spec/TRACEABILITY.md`) and `.productforge/` itself (except staging).

**What it allows:** staging folders, the open stage's documents (e.g. `plans/README.md` while
phases are executed) and every file that is not a ProductForge artifact — the generated
project's code.

**Failure mode.** Any internal error fails open: the write is allowed and a note goes to stderr,
so a guard bug never blocks a session. Stdlib only; it runs in well under 50 ms.

**Disabling.** Disable the plugin (`/plugin disable productforge`) or remove the hook from your
settings.
