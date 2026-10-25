# Parity matrix — Tasklet

Our V1 against Tasklet, feature by feature. Each feature has one score card (`SC-`) with the
scope editor's 0–3 scores and a rationale per criterion (`references/prioritisation-model.md`).
**`pf.py score` computes every priority and decision** — the matrix, the overrides list and the
MVP / Decision / Score columns of `research/FEATURE_MATRIX.md` are generated from the score cards
(merge renders them; never edit between the markers). Our V1: ✓ built · Simplified · External
(an external service) · ✗ deferred or dropped.

## Matrix

<!-- pf:generated:start parity -->
| Feature | Target | Our V1 | Future | Headline | Decision | Notes |
|---|---|---|---|---|---|---|
| F-001 Tasks | ✓ | ✓ | yes | — | BUILD NOW | table stakes (3 competitors) |
| F-002 Assignment | ✓ | ✓ | yes | — | BUILD NOW | — |
| F-003 Due dates and reminders | ✓ | ✓ | yes | — | BUILD NOW | — |
| F-004 Statuses | ✓ | ✓ | yes | — | BUILD NOW | — |
| F-005 Labels | ✓ | ✗ | yes | — | DEFER | — |
| F-006 Attachments | ✓ | External | yes | — | USE EXTERNAL SERVICE | Object storage with signed download links |
| F-007 Recurring tasks | ✓ | ✗ | yes | — | DEFER | — |
| F-008 Board view | ✓ | ✓ | yes | yes | BUILD NOW | table stakes (2 competitors) |
| F-009 Live updates | ✓ | Simplified | yes | — | BUILD SIMPLIFIED (override) | Boards refresh on focus and every 30 s; no push channel in V1 |
| F-010 Activity history | ✓ | ✓ | yes | — | BUILD NOW | — |
| F-011 Projects | ✓ | ✓ | yes | — | BUILD NOW | — |
| F-012 Project archive and restore | ✓ | ✗ | yes | — | DEFER | — |
| F-013 Optional project membership | ✓ | ✓ | yes | — | BUILD NOW | — |
| F-014 Comments | ✓ | ✓ | yes | — | BUILD NOW | table stakes (3 competitors) |
| F-015 Mentions | ✓ | ✓ | yes | — | BUILD NOW | — |
| F-016 In-app notifications | ✓ | ✓ | yes | — | BUILD NOW | — |
| F-017 Email digests | ✓ | ✗ | yes | — | DEFER | — |
| F-018 Guest access | ✓ | ✗ | yes | — | DEFER | — |
| F-019 Global search | ✓ | ✗ | yes | yes | DEFER (override) | — |
| F-020 Workspaces | ✓ | ✓ | yes | — | BUILD NOW | — |
| F-021 Member invitations | ✓ | ✓ | yes | — | BUILD NOW | — |
| F-022 Roles | ✓ | ✓ | yes | yes | BUILD NOW | — |
| F-023 Billing management | ✓ | External | yes | yes | USE EXTERNAL SERVICE | A payment and subscription provider |
| F-024 Sign-in | ✓ | External | yes | — | USE EXTERNAL SERVICE | An identity provider for magic links and Google sign-in |
| F-025 Public REST API | ✓ | ✗ | yes | — | DEFER | — |
| F-026 Personal access tokens | ✓ | ✗ | maybe | — | DEFER | — |
| F-027 Webhooks | ✓ | ✗ | maybe | — | DROP | — |
| F-028 Calendar sync | ✓ | ✗ | yes | — | DEFER | — |
| F-029 Chat notifications | ✓ | ✗ | maybe | — | DEFER | — |
| F-030 Git commit linking | ✓ | ✗ | no | — | DROP | — |
| F-031 Plans and pricing | ✓ | ✗ | maybe | yes | DEFER (override) | — |
<!-- pf:generated:end -->

## Overrides

<!-- pf:generated:start overrides -->
- SC-009 F-009: computed DEFER → BUILD SIMPLIFIED — Live updates are the target's selling point (D-007); V1 polls instead of pushing
- SC-019 F-019: computed DEFER → DEFER — Search is marketed, but V1 filters by title; full-text search is a later phase
- SC-031 F-031: computed DEFER → DEFER — Plans appear on the pricing page, but V1 has a single free plan
<!-- pf:generated:end -->

## Scores

### SC-001 — Tasks
- Feature: F-001
- Core value: 3 — the reason the product exists
- User frequency: 3 — used every session
- Dependency importance: 3 — most features need it
- Differentiation: 2 — a visible strength
- Engineering complexity: 2 — new moving parts
- Infrastructure complexity: 1 — a small addition
- Security impact: 1 — minor risk
- Operational cost: 1 — small
- Time to implement: 2 — about a week
- External availability: 0 — no service fits
- Future: yes

