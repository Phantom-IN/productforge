# Competitors — Tasklet

A shallow look at Tasklet's category: which competitors exist, what every product in the
category offers (table stakes), what sets products apart, and what users complain about. This is a
lens for scoping, **not** a second discovery and never a source of copy — competitors are
paraphrased and cited, and no competitor's source supports a claim about Tasklet.

Competitor sources live in `sources.md` with `Relevant area: competitor:<C-ID>`. The tables below
are generated from the records by `pf.py render` (merge does it automatically) — never edit between
the markers.

## Landscape

<!-- pf:generated:start landscape -->
| C | Name | Positioning | Pricing | Table-stakes overlaps |
|---|---|---|---|---|
| C-01 | Taskmate | Task lists with built-in time tracking | Free tier; per-seat paid plans | 3 |
| C-02 | Doable | Fast search across everything a team tracks | Per-seat subscription | 3 |
| C-03 | Listwise | Lists first, with developer integrations | Free for small teams; paid add-ons | 2 |
<!-- pf:generated:end -->

## Signals by feature

<!-- pf:generated:start signals -->
| F | Feature | Offered by | Table stakes | Differentiator |
|---|---|---|---|---|
| F-001 | Tasks | 3 | yes | 0 |
| F-008 | Board view | 2 | yes | 0 |
| F-014 | Comments | 3 | yes | 0 |
| F-019 | Global search | 1 | rare | 1 |
| F-030 | Git commit linking | 1 | rare | 0 |
<!-- pf:generated:end -->

## Missing in target

<!-- pf:generated:start absent -->
| Capability | Competitors | Signal |
|---|---|---|
| Time tracking | C-01 | FS-004 |
<!-- pf:generated:end -->

## Records

### C-01 — Taskmate
- Name: Taskmate
- URL: https://taskmate.example/
- Positioning: Task lists with built-in time tracking
- Target users: Freelancers and small agencies
- Pricing model: Free tier; per-seat paid plans
- Table-stakes features: F-001, F-008, F-014
- Differentiators: Time tracking on every task
- Common complaints: Setup is slow for new teams (S-021)
- Evidence: S-023, S-024
- Confidence: CONFIRMED

### C-02 — Doable
- Name: Doable
- URL: https://doable.example/
- Positioning: Fast search across everything a team tracks
- Target users: Small product teams
- Pricing model: Per-seat subscription
- Table-stakes features: F-001, F-008, F-014
- Differentiators: Search across tasks, files and comments
- Common complaints: Mobile app lags behind the web app (S-026)
- Evidence: S-025
- Confidence: CONFIRMED

### C-03 — Listwise
- Name: Listwise
- URL: https://listwise.example/
- Positioning: Lists first, with developer integrations
- Target users: Engineering teams
- Pricing model: Free for small teams; paid add-ons
- Table-stakes features: F-001, F-014
- Differentiators: Links commits and pull requests to tasks
- Common complaints: Sync between devices is unreliable (S-028)
- Evidence: S-027
- Confidence: CONFIRMED

## Feature signals

### FS-001 — Tasks is table-stakes
- Feature: F-001
- Signal: table-stakes
- Competitors: C-01, C-02, C-03
- Evidence: S-023, S-025, S-027
- Notes:

### FS-002 — Global search is differentiator
- Feature: F-019
- Signal: differentiator
- Competitors: C-02
- Evidence: S-025
- Notes: Doable markets search as its edge

### FS-003 — Git commit linking is rare
- Feature: F-030
- Signal: rare
- Competitors: C-03
- Evidence: S-027
- Notes:

### FS-004 — Time tracking is absent-in-target
- Feature: Time tracking
- Signal: absent-in-target
- Competitors: C-01
- Evidence: S-023
- Notes: Taskmate's headline feature
