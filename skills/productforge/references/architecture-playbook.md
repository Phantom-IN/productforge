# Architecture playbook

How ARCHITECTURE_LOCKED designs **our** system. Only now
— with research, model and scope locked — is technology chosen.

## Rules

1. **Our architecture, not theirs.** `spec/ARCHITECTURE.md` opens with "This is our architecture, not
   a claim about <target>." Nothing in it or in an ADR describes how the target is built.
2. **Simplest thing that satisfies R.** Every component cites an `R-`, `A-` or `ADR-`
   (`UNJUSTIFIED_COMPONENT`). No component exists for a deferred or dropped feature.
3. **Every requirement is addressed** by an ADR's `Satisfies`, or by a line under
   `## Convention-covered requirements` (`- R-NNN: <how>`) when plain code covers it.
4. **Every inference gets exactly one proposal** (`AP`), even if it says "Not in V1 (SC-…)".
5. **Preferences lose to hard requirements.** A stack preference (`--stack`) is used where it fits;
   when a requirement rules it out, the ADR's `Reason` says which requirement and why.

## Mandatory topics

Each gets an ADR with `Topic` set, or a line under `## Not applicable topics` with the reason.

| Topic | Typical alternatives | Heuristics |
|---|---|---|
| identity | auto-increment, UUIDv4, UUIDv7/ULID, human keys (`ENG-123`) | expose only unguessable or scoped IDs; human keys per tenant |
| tenancy | database per tenant, schema per tenant, shared tables + row-level security | shared + RLS for small tenants; isolation by the database, not by convention |
| authn | hosted identity provider, own magic links, passwords, SSO | buy commodity security; SSO only when a requirement asks |
| authz | per-handler checks, one policy module, external policy engine | one module mirroring the permissions matrix, tested per cell |
| storage | PostgreSQL, MySQL, document store, SQLite | relational by default; one primary store in V1 |
| realtime | polling, server-sent events, WebSockets, hosted realtime | the measurable requirement decides: 30 s → polling; < 2 s → push |
| async | database-backed queue, hosted queue, Redis jobs, cron | transactional outbox; idempotent handlers |
| search | database full-text, a search engine, a hosted search service | database full-text until a requirement needs more |
| files | object storage + signed URLs, database blobs, local disk | object storage; the API checks policy before signing |
| deployment | containers on a platform, Kubernetes, serverless, one VM | fewest moving parts that separate web, API and workers |

## Invariants (`INV`)

A rule that must always hold, its reason, and **how it is enforced** — `Enforced by` starts with
`test`, `middleware`, `db-constraint`, `lint` or `review` (`INVARIANT_UNENFORCED`). Patterns:
tenancy filter on every query · authorization on every access · audit entry on every mutation ·
stable IDs never reused · idempotent jobs · credentials stored only encrypted or hashed. Invariants
become the generated project's CLAUDE.md golden rules (Phase 15).

## Repository structure

A fenced tree of real paths under `## Repository structure` (`pflib/repotree.py`): box-drawing or
indentation, directories end with `/`, `#` comments allowed, one root folder optional. Prefer
`apps/` (deployables), `packages/` (shared code), `infra/`, `tests/`, `docs/`. Generated phase plans
may only touch paths inside this tree.

## Stack table

`| Concern | Choice | ADR |` under `## Stack`; every choice named (`STACK_INCOMPLETE` on TBD, `?`,
unknown or empty).

## Build readiness

Three more sections, each behind a gate, so a build session never has to stop and ask:

- `## Toolchain` — `| Concern | Choice | Version | Verified |` for every concern in
  `architecture.toolchain_concerns`. Verify every version and container image on the day against
  its registry (npm, PyPI, crates, Docker Hub, the vendor page) with WebFetch; `Verified` reads
  `YYYY-MM-DD <registry or URL>`. Prefer actively published images (`G-AR-TOOLCHAIN`).
- `## External services` — `| Capability | Vendor | ADR | Test stand-in |`; each vendor has an ADR with
  `Topic: vendor`: vendor, why, pricing note, sandbox, webhook verification, fallback. Without a
  public API reference add "the adapter is written from `docs/vendors/<vendor>/`; finish on the stub
  until it exists". No services: one row `none` (`G-AR-EXTERNAL-SERVICES`).
- `## Environments` — `| Name | Secret | Used by | Development value |` and `### Local services`
  (`- <service>: <image:tag>, <port>`) (`G-AR-ENV-CONTRACT`).

Regulatory numbers (deadlines, rates, statutory periods) in a default need a cited source
(`DEFAULT_RULE_UNSOURCED`); no document may leave a choice open (`UNDECIDED_CHOICE`).

## Changing a decision

Never edit an accepted ADR's decision. Stage a new ADR and supersede the old one
(`### AMEND ADR-NNN` · `Status: superseded-by ADR-?1` · `Why`), then re-point proposals that cited
it (`### AMEND AP-NNN` · `Decision: ADR-?1` · `Why`; `SUPERSEDED_DECISION_CITED` warns until they
are). The superseded ADR stays in `spec/decisions/` as history.