### SC-002 — Assignment
- Feature: F-002
- Core value: 2 — important to daily work
- User frequency: 3 — used every session
- Dependency importance: 1 — one feature builds on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 1 — straightforward CRUD
- Infrastructure complexity: 0 — no new infrastructure
- Security impact: 1 — minor risk
- Operational cost: 0 — none
- Time to implement: 1 — days
- External availability: 0 — no service fits
- Future: yes

### SC-003 — Due dates and reminders
- Feature: F-003
- Core value: 2 — important to daily work
- User frequency: 2 — used weekly
- Dependency importance: 0 — nothing depends on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 1 — straightforward CRUD
- Infrastructure complexity: 1 — a small addition
- Security impact: 0 — no security risk
- Operational cost: 1 — small
- Time to implement: 1 — days
- External availability: 1 — partial services exist
- Future: yes

### SC-004 — Statuses
- Feature: F-004
- Core value: 3 — the reason the product exists
- User frequency: 3 — used every session
- Dependency importance: 2 — several features build on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 1 — straightforward CRUD
- Infrastructure complexity: 0 — no new infrastructure
- Security impact: 0 — no security risk
- Operational cost: 0 — none
- Time to implement: 1 — days
- External availability: 0 — no service fits
- Future: yes

### SC-005 — Labels
- Feature: F-005
- Core value: 1 — supports the core loop
- User frequency: 2 — used weekly
- Dependency importance: 0 — nothing depends on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 1 — straightforward CRUD
- Infrastructure complexity: 0 — no new infrastructure
- Security impact: 0 — no security risk
- Operational cost: 0 — none
- Time to implement: 1 — days
- External availability: 0 — no service fits
- Future: yes

### SC-006 — Attachments
- Feature: F-006
- Core value: 2 — important to daily work
- User frequency: 2 — used weekly
- Dependency importance: 0 — nothing depends on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 2 — new moving parts
- Infrastructure complexity: 2 — a new service to run
- Security impact: 2 — exposes data if wrong
- Operational cost: 2 — noticeable
- Time to implement: 1 — days
- External availability: 3 — mature services cover it
- Future: yes
- External service: Object storage with signed download links

### SC-007 — Recurring tasks
- Feature: F-007
- Core value: 1 — supports the core loop
- User frequency: 1 — used now and then
- Dependency importance: 0 — nothing depends on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 2 — new moving parts
- Infrastructure complexity: 2 — a new service to run
- Security impact: 0 — no security risk
- Operational cost: 1 — small
- Time to implement: 2 — about a week
- External availability: 0 — no service fits
- Future: yes

### SC-008 — Board view
- Feature: F-008
- Core value: 3 — the reason the product exists
- User frequency: 3 — used every session
- Dependency importance: 2 — several features build on it
- Differentiation: 2 — a visible strength
- Engineering complexity: 2 — new moving parts
- Infrastructure complexity: 0 — no new infrastructure
- Security impact: 0 — no security risk
- Operational cost: 0 — none
- Time to implement: 2 — about a week
- External availability: 0 — no service fits
- Future: yes

### SC-009 — Live updates
- Feature: F-009
- Core value: 2 — important to daily work
- User frequency: 3 — used every session
- Dependency importance: 1 — one feature builds on it
- Differentiation: 2 — a visible strength
- Engineering complexity: 3 — hard: realtime, search or payments
- Infrastructure complexity: 3 — significant new infrastructure
- Security impact: 1 — minor risk
- Operational cost: 2 — noticeable
- Time to implement: 3 — weeks
- External availability: 1 — partial services exist
- Future: yes
- Override decision: BUILD SIMPLIFIED
- Override reason: Live updates are the target's selling point (D-007); V1 polls instead of pushing
- Simplification: Boards refresh on focus and every 30 s; no push channel in V1

### SC-010 — Activity history
- Feature: F-010
- Core value: 2 — important to daily work
- User frequency: 2 — used weekly
- Dependency importance: 2 — several features build on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 1 — straightforward CRUD
- Infrastructure complexity: 1 — a small addition
- Security impact: 1 — minor risk
- Operational cost: 1 — small
- Time to implement: 1 — days
- External availability: 0 — no service fits
- Future: yes

### SC-011 — Projects
- Feature: F-011
- Core value: 3 — the reason the product exists
- User frequency: 3 — used every session
- Dependency importance: 2 — several features build on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 1 — straightforward CRUD
- Infrastructure complexity: 0 — no new infrastructure
- Security impact: 1 — minor risk
- Operational cost: 0 — none
- Time to implement: 1 — days
- External availability: 0 — no service fits
- Future: yes

