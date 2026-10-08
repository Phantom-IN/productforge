# DEVELOPMENT — ProductForge

How to work on ProductForge locally. Commands become real as phases land; Phase 00 makes everything
in "Setup" and "Everyday loop" work.

## Prerequisites

- Python **3.11** available as `python3.11` (runtime scripts are stdlib-only; CI checks 3.11 and 3.12).
  macOS: `brew install python@3.11`.
- Claude Code (CLI or IDE extension) for exercising the plugin
- `make`, `git`
- Network access only for `pf.py discover` and real-product dogfooding — tests never use the network

## Setup

```bash
python3.11 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e '.[dev]'        # pytest, ruff, mypy — dev only
make check                     # should be green on a fresh clone
```

There are no environment variables. All knobs live in `skills/productforge/scripts/pflib/config.py`
(`DEFAULTS`) and can be overridden per workspace in `.productforge/config.json` or by CLI flags.

## Everyday loop

```bash
make test        # pytest -q
make lint        # ruff + mypy
make check       # compile + test + lint + fixtures-check (examples join in Phase 17)
```

`make` defaults to `PYTHON=python3.11`. To use a venv or check another version (as CI does with 3.12), pass it in:

```bash
make check PYTHON=.venv/bin/python
python3.12 -m venv .venv3.12 && .venv3.12/bin/pip install -e '.[dev]' && make check PYTHON=.venv3.12/bin/python
```

Run a single test module: `python3.11 -m pytest tests/unit/test_records.py -q`.

## Using the CLI directly

```bash
PF=skills/productforge/scripts/pf.py
python3.11 $PF init https://tasklet.example --out /tmp/tasklet --name "Tasklet Alt"
python3.11 $PF status --workspace /tmp/tasklet
python3.11 $PF validate --workspace /tmp/tasklet --json
python3.11 $PF check --workspace examples/tasklet
```

## Running the plugin in Claude Code

```bash
claude --plugin-dir /path/to/productforge
# then inside Claude Code:
/productforge status
/productforge https://some-public-product.com --scope "core area"
```

Alternative: add the repo as a local marketplace (`/plugin marketplace add /path/to/productforge`)
and install `productforge` from it. For a standalone skill install, symlink
`skills/productforge` into `~/.claude/skills/productforge` (agents then run inline — see SKILL.md).

## Reused skills & plugins (capabilities)

ProductForge delegates generic work to existing skills (see IMPLEMENTATION_PLAN §9.4). Nothing is
required — every capability has a built-in fallback — but results improve with providers installed.

```bash
python3.11 skills/productforge/scripts/pf.py deps --json                 # what is detected/resolved
python3.11 skills/productforge/scripts/pf.py deps install repo.intel     # prints the install command only
python3.11 skills/productforge/scripts/pf.py deps use research.deep builtin   # pin fallback (reproducible runs)
```

Installs run `claude plugin install <plugin>@<marketplace> --scope project` and only with
`--confirmed`; inside Claude Code the orchestrator asks you first. Restart the session to load a new
plugin. Host-provided skills (`anthropic-skills:*`) are detected by the orchestrator, not from disk.
Tests fake `$HOME` and never call the real `claude` CLI.

## Fixtures

- `tests/fixtures/workspaces/tasklet/<STATE>/` — a synthetic product ("Tasklet") frozen at each
  lifecycle state. When a phase adds an artifact or gate, extend the snapshot for that state and every
  later one (`make fixtures-check` verifies each snapshot passes `validate` for its state).
- `tests/fixtures/invalid/<CODE>.md` — one overlay per validator finding code, applied to a copy of
  the Tasklet DISCOVERY snapshot by `conftest.apply_overlay`; it must produce exactly that code.
- `tests/fixtures/http/` — canned `robots.txt`, sitemaps and HTML served by a local `http.server`
  in discover tests.
- Never put real third-party content in fixtures or `examples/`.

## Dogfooding on a real product

Write outputs outside the repo or under `.dogfood/` (gitignored). Only the summary report
(`docs/dogfood-*.md`) is committed — never the third-party research artifacts themselves.

## Debugging

- `pf.py <cmd> --json` shows the exact structure the skill consumes.
- `.productforge/history.log` (JSONL) records every transition, merge, reopen and override.
- Stage guard hook blocked a write? Run `pf.py status` — the file belongs to a stage that is not open;
  use the right command or `pf.py reopen`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `LOCK_VIOLATION` from validate | You edited a closed stage's record. Revert, or `pf.py reopen <STAGE> --reason "…"` |
| `DANGLING_REF` | A record cites an ID that does not exist — usually an un-merged staging run |
| `/productforge` not found | Plugin not loaded; check `claude --plugin-dir` path, or use the namespaced `/productforge:productforge` |
| discover returns nothing | robots.txt disallows the paths, or the site needs JS — agents fall back to WebSearch + WebFetch |
