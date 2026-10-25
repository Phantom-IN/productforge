# Product specification — tasklet-alt

What **we** build in V1: tasklet-alt, an independent product informed by the reconstructed model of
Tasklet (https://tasklet.example). Requirements (`R-`) state our behaviour — measurable where
possible — and cite the features, workflows, inferences and claims they derive from. The reduction
funnel and accepted defaults are generated (never edit between the markers).

## Product summary

tasklet-alt is task tracking for small teams: tasks on boards, grouped into projects, discussed in comments, inside one workspace per team.

## Users

Small teams (S-007): owners and admins who run the workspace, members who do the work, and guests who comment on shared tasks.

## V1 goals

- Track tasks from To do to Done on a board (R-001, R-002)
- Collaborate with comments, mentions and notifications (R-005, R-006)
- Run a workspace with roles and invitations (R-007, R-008)

## V1 non-goals

- Push-based live sync (polling in V1, see SC-009)
- Search, recurring tasks, integrations and the public API (deferred in the parity matrix)

## Requirements

### R-001 — Tasks move through a fixed status set
- Statement: Members create tasks with a title, an optional assignee, due date and reminder, and move them through To do, In progress and Done
- Derived from: W-001, W-002, W-007, D-024, A-004
- Acceptance signal: A task created on the board shows in To do and can reach Done in two moves
- Priority: must
- Features: F-001, F-002, F-003, F-004

### R-002 — Boards show tasks by status and stay current
- Statement: The board shows one column per status and reflects other members' changes within 30 s
- Derived from: W-007, A-001, D-037
- Acceptance signal: A status change made in one browser appears in another within 30 s
- Priority: must
- Features: F-008, F-009

### R-003 — Projects group tasks
- Statement: Members group tasks into projects with one owner; a task may have no project
- Derived from: W-008, D-021, D-002
- Acceptance signal: A task can be created with and without a project
- Priority: must
- Features: F-011, F-013

### R-004 — Every task keeps its history
- Statement: Every change to a task appends an entry to its activity history that is never edited
- Derived from: A-004, D-012
- Acceptance signal: Editing a task three times shows three history entries
- Priority: must
- Features: F-010

### R-005 — Members discuss tasks
- Statement: Members comment on tasks and mention other members
- Derived from: W-005, D-038
- Acceptance signal: A mention in a comment notifies the mentioned member
- Priority: must
- Features: F-014, F-015

### R-006 — Members are notified in the app
- Statement: Members get an in-app notification when assigned or mentioned, within 5 s
- Derived from: A-003, W-002
- Acceptance signal: Assigning a task produces a notification for the assignee within 5 s
- Priority: should
- Features: F-016

### R-007 — Workspaces hold members
- Statement: Every record belongs to one workspace; admins invite members by email
- Derived from: W-003, A-006, E-01
- Acceptance signal: An invited member joins and sees only that workspace's data
- Priority: must
- Features: F-020, F-021

### R-008 — Roles decide what members may do
- Statement: Owner, admin, member and guest roles are enforced on every request as in the permissions matrix
- Derived from: A-005, PR-007, E-03
- Acceptance signal: A guest cannot read a task that was not shared with them
- Priority: must
- Features: F-022

### R-009 — Sign-in uses an identity provider
- Statement: Members sign in with an emailed one-time link or a Google account through an identity provider
- Derived from: A-014, I-06
- Acceptance signal: A sign-in link works once and then expires
- Priority: must
- Features: F-024

### R-010 — Files attach to tasks
- Statement: Members attach files to tasks; files are stored by an object-storage service and served only to readers of the task
- Derived from: A-010
- Acceptance signal: A member without access to the task cannot download its file
- Priority: should
- Features: F-006

### R-011 — Billing runs through a payment provider
- Statement: Owners and admins manage the subscription through a payment provider; we never store card data
- Derived from: D-028, D-040
- Acceptance signal: Upgrading a workspace changes its plan without our system seeing card numbers
- Priority: should
- Features: F-023

## Reduction funnel

<!-- pf:generated:start funnel -->
| Step | Count |
|---|---:|
| Observed claims | 44 |
| Features reconstructed | 31 |
| Core requirements (must) | 8 |
| V1 capabilities (built or external) | 18 |
| Phases | — |
<!-- pf:generated:end -->

## Accepted defaults

<!-- pf:generated:start defaults -->
| Unknown | Question | V1 default | Impact if wrong |
|---|---|---|---|
| U-001 | How long does the product keep task activity history? | Keep activity history for the life of the task | Low — a retention job can be added later |
| U-002 | Are guest accounts included on every plan or only on paid plans? | Guests are allowed on every plan | Medium — billing rules change if guests become paid |
| U-003 | Is automatic AI triage a real feature? | No AI triage | Low |
| U-004 | Are any SDKs or components published as public repositories? | No public SDK in V1 | Low |
| U-005 | Does Tasklet sell an enterprise plan (SSO, audit log, contracts)? | No enterprise plan in V1 | Medium — SSO and audit would be needed |
| U-006 | Are there talks or podcasts by Tasklet staff about the product? | Talks are not needed for V1 | None |
| U-007 | Does Tasklet publish tutorials or courses beyond the documentation? | Official tutorials are not needed for V1 | None |
| U-008 | Are notifications delivered in-app only, or also by email and push? | In-app notifications only | Medium — email delivery may be expected |
<!-- pf:generated:end -->

## Headline features cut from V1

<!-- pf:generated:start headline-cuts -->
| Feature | Computed | Final decision | Override reason |
|---|---|---|---|
| F-019 Global search | DEFER | DEFER | Search is marketed, but V1 filters by title; full-text search is a later phase |
| F-031 Plans and pricing | DEFER | DEFER | Plans appear on the pricing page, but V1 has a single free plan |
<!-- pf:generated:end -->
