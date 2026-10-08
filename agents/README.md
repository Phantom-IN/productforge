# Role agents

ProductForge's seven role agents (IMPLEMENTATION_PLAN.md §9.2, IDEA §33). Each agent writes only to
its staging folder (`.productforge/staging/<run-id>/`); `pf.py merge` is the only writer of canonical
files. Agent bodies arrive with the phase that first needs them — none are defined yet, so no agent
is registered by the plugin.

| Agent | Stage(s) | Implemented in |
|---|---|---|
| `research-agent` | DISCOVERY, feedback loops | Phase 06 (sources), Phase 07 (evidence) |
| `product-analyst` | DISCOVERY (surfaces), PRODUCT_MODEL (features, integrations), competitors | Phase 07 (surfaces), 08 (features), 11 (integrations), 12 (competitors) |
| `ux-analyst` | PRODUCT_MODEL (workflows) | Phase 09 |
| `domain-architect` | PRODUCT_MODEL (domain, identity, permissions) | Phase 10 |
| `systems-architect` | PRODUCT_MODEL (inference), ARCHITECTURE_LOCKED | Phase 11 (inference), 14 (design) |
| `scope-editor` | SCOPE_DEFINED | Phase 13 |
| `phase-planner` | PHASE_PLAN_READY | Phase 15 |

The shared agent contract (`_contract.md`) lands in Phase 04.
