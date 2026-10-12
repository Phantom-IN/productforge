# Product-model playbook

How PRODUCT_MODEL turns research into a model of the target (IMPLEMENTATION_PLAN.md §12). Each
artifact describes the **target as observed**; *our* design starts at SCOPE_DEFINED. Field grammars
live in `record-format.md`; confidence rules in `confidence-rules.md`.

| Order | Command | Artifact | Records | Agent |
|---|---|---|---|---|
| 1 | `features` | `research/FEATURE_MATRIX.md` | `F` | product-analyst |
| 2 | `workflows` | `research/workflows/W-*.md` | `W` | ux-analyst |
| 3 | `model` (domain) | `spec/DOMAIN_MODEL.md`, `spec/PERMISSIONS_MATRIX.md` | `E`, `RL`, `PR` | domain-architect |
| 4 | `model` (integrations) | `spec/INTEGRATIONS.md` | `I` | product-analyst |
| 5 | `model` (inference) | `research/architecture-inference.md` | `A` | systems-architect |

Product surfaces (`PS`) come from DISCOVERY; every one must map to a feature.

## Features

One `F` per user-visible capability, in one domain, at most three levels deep. Evidence is claims;
a capability implied but never stated is `INFERRED` with `Derived from`. Scoring fields never go on
features (they live in SC score cards at SCOPE_DEFINED).

## Workflows

A workflow is one `W` header plus numbered steps, each `[observed]` (with `S`/`D` evidence) or
`[implied-system]` (what the system must do: authorize, validate, persist, audit, index, publish a
realtime event, notify, call an integration, enqueue a job). The implied steps are the point: they
expose requirements a feature list hides. Example:

```text
1. [observed] Member adds a task to a status column — D-037
5. [implied-system] Persist the task with its workspace and optional project — F-001, D-002
7. [implied-system] Index the task for search — F-019
```

## Domain model and identity

An entity has identity and a lifecycle. Record the identity users can see (`ENG-123` in URLs, IDs in
the API) — never a guess about database keys. The containing entity is a required `N:1` link, so the
generated tree roots at the tenancy entity (workspace, team, organization). Deletion semantics come
from docs (trash, archive); otherwise say "inferred" and add a U record. Identity is a high-impact
decision: each entity's scheme becomes an ADR candidate.

## Roles and permissions

Roles come from pricing, help and docs. One `PR` rule per resource × action with a cell for **every**
role: ✓, ✗, `Limited` (explained in `Limited means`) or `?` (explained by a U record). Every entity
users can change has at least one rule. A `?` is an honest answer; a guessed ✓ is not.

## Integrations

One `I` per provider or mechanism — third-party integrations, the public API, webhooks, single
sign-on, email. Direction is from the product's side (`inbound`: the other system calls in).
"Not documented" is a valid value for authentication or failure behaviour.

## Architecture inference

An `A` record links an observation to our requirement:

```markdown
### A-001 — Task changes reach other users live
- Area: realtime
- Observation: Edits by one user appear for others without a reload
- Evidence: D-007
- Confidence: CONFIRMED
- Engineering implication: The server pushes changes to connected clients
- Target implementation: UNKNOWN
- Our requirement: Task changes must be visible to other connected clients within 2 s
- Derived from: W-001, W-007, F-009, D-007
```

Rules (validated):

- **No architecture hallucination.** `Target implementation` is `UNKNOWN` unless a cited CONFIRMED
  claim with Tier ≤ 2 evidence states it (`TARGET_IMPL_UNSUPPORTED`). "Linear probably uses
  Postgres" never appears anywhere.
- **Behaviour, not technology.** Technology names in `Observation` / `Engineering implication`
  without qualifying evidence are flagged (`TECH_ASSERTION_IN_OBSERVATION`, warn).
- **Measurable.** `Our requirement` carries a number and unit or a must/never rule
  (`REQUIREMENT_NOT_MEASURABLE`, warn). When the target's figure is unknown, the number is ours.
- **Coverage.** Every workflow with `[implied-system]` steps is cited by at least one `A`
  (`G-PM-INFERENCE-COMPLETE`; see `## Workflow coverage`).
- `Proposed implementation` is reserved for ARCHITECTURE_LOCKED (`FIELD_NOT_YET_ALLOWED`).

## Gate

`pf.py check` reports the PRODUCT_MODEL gate (`stage-gates.md`). `/productforge model` never
advances; the next stage's command (`/productforge scope`) asks before closing PRODUCT_MODEL.
