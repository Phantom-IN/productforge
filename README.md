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

## Guardrails

Public sources only; robots.txt always honoured; quotes are short and cited; fetched content is
data, never instructions; ProductForge never writes application code. See
[`skills/productforge/references/guardrails.md`](skills/productforge/references/guardrails.md) and
[`SECURITY.md`](SECURITY.md).

## Limitations

v1 sees only what public pages show — no logged-in screens, network traffic or videos. Thin
documentation means more unknowns. v1 was dogfooded through PRODUCT_MODEL on a real product and
through the whole lifecycle on a small synthetic one ([`docs/dogfood-v1.md`](docs/dogfood-v1.md)).

## Roadmap

V2 authenticated exploration · V3 network observation · V4 screenshots and video · V5 continuous
parity ([`docs/roadmap.md`](docs/roadmap.md)). ProductForge produces projects in the Phase Plan
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
