# Architecture inference — Tasklet

Observed behaviour of Tasklet translated into engineering requirements **for our system**.
We are not claiming to know the target's internal architecture; we derive what *our* architecture
must support. Every `A-` record pairs an observation (with evidence) with the implication and our
measurable requirement. `Target implementation` stays `UNKNOWN` unless a CONFIRMED claim backed by
a Tier ≤ 2 source states it; how *we* implement it is decided later (ARCHITECTURE_LOCKED).

`## Requirement areas` and `## Workflow coverage` are generated from the records by `pf.py render`
(merge does it automatically) — never edit between the markers.

## Requirement areas

<!-- pf:generated:start areas -->
- **async**
  - A-009 Daily digests are scheduled
- **audit**
  - A-004 Every task keeps its history
- **authn**
  - A-014 Two sign-in methods
- **authz**
  - A-005 Guests see only what is shared with them
- **files**
  - A-010 Files attach to tasks
- **integrations**
  - A-007 Webhooks report task changes
  - A-008 Due dates sync to calendars
  - A-013 Commits close tasks
- **notifications**
  - A-003 Assignment notifies the assignee
- **performance**
  - A-015 API lists page with cursors
- **realtime**
  - A-001 Task changes reach other users live
- **search**
  - A-002 One search spans tasks and projects
- **security**
  - A-011 Customer data is encrypted at rest
- **storage**
  - A-012 Archive is reversible
- **tenancy**
  - A-006 The workspace bounds all data
<!-- pf:generated:end -->

## Workflow coverage

<!-- pf:generated:start workflow-coverage -->
| W | Workflow | Implied system steps | Requirements surfaced | A refs |
|---|---|---|---|---|
| W-001 | Create a task | 6 | 4 | A-001, A-003, A-004 |
| W-002 | Assign a task | 3 | 2 | A-003 |
| W-003 | Invite a member | 3 | 2 | A-005, A-006, A-014 |
| W-004 | Search the workspace | 2 | 2 | A-002 |
| W-005 | Comment on a task | 3 | 1 | A-005 |
| W-006 | Connect the calendar integration | 2 | 2 | A-008 |
| W-007 | Change a task's status | 2 | 1 | A-001, A-004 |
| W-008 | Archive a project | 1 | 1 | A-012 |
<!-- pf:generated:end -->

## Records

### A-001 — Task changes reach other users live
- Area: realtime
- Observation: Edits by one user appear for others without a reload
- Evidence: D-007
- Confidence: CONFIRMED
- Engineering implication: The server pushes changes to connected clients
- Target implementation: UNKNOWN
- Our requirement: Task changes must be visible to other connected clients within 2 s
- Derived from: W-001, W-007, F-009, D-007

### A-002 — One search spans tasks and projects
- Area: search
- Observation: One search box finds both tasks and projects
- Evidence: D-036
- Confidence: CONFIRMED
- Engineering implication: A combined index over several entity types
- Target implementation: UNKNOWN
- Our requirement: Search must return tasks and projects together; a new task must be searchable within 5 s
- Derived from: W-004, F-019, D-043

### A-003 — Assignment notifies the assignee
- Area: notifications
- Observation: Members are notified in-app when a task is assigned to them
- Evidence: D-019
- Confidence: CONFIRMED
- Engineering implication: Notifications are produced from task events
- Target implementation: UNKNOWN
- Our requirement: A new assignee must get an in-app notification within 5 s
- Derived from: W-002, W-001, F-016

### A-004 — Every task keeps its history
- Area: audit
- Observation: Each task shows a history of its changes
- Evidence: D-012
- Confidence: CONFIRMED
- Engineering implication: An append-only activity log per task
- Target implementation: UNKNOWN
- Our requirement: Every task change must append an activity entry that is never edited
- Derived from: W-001, W-007, F-010, E-11

### A-005 — Guests see only what is shared with them
- Area: authz
- Observation: Guests can comment only on tasks shared with them
- Evidence: D-004
- Confidence: CONFIRMED
- Engineering implication: Every read and write is checked against the actor's role
- Target implementation: UNKNOWN
- Our requirement: Every request must be authorized by workspace role; a guest must never read an unshared task
- Derived from: W-005, W-003, PR-007, PR-010

### A-006 — The workspace bounds all data
- Area: tenancy
- Observation: Members and projects belong to a workspace
- Evidence: D-025
- Confidence: CONFIRMED
- Engineering implication: Every record carries its workspace
- Target implementation: UNKNOWN
- Our requirement: Every record must belong to exactly one workspace; no query may cross workspaces
- Derived from: W-003, E-01

### A-007 — Webhooks report task changes
- Area: integrations
- Observation: External systems can be notified when tasks change
- Evidence: D-031
- Confidence: CONFIRMED
- Engineering implication: Outbound delivery that survives receiver outages
- Target implementation: UNKNOWN
- Our requirement: Each webhook delivery must be retried at least 3 times with backoff
- Derived from: I-02, F-027

### A-008 — Due dates sync to calendars
- Area: integrations
- Observation: Due dates can be synced to an external calendar
- Evidence: D-033
- Confidence: CONFIRMED
- Engineering implication: A connected-account sync that follows task changes
- Target implementation: UNKNOWN
- Our requirement: A due-date change must reach the connected calendar within 5 minutes
- Derived from: W-006, I-03, F-028