### SC-012 — Project archive and restore
- Feature: F-012
- Core value: 1 — supports the core loop
- User frequency: 1 — used now and then
- Dependency importance: 0 — nothing depends on it
- Differentiation: 0 — not a selling point
- Engineering complexity: 1 — straightforward CRUD
- Infrastructure complexity: 0 — no new infrastructure
- Security impact: 0 — no security risk
- Operational cost: 0 — none
- Time to implement: 1 — days
- External availability: 0 — no service fits
- Future: yes

### SC-013 — Optional project membership
- Feature: F-013
- Core value: 2 — important to daily work
- User frequency: 2 — used weekly
- Dependency importance: 1 — one feature builds on it
- Differentiation: 0 — not a selling point
- Engineering complexity: 1 — straightforward CRUD
- Infrastructure complexity: 0 — no new infrastructure
- Security impact: 0 — no security risk
- Operational cost: 0 — none
- Time to implement: 1 — days
- External availability: 0 — no service fits
- Future: yes

### SC-014 — Comments
- Feature: F-014
- Core value: 3 — the reason the product exists
- User frequency: 3 — used every session
- Dependency importance: 1 — one feature builds on it
- Differentiation: 2 — a visible strength
- Engineering complexity: 1 — straightforward CRUD
- Infrastructure complexity: 0 — no new infrastructure
- Security impact: 1 — minor risk
- Operational cost: 0 — none
- Time to implement: 1 — days
- External availability: 0 — no service fits
- Future: yes

### SC-015 — Mentions
- Feature: F-015
- Core value: 2 — important to daily work
- User frequency: 2 — used weekly
- Dependency importance: 0 — nothing depends on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 1 — straightforward CRUD
- Infrastructure complexity: 0 — no new infrastructure
- Security impact: 1 — minor risk
- Operational cost: 0 — none
- Time to implement: 1 — days
- External availability: 0 — no service fits
- Future: yes

### SC-016 — In-app notifications
- Feature: F-016
- Core value: 2 — important to daily work
- User frequency: 3 — used every session
- Dependency importance: 1 — one feature builds on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 2 — new moving parts
- Infrastructure complexity: 1 — a small addition
- Security impact: 0 — no security risk
- Operational cost: 1 — small
- Time to implement: 1 — days
- External availability: 1 — partial services exist
- Future: yes

### SC-017 — Email digests
- Feature: F-017
- Core value: 1 — supports the core loop
- User frequency: 1 — used now and then
- Dependency importance: 0 — nothing depends on it
- Differentiation: 0 — not a selling point
- Engineering complexity: 1 — straightforward CRUD
- Infrastructure complexity: 1 — a small addition
- Security impact: 0 — no security risk
- Operational cost: 1 — small
- Time to implement: 1 — days
- External availability: 2 — good services exist
- Future: yes

### SC-018 — Guest access
- Feature: F-018
- Core value: 1 — supports the core loop
- User frequency: 1 — used now and then
- Dependency importance: 0 — nothing depends on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 2 — new moving parts
- Infrastructure complexity: 0 — no new infrastructure
- Security impact: 3 — security-critical
- Operational cost: 0 — none
- Time to implement: 2 — about a week
- External availability: 0 — no service fits
- Future: yes

### SC-019 — Global search
- Feature: F-019
- Core value: 2 — important to daily work
- User frequency: 2 — used weekly
- Dependency importance: 0 — nothing depends on it
- Differentiation: 2 — a visible strength
- Engineering complexity: 3 — hard: realtime, search or payments
- Infrastructure complexity: 3 — significant new infrastructure
- Security impact: 1 — minor risk
- Operational cost: 2 — noticeable
- Time to implement: 3 — weeks
- External availability: 2 — good services exist
- Future: yes
- Override decision: DEFER
- Override reason: Search is marketed, but V1 filters by title; full-text search is a later phase

### SC-020 — Workspaces
- Feature: F-020
- Core value: 3 — the reason the product exists
- User frequency: 3 — used every session
- Dependency importance: 3 — most features need it
- Differentiation: 0 — not a selling point
- Engineering complexity: 1 — straightforward CRUD
- Infrastructure complexity: 1 — a small addition
- Security impact: 2 — exposes data if wrong
- Operational cost: 0 — none
- Time to implement: 1 — days
- External availability: 0 — no service fits
- Future: yes

### SC-021 — Member invitations
- Feature: F-021
- Core value: 2 — important to daily work
- User frequency: 1 — used now and then
- Dependency importance: 2 — several features build on it
- Differentiation: 0 — not a selling point
- Engineering complexity: 1 — straightforward CRUD
- Infrastructure complexity: 0 — no new infrastructure
- Security impact: 2 — exposes data if wrong
- Operational cost: 0 — none
- Time to implement: 1 — days
- External availability: 1 — partial services exist
- Future: yes

