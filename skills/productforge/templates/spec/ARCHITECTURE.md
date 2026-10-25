# Architecture — {{our_name}}

**This is our architecture, not a claim about {{product_name}}.** It designs {{our_name}}'s V1 from
our requirements (`spec/PRODUCT_SPEC.md`), the architecture inferences
(`research/architecture-inference.md`) and the reconstructed domain model — nothing here describes
how {{product_name}} is built. Every component is justified by a requirement (`R-`), an inference
(`A-`) or a decision (`ADR-`); decisions live in `spec/decisions/`. `## Decisions` and
`## Requirement coverage` are generated (never edit between the markers).

## Overview

_Diagram (mermaid or ASCII) of our system: clients, services, stores, external services._

## Stack

| Concern | Choice | ADR |
|---|---|---|

## External services

_One row per third-party service the product calls, each with a `Topic: vendor` ADR. A product with
none writes a single row `none`; a capability that V1 does not need goes under
`## Not applicable topics`._

| Capability | Vendor | ADR | Test stand-in |
|---|---|---|---|

## Toolchain

_Every concern in `architecture.toolchain_concerns`, each with a pinned version and a verification
note: `YYYY-MM-DD <registry or URL>` (checked on the day against npm, PyPI, crates, Docker Hub or
the vendor page)._

| Concern | Choice | Version | Verified |
|---|---|---|---|

## Environments

_Every environment variable the system reads, and the services a developer runs locally._

| Name | Secret | Used by | Development value |
|---|---|---|---|

### Local services

_`- <service>: <image:tag>, <port>`_

## Components

_One line per component: `- <name>: <role> (R-/A-/ADR- IDs)`._

## Data storage

## Identity & tenancy

## Authentication

## Authorization

## Async processing

## Realtime

## Search

## File storage

## Integrations

## Observability

## Security

## Deployment

## Invariants

## Repository structure

```text
<our-repo>/
```

## Deviations from the target model

_Where our domain model intentionally differs from `spec/DOMAIN_MODEL.md`, citing E IDs._

## Not applicable topics

_`- <mandatory topic>: <why V1 needs no decision>` for any mandatory topic without an ADR._

## Convention-covered requirements

_`- R-NNN: <how a plain convention covers it>` for requirements no ADR needs to name._

## Decisions

<!-- pf:generated:start decisions -->
_No decisions yet._
<!-- pf:generated:end -->

## Requirement coverage

<!-- pf:generated:start coverage -->
_No decisions yet._
<!-- pf:generated:end -->
