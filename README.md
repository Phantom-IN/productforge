# ProductForge

> **ProductForge turns an existing software product into an evidence-backed, implementation-ready
> engineering blueprint.**

Give ProductForge a public product URL. It researches the product across public sources,
reconstructs its features, workflows, domain model, permissions and observable behaviour, keeps facts
separate from inference, reduces the product to a realistic MVP, designs an **independent**
architecture, and generates a complete phase-wise implementation plan that a fresh Claude Code
session can execute with `execute phase 00`.

ProductForge builds only the part nothing else does — a deterministic framework (stage gates, record
IDs, confidence rules, scoring, traceability) — and **reuses existing Claude Code skills and plugins**
for generic work such as deep web research, browsing JS-heavy docs, reading PDFs and analysing public
repos (with your consent to install them, and a built-in fallback for each).

It is **not** a website cloner: no proprietary code, no brand assets, no copied copy, no claims about
a target's internals without evidence. See [`IDEA.md`](IDEA.md) for the full vision.

> **Status:** v1 in planning. Nothing below is implemented yet — see [`plans/v1/`](plans/v1/README.md).

## How it will work

```text
/productforge https://example-product.com --scope "issue tracking"   # DISCOVERY
/productforge research                                                # more sources, claims, unknowns
/productforge features | workflows | model | competitors              # PRODUCT_MODEL
/productforge scope                                                   # SCOPE_DEFINED
/productforge architect                                               # ARCHITECTURE_LOCKED
/productforge finalize                                                # PHASE_PLAN_READY
/productforge status                                                  # any time
```

Stages are enforced by a state machine; each stage has a machine-checked exit gate and needs your
confirmation before advancing. Every claim has a confidence state
(`CONFIRMED / PROBABLE / INFERRED / UNKNOWN`) backed by a tiered source ledger.

## Output

```text
<your-project>/
├── README.md  IMPLEMENTATION_PLAN.md  CLAUDE.md  DEVELOPMENT.md  STARTUP_PROMPT.md
├── research/   sources, discovery ledger, unknowns, surfaces, feature matrix, workflows, inference, competitors
├── spec/       product spec, domain model, permissions, integrations, parity, architecture, ADRs, traceability
└── plans/      README ledger + phase-NN-*.md
```

## Repository map (this repo)

| Path | What |
|---|---|
| [`IDEA.md`](IDEA.md) | Product vision |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | v1 architecture — source of truth |
| [`CLAUDE.md`](CLAUDE.md) | Working contract and golden rules |
| [`DEVELOPMENT.md`](DEVELOPMENT.md) | Local development |
| [`STARTUP_PROMPT.md`](STARTUP_PROMPT.md) | Paste into a fresh Claude Code session to build v1 |
| [`plans/v1/`](plans/v1/README.md) | Phase plans for v1 |

## Roadmap

V1 public product intelligence → V2 authenticated exploration → V3 network/API observation →
V4 screenshots & video → V5 continuous parity monitoring (IDEA §44).

## License

MIT — see [`LICENSE`](LICENSE).