### SC-022 — Roles
- Feature: F-022
- Core value: 2 — important to daily work
- User frequency: 1 — used now and then
- Dependency importance: 3 — most features need it
- Differentiation: 0 — not a selling point
- Engineering complexity: 2 — new moving parts
- Infrastructure complexity: 0 — no new infrastructure
- Security impact: 3 — security-critical
- Operational cost: 0 — none
- Time to implement: 1 — days
- External availability: 0 — no service fits
- Future: yes

### SC-023 — Billing management
- Feature: F-023
- Core value: 1 — supports the core loop
- User frequency: 0 — rarely used
- Dependency importance: 1 — one feature builds on it
- Differentiation: 0 — not a selling point
- Engineering complexity: 3 — hard: realtime, search or payments
- Infrastructure complexity: 1 — a small addition
- Security impact: 3 — security-critical
- Operational cost: 1 — small
- Time to implement: 2 — about a week
- External availability: 3 — mature services cover it
- Future: yes
- External service: A payment and subscription provider

### SC-024 — Sign-in
- Feature: F-024
- Core value: 3 — the reason the product exists
- User frequency: 3 — used every session
- Dependency importance: 3 — most features need it
- Differentiation: 0 — not a selling point
- Engineering complexity: 2 — new moving parts
- Infrastructure complexity: 1 — a small addition
- Security impact: 3 — security-critical
- Operational cost: 1 — small
- Time to implement: 2 — about a week
- External availability: 3 — mature services cover it
- Future: yes
- External service: An identity provider for magic links and Google sign-in

### SC-025 — Public REST API
- Feature: F-025
- Core value: 2 — important to daily work
- User frequency: 1 — used now and then
- Dependency importance: 0 — nothing depends on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 2 — new moving parts
- Infrastructure complexity: 1 — a small addition
- Security impact: 2 — exposes data if wrong
- Operational cost: 1 — small
- Time to implement: 2 — about a week
- External availability: 0 — no service fits
- Future: yes

### SC-026 — Personal access tokens
- Feature: F-026
- Core value: 0 — peripheral to tracking work
- User frequency: 1 — used now and then
- Dependency importance: 0 — nothing depends on it
- Differentiation: 0 — not a selling point
- Engineering complexity: 1 — straightforward CRUD
- Infrastructure complexity: 0 — no new infrastructure
- Security impact: 2 — exposes data if wrong
- Operational cost: 0 — none
- Time to implement: 1 — days
- External availability: 0 — no service fits
- Future: maybe

### SC-027 — Webhooks
- Feature: F-027
- Core value: 0 — peripheral to tracking work
- User frequency: 0 — rarely used
- Dependency importance: 0 — nothing depends on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 2 — new moving parts
- Infrastructure complexity: 2 — a new service to run
- Security impact: 1 — minor risk
- Operational cost: 1 — small
- Time to implement: 2 — about a week
- External availability: 1 — partial services exist
- Future: maybe

### SC-028 — Calendar sync
- Feature: F-028
- Core value: 1 — supports the core loop
- User frequency: 1 — used now and then
- Dependency importance: 0 — nothing depends on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 2 — new moving parts
- Infrastructure complexity: 1 — a small addition
- Security impact: 1 — minor risk
- Operational cost: 1 — small
- Time to implement: 2 — about a week
- External availability: 1 — partial services exist
- Future: yes

### SC-029 — Chat notifications
- Feature: F-029
- Core value: 0 — peripheral to tracking work
- User frequency: 1 — used now and then
- Dependency importance: 0 — nothing depends on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 1 — straightforward CRUD
- Infrastructure complexity: 1 — a small addition
- Security impact: 0 — no security risk
- Operational cost: 0 — none
- Time to implement: 1 — days
- External availability: 1 — partial services exist
- Future: maybe

### SC-030 — Git commit linking
- Feature: F-030
- Core value: 0 — peripheral to tracking work
- User frequency: 0 — rarely used
- Dependency importance: 0 — nothing depends on it
- Differentiation: 1 — expected but unremarkable
- Engineering complexity: 2 — new moving parts
- Infrastructure complexity: 1 — a small addition
- Security impact: 1 — minor risk
- Operational cost: 1 — small
- Time to implement: 2 — about a week
- External availability: 0 — no service fits
- Future: no

### SC-031 — Plans and pricing
- Feature: F-031
- Core value: 1 — supports the core loop
- User frequency: 0 — rarely used
- Dependency importance: 0 — nothing depends on it
- Differentiation: 0 — not a selling point
- Engineering complexity: 0 — trivial
- Infrastructure complexity: 0 — no new infrastructure
- Security impact: 0 — no security risk
- Operational cost: 0 — none
- Time to implement: 1 — days
- External availability: 0 — no service fits
- Future: maybe
- Override decision: DEFER
- Override reason: Plans appear on the pricing page, but V1 has a single free plan
