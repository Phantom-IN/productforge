<div align="center">

# ProductForge

**Turn an existing software product into an evidence-backed, implementation-ready engineering blueprint.**

A Claude Code plugin that researches a product, reconstructs how it works, separates facts from
guesses, scopes a realistic first version, designs **your own** architecture, and writes a
phase-by-phase plan that a fresh Claude Code session can build from, starting with `execute phase 00`.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-d97757)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab)
![Runtime: stdlib only](https://img.shields.io/badge/runtime-stdlib%20only-success)

</div>

---

## Why

"Build something like X" usually starts with a vague feature list and a guessed architecture.
ProductForge replaces the guessing with a traceable chain:

```text
public source ─▶ claim ─▶ feature / workflow / inference ─▶ requirement ─▶ decision ─▶ phase
```

Every claim carries a confidence (`CONFIRMED`, `PROBABLE`, `INFERRED` or `UNKNOWN`), assigned by
mechanical rules over tiered sources. Every gap becomes an explicit unknown with a default for
version 1. Every phase of the final plan can be traced back to the evidence behind it
(`pf.py explain R-007`).

**It is not a website cloner.** It copies no proprietary code, brand assets or text. It makes no
claim about how a product is built internally without evidence that states it, and your product
gets its own name.

## How it works

ProductForge moves a workspace through five stages. Each stage has a machine-checked exit gate, and
ProductForge asks you before it closes one:

| Stage | Command | What happens |
|---|---|---|
| **DISCOVERY** | `/productforge <url>` · `research` | Finds and tiers public sources (docs, help center, changelog, pricing, API docs, reviews…), extracts claims and unknowns, maps product surfaces |
| **PRODUCT_MODEL** | `features` · `workflows` · `model` · `competitors` | Feature matrix by domain, user workflows (observed vs. implied system steps), domain model, roles × permissions, integrations, architecture inferences, optional competitor signals |
| **SCOPE_DEFINED** | `scope` | Scores every feature; a script applies the decision rules (build now, simplify, use an external service, defer, drop). You accept or adjust; then requirements and V1 defaults are written |
| **ARCHITECTURE_LOCKED** | `architect [--stack "…"]` | An **independent** architecture for *your* product: stack, ADRs with alternatives, invariants with enforcement, repository tree |
| **PHASE_PLAN_READY** | `finalize` | Generates the project: `README`, `IMPLEMENTATION_PLAN`, `CLAUDE.md`, `DEVELOPMENT`, `STARTUP_PROMPT` and lint-checked phase files, then traces every requirement to a phase |

The model does the judgment. Deterministic, standard-library Python scripts (`pf.py`) handle
state, IDs, merging, validation, scoring, gates, phase lint and traceability. Files hold the memory,
so you can stop and resume at any time.

## Install

You need **[Claude Code](https://claude.com/claude-code)** and **Python 3.11 or newer**, available
as `python3.11`. Nothing else is required: ProductForge's scripts use only the standard library.

In Claude Code:

```text
/plugin marketplace add Phantom-IN/productforge
/plugin install productforge@productforge
```

Or from a terminal:

```bash
claude plugin marketplace add Phantom-IN/productforge
claude plugin install productforge@productforge
```

To try it from a clone without installing:

```bash
git clone https://github.com/Phantom-IN/productforge.git
claude --plugin-dir ./productforge
```

## Quick start

```text
/productforge https://example-product.com --scope "issue tracking" --name "Our Name"
```

This creates a workspace folder and starts DISCOVERY. Then follow the stages:

```text
/productforge research        # until the DISCOVERY gate passes
/productforge features        # asks before closing DISCOVERY
/productforge workflows
/productforge model           # domain, permissions, integrations, inferences
/productforge scope           # review the computed scope: accept or adjust
/productforge architect --stack "Next.js, PostgreSQL"   # stack preference is optional
/productforge finalize        # the generated project and its phases
```

You can run `/productforge status` at any time. It shows the counts, the open stage, gate progress and
the next command. When the plan is ready, open a **new** Claude Code session in the generated
folder, paste `STARTUP_PROMPT.md`, and say `execute phase 00`.

> **Tip.** Large products are scoped: give `--scope` up front, or ProductForge recommends one when
> the product has more major areas than one research pass can cover well.

### All commands

| Command | Stage | Purpose |
|---|---|---|
| `/productforge <url> [--scope "…"] [--name "…"] [--out DIR]` | — | Create a workspace and begin research |
| `/productforge research` | DISCOVERY | More sources, claims, unknowns and surfaces |
| `/productforge features` · `workflows` · `model` · `competitors` | PRODUCT_MODEL | Build the product model |
| `/productforge auto <url> --scope "…" [--name "…"] [--stack "…"]` | all | Run every stage unattended (see Autonomous mode) |
| `/productforge observe` | DISCOVERY or PRODUCT_MODEL | Record the product as **you** use it (see below) |
| `/productforge scope` | SCOPE_DEFINED | Prioritise, decide V1, write requirements |
| `/productforge architect [--stack "…"]` | ARCHITECTURE_LOCKED | Design our architecture |
| `/productforge finalize` | PHASE_PLAN_READY | Generate the project and phases |
| `/productforge status` | any | Where things stand and what to do next |
| `/productforge reopen <STAGE> --reason "…"` | any | Go back to an earlier stage; later stages become stale |

## What you get

```text
<your-project>/
├── README.md  IMPLEMENTATION_PLAN.md  CLAUDE.md  DEVELOPMENT.md  STARTUP_PROMPT.md
├── research/   what the target does, with evidence
│   ├── sources.md  DISCOVERY_LEDGER.md  UNKNOWNS.md  product-surfaces.md
│   ├── FEATURE_MATRIX.md  workflows/  architecture-inference.md  COMPETITORS.md
│   └── observations.md            (observe mode)
├── spec/       what *we* build
│   ├── PRODUCT_SPEC.md  PARITY_MATRIX.md  DOMAIN_MODEL.md  PERMISSIONS_MATRIX.md
│   ├── INTEGRATIONS.md  ARCHITECTURE.md  decisions/ADR-*.md  TRACEABILITY.md
└── plans/      README.md (the phase ledger) + phase-NN-*.md
```

See **[`examples/tasklet/`](examples/README.md)**, a complete workspace for a fictional task tracker
that passes every check:

```bash
python3.11 skills/productforge/scripts/pf.py explain R-010 --workspace examples/tasklet
```

## Autonomous mode (optional)

One command takes a product URL to a completed, build-ready plan:

```
/productforge auto https://example.com --scope "task tracking" --name mytracker
```

ProductForge shows what autonomy covers and asks once. After your yes, a driver
(`pf.py auto start`) runs **one fresh headless Claude session per stage command**, advances each
stage when its gate passes, and logs every choice it makes for you (`pf.py decide --list`: it takes
the option marked Recommended, declines capability installs, researches competitors and skips
observe). Gates still decide every transition.

- **What it starts:** `claude -p` sessions with `--plugin-dir`, the orchestrator on `auto.main_model`
  (`opus`), role agents on `auto.subagent_model` (`sonnet`), and `auto.permission_args`
  (default `--dangerously-skip-permissions`, named in the consent text; set a stricter mode in
  `.productforge/config.json`).
- **Cost and time:** expect many sessions and several hours for a large product, mostly agent runs
  on the subagent model; usage limits make it wait `auto.retry_wait_seconds` and retry. Set
  `research.max_sources` and the other caps low for a first try.
- **Follow, stop, resume:** `pf.py auto status` (or `.productforge/auto.log`); `pf.py auto stop`
  stops between sessions; re-running `auto start` resumes where the workspace is. `pf.py auto start
  --dry-run` prints the next session and changes nothing. `pf.py autonomy revoke` ends the grant.
- **Stops, with a reason:** a stall (`auto.max_stalls` sessions with no change), the retry limit, the
  session limit (`auto.max_sessions`), a refused command or a failing gate on `advance`.

It ends with `complete --auto`; ProductForge still writes no application code.

## Observe mode (optional)

`/productforge observe` records the product **in your own account**. ProductForge opens a real
browser window that you drive, plus a local control panel with a recording indicator, pause and
stop buttons, and a "Now doing" box for naming each step. It **never clicks or types for you**. What the product does
becomes first-hand evidence:
- screens, and the actions you take on them;
- API request and response **shapes** (field names and types, never values);
- realtime message shapes;
- the 403s a lower-role account receives.

Workflows gain screen-level steps, architecture inferences gain observed API shapes, and unknown
permission cells get settled.

- **Consent first.** ProductForge asks before installing Playwright and Chromium (about 540 MB, in
  their own virtual environment) and before the first session. The consent text says plainly that
  the product's terms may forbid this, and that the decision is yours.
- **Redacted before anything touches disk.** It never stores:
  - passwords, payment fields, cookies, tokens or anything you type;
  - request or response bodies (only their field shapes are kept);
  - the names of list items, or the text of anything you click (only where you clicked);
  - traffic to hosts other than the product's own.
- **Local only.** Sessions live in the workspace's `.productforge/observe/` (git-ignored). They are
  never merged or published, and are deleted after 30 days or with `pf.py observe discard`.
- **Internals stay UNKNOWN.** An observation shows behaviour, never the database or framework
  behind it; asserting one is a validation error.
- **Sign-in.** Google and some other single-sign-on providers refuse automated browsers.
  ProductForge does not work around that. Use e-mail and password, GitHub sign-in, or a self-hosted
  instance of the product.

Full details: [`SECURITY.md`](SECURITY.md#observe-mode-v2-opt-in) ·
[`references/commands-observe.md`](skills/productforge/references/commands-observe.md).

## How it stays trustworthy

- **Stages are enforced.** Closed stages are append-only; changing one means `reopen`, which marks
  later stages stale. One transition per command, and only after you confirm — per transition, or once for the whole run through a recorded, revocable autonomy grant (`pf.py autonomy grant`).
- **Scripts do the arithmetic.** IDs, merges, scores, decisions, gate verdicts, phase lint and
  traceability come from `pf.py`, never from the model.
- **Agents only stage.** Seven role agents (research, product, UX, domain, scope, systems,
  phase planning) write to a staging folder; `pf.py merge` is the only writer of canonical
  records, after a preflight validation.
- **Target ≠ ours.** `research/` describes the product you studied; `spec/` describes the one you
  will build. Our architecture is never presented as a claim about theirs.
- **A stage-guard hook** blocks direct edits to canonical records, closed stages and session files
  inside a workspace, and does nothing anywhere else.

## Reuses what you already have

ProductForge delegates generic work to skills and plugins you have installed, with a built-in
fallback for every required capability. It installs nothing without your explicit consent.

| Capability | Reused when available | Fallback |
|---|---|---|
| Multi-source web research | `deep-research` skill | built-in research agent |
| JavaScript-heavy pages | browser skills | built-in fetching |
| PDFs (security and trust docs) | `pdf` skill | built-in |
| Public repositories of the target | [contributor-scout](https://github.com/Phantom-IN/contributor-scout) repository intelligence | built-in |
| Architecture diagrams | diagramming skill | Mermaid in Markdown |
| Knowledge graph / publishing | `graphify`, Artifacts | none (optional) |

Check what's in use with `pf.py deps --json`.

## Guardrails

Public sources only (and, in observe mode, your own account). `robots.txt` is always honoured.
Quotes are short and cited, and fetched content is treated as data, never as instructions.
ProductForge never writes application code; it writes the plan. See
[`guardrails.md`](skills/productforge/references/guardrails.md) and [`SECURITY.md`](SECURITY.md).

## Configuration

Every knob has a default, and can be overridden per workspace in `.productforge/config.json`
(source caps, gate thresholds, scoring weights, phase limits, observe-mode screenshots…). The full
list is in [`docs/configuration.md`](docs/configuration.md).

## Limitations

- It sees only what public pages show, or, in observe mode, what your own account and role can
  reach. Thin documentation means more unknowns.
- A full run on a large product uses a lot of model time. Scope it, and expect each stage to take
  a while.
- Proven end to end on a real product (an open-source web-analytics tool) and on a synthetic one;
  the findings and fixes are in [`docs/`](docs/README.md).

## Development

```bash
python3.11 -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'
make check        # compile + tests + ruff + mypy + fixture and example validation
```

[`DEVELOPMENT.md`](DEVELOPMENT.md) covers the toolchain, the observe-mode test setup and plugin
evals. [`CLAUDE.md`](CLAUDE.md) holds the golden rules and extension recipes, and
[`CONTRIBUTING.md`](CONTRIBUTING.md) explains how to contribute. Release notes are in
[`CHANGELOG.md`](CHANGELOG.md).

## License

[MIT](LICENSE) © Vaibhav Vanage