### A-009 — Daily digests are scheduled
- Area: async
- Observation: Members can opt into a daily email digest
- Evidence: D-020
- Confidence: CONFIRMED
- Engineering implication: A scheduler runs per-member jobs
- Target implementation: UNKNOWN
- Our requirement: The digest job must run once per day for every opted-in member
- Derived from: F-017, D-020

### A-010 — Files attach to tasks
- Area: files
- Observation: Members can attach files to a task
- Evidence: D-039
- Confidence: CONFIRMED
- Engineering implication: Durable file storage with the task's access rules
- Target implementation: UNKNOWN
- Our requirement: Attachments must be stored durably and served only to members who may read the task
- Derived from: F-006, E-08

### A-011 — Customer data is encrypted at rest
- Area: security
- Observation: The security overview says data is encrypted at rest
- Evidence: D-016
- Confidence: CONFIRMED
- Engineering implication: Every store that holds customer data encrypts it
- Target implementation: UNKNOWN
- Our requirement: Customer data must be encrypted at rest in every store
- Derived from: D-016

### A-012 — Archive is reversible
- Area: storage
- Observation: Archived projects disappear from boards and can be restored
- Evidence: D-022
- Confidence: CONFIRMED
- Engineering implication: Archive is a state, not a delete
- Target implementation: UNKNOWN
- Our requirement: Archiving must never delete tasks; restore must return the project and its tasks unchanged
- Derived from: W-008, E-04

### A-013 — Commits close tasks
- Area: integrations
- Observation: Git commits that reference a task can close it
- Evidence: D-035
- Confidence: CONFIRMED
- Engineering implication: Inbound events from a repository host change task state
- Target implementation: UNKNOWN
- Our requirement: A commit referencing a task must close it within 1 minute of the push being received
- Derived from: I-05, F-030

### A-014 — Two sign-in methods
- Area: authn
- Observation: Users sign in with an emailed link or a Google account
- Evidence: D-029
- Confidence: CONFIRMED
- Engineering implication: Passwordless links plus an external identity provider
- Target implementation: UNKNOWN
- Our requirement: Sign-in must accept one-time emailed links and Google accounts; a link must expire after first use
- Derived from: I-06, F-024, W-003

### A-015 — API lists page with cursors
- Area: performance
- Observation: API list endpoints are paginated with cursors
- Evidence: D-032
- Confidence: CONFIRMED
- Engineering implication: Stable cursors over changing lists
- Target implementation: UNKNOWN
- Our requirement: Every API list endpoint must page with cursors, at most 100 items per page
- Derived from: I-01, F-025

## Proposals

### AP-001 — Proposal for A-001
- Inference: A-001
- Proposed implementation: Refetch on focus and every 30 s using updated_at cursors
- Decision: ADR-006

### AP-002 — Proposal for A-002
- Inference: A-002
- Proposed implementation: Deferred (SC-019); PostgreSQL full-text search when it lands
- Decision: ADR-005

### AP-003 — Proposal for A-003
- Inference: A-003
- Proposed implementation: Outbox rows on assignment; the worker creates notifications
- Decision: ADR-007

### AP-004 — Proposal for A-004
- Inference: A-004
- Proposed implementation: An append-only activity table written in the mutation's transaction
- Decision: ADR-005

### AP-005 — Proposal for A-005
- Inference: A-005
- Proposed implementation: The policy module on every handler; RLS as the tenancy backstop
- Decision: ADR-004

### AP-006 — Proposal for A-006
- Inference: A-006
- Proposed implementation: workspace_id on every tenant table with row-level security
- Decision: ADR-002

### AP-007 — Proposal for A-007
- Inference: A-007
- Proposed implementation: Not in V1 (SC-027); the outbox would deliver webhooks later
- Decision: ADR-007

### AP-008 — Proposal for A-008
- Inference: A-008
- Proposed implementation: Not in V1 (SC-028); a sync job on the queue later
- Decision: ADR-007

### AP-009 — Proposal for A-009
- Inference: A-009
- Proposed implementation: Not in V1 (SC-017); a scheduled job on the queue later
- Decision: ADR-007

### AP-010 — Proposal for A-010
- Inference: A-010
- Proposed implementation: Object storage with signed URLs after a policy check
- Decision: ADR-008

### AP-011 — Proposal for A-011
- Inference: A-011
- Proposed implementation: Managed PostgreSQL and object storage with encryption at rest
- Decision: ADR-009

### AP-012 — Proposal for A-012
- Inference: A-012
- Proposed implementation: An archived_at column; archived projects are filtered, never deleted
- Decision: ADR-005

### AP-013 — Proposal for A-013
- Inference: A-013
- Proposed implementation: Not in V1 (SC-030); an inbound webhook handler later
- Decision: ADR-007

### AP-014 — Proposal for A-014
- Inference: A-014
- Proposed implementation: The hosted identity provider's magic links and Google OIDC
- Decision: ADR-003

### AP-015 — Proposal for A-015
- Inference: A-015
- Proposed implementation: Not in V1 (SC-025); keyset pagination when the API ships
- Decision: ADR-010
