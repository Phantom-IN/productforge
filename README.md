# ProductForge

> **ProductForge turns an existing software product into an evidence-backed, implementation-ready
> engineering blueprint.**

Give ProductForge a public product URL. It researches the product across public sources,
reconstructs its features, workflows, domain model, permissions and observable behaviour, keeps
facts separate from inference, reduces the product to a realistic MVP, designs an **independent**
architecture, and writes a complete phase-wise plan that a fresh Claude Code session can execute
with `execute phase 00`.

It is **not** a website cloner: no proprietary code, no brand assets, no copied text, no claims
about a target's internals without evidence, and your product gets its own name.

## Install

```text
/plugin marketplace add Phantom-IN/productforge
/plugin install productforge@phantom-in
```

Or run it from a checkout: `claude --plugin-dir /path/to/productforge`. ProductForge needs
**Python 3.11** (`python3.11`); its scripts use only the standard library.

## Use

```text
/productforge https://example-product.com --scope "issue tracking" --name "Our Name"   # DISCOVERY
/productforge research                                                  # more sources, claims, unknowns
/productforge features | workflows | model | competitors                # PRODUCT_MODEL
/productforge scope                                                     # SCOPE_DEFINED
/productforge architect --stack "Next.js, PostgreSQL"                   # ARCHITECTURE_LOCKED
/productforge finalize                                                  # PHASE_PLAN_READY
/productforge status | reopen <STAGE> --reason "…"                      # any time
```

Each stage has a machine-checked exit gate, and ProductForge asks before it closes one. Then open a
new Claude Code session in the generated folder, paste `STARTUP_PROMPT.md`, and say
`execute phase 00`.

## What you get

```text
<your-project>/
├── README.md  IMPLEMENTATION_PLAN.md  CLAUDE.md  DEVELOPMENT.md  STARTUP_PROMPT.md
├── research/   sources, discovery ledger, unknowns, surfaces, feature matrix, workflows,
│               architecture inference, competitors — what the target does, with evidence
├── spec/       product spec, domain model, permissions, integrations, parity matrix,
│               architecture, ADRs, traceability — what *we* build
└── plans/      the phase ledger + phase-NN-*.md
```

See [`examples/tasklet/`](examples/README.md) for a complete synthetic example.

## How it stays trustworthy

- **Stages are enforced** (DISCOVERY → PRODUCT_MODEL → SCOPE_DEFINED → ARCHITECTURE_LOCKED →
  PHASE_PLAN_READY). Closed stages are append-only; changing one means `reopen`, which marks later
  stages stale.
- **Every claim has a confidence** — CONFIRMED, PROBABLE, INFERRED or UNKNOWN — decided by
  mechanical rules over tiered sources. Gaps become explicit unknowns with V1 defaults.
- **Scripts do the arithmetic.** IDs, merges, scores, decisions, gates, phase lint and
  traceability come from `pf.py`, never from the model.
- **Traceability end to end:** source → claim → feature/workflow/inference → requirement →
  decision → phase (`pf.py explain R-007`).
- **A stage guard hook** blocks direct edits to canonical records and closed stages inside a
  workspace, and does nothing anywhere else.

ProductForge reuses existing skills and plugins for generic work (deep research, browsing JS-heavy
docs, PDFs, public repositories) when they are installed — only with your consent — and falls back
to its own agents otherwise.

## Observe mode (v2, opt-in)

`/productforge observe` lets you record the product **in your own account**: ProductForge opens a
real browser window that you drive (it never clicks or types for you) plus a local control panel
with a recording dot, pause, stop and a "now doing" box. What the product does becomes first-hand
evidence: screens, your actions, API request/response *shapes*, realtime messages and the 403s a
lower role gets — so workflows gain screen-level steps, API inferences gain observed shapes and
unknown permission cells get settled.

- Asks before installing (Playwright and Chromium, about 540 MB, in their own venv) and before the
  first session; the consent text says plainly that the product's terms may forbid this and that
  the decision is yours.
- Redacted before anything touches disk: no passwords, payment fields, cookies, tokens or typed
  values; bodies become field shapes; names of list items are masked; only the product's hosts.
- Local only: sessions live in the workspace's `.productforge/observe/` (git-ignored), are never
  merged or published, and are deleted after 30 days or with `pf.py observe discard`.
- Internals stay UNKNOWN: an observation shows behaviour, never the database or framework
  (`INTERNALS_FROM_OBSERVATION`).

Details: [`SECURITY.md`](SECURITY.md#observe-mode-v2-opt-in) and
[`references/commands-observe.md`](skills/productforge/references/commands-observe.md).

## Guardrails

Outside observe mode, public sources only; robots.txt always honoured; quotes are short and cited; fetched content is
data, never instructions; ProductForge never writes application code. See
[`skills/productforge/references/guardrails.md`](skills/productforge/references/guardrails.md) and
[`SECURITY.md`](SECURITY.md).

## Limitations

Without observe mode ProductForge sees only what public pages show; observe mode sees only what
your own account and role can reach, and no video. Thin
documentation means more unknowns. v1 was dogfooded through PRODUCT_MODEL on a real product and
through the whole lifecycle on a small synthetic one ([`docs/dogfood-v1.md`](docs/dogfood-v1.md)).

## Roadmap

V2 observe mode (authenticated exploration, network observation and screenshots in one
feature) · V5 continuous parity ([`docs/roadmap.md`](docs/roadmap.md)). ProductForge produces projects in the Phase Plan
Method format — the same one this repository was built with ([`plans/v1/`](plans/v1/README.md)).

## Repository

| Path | What |
|---|---|
| [`IDEA.md`](IDEA.md) | Product vision |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | Architecture — source of truth |
| [`CLAUDE.md`](CLAUDE.md) | Working contract and golden rules |
| [`DEVELOPMENT.md`](DEVELOPMENT.md) · [`CONTRIBUTING.md`](CONTRIBUTING.md) | Developing ProductForge |
| [`plans/v1/`](plans/v1/README.md) | The phases v1 was built in |
| [`CHANGELOG.md`](CHANGELOG.md) | Releases |

## License

MIT — see [`LICENSE`](LICENSE).
