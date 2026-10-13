# Examples

## `tasklet/` — a complete synthetic workspace

A ProductForge workspace for **Tasklet**, an invented task tracker on `.example` domains, at
PHASE_PLAN_READY. It is generated from the test fixtures (`tests/fixtures/build_tasklet.py`), so
it always passes `pf.py check`, `lint-phases` and `trace` (`make example`). No real product content
is involved.

| Look at | To see |
|---|---|
| `research/sources.md`, `research/DISCOVERY_LEDGER.md` | tiered sources and claims with confidence |
| `research/FEATURE_MATRIX.md`, `research/workflows/` | features by domain; workflows with observed vs implied-system steps |
| `spec/DOMAIN_MODEL.md`, `spec/PERMISSIONS_MATRIX.md` | entity tree, identity table, role × action matrix |
| `research/architecture-inference.md` | behaviour → our measurable requirements, target internals UNKNOWN |
| `spec/PARITY_MATRIX.md`, `spec/PRODUCT_SPEC.md` | script-computed scope decisions, requirements, funnel |
| `spec/ARCHITECTURE.md`, `spec/decisions/` | our stack, ADRs, invariants, repository tree |
| `IMPLEMENTATION_PLAN.md`, `CLAUDE.md`, `plans/` | the generated project and its 13 phases |
| `spec/TRACEABILITY.md` | every requirement's chain from source to phase |

Walk one chain:

```bash
python3.11 skills/productforge/scripts/pf.py explain R-010 --workspace examples/tasklet
python3.11 skills/productforge/scripts/pf.py status --workspace examples/tasklet
```
