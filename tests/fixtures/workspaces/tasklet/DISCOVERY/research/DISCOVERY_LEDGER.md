# Discovery ledger

One observable fact per claim; repeated sightings add evidence to the same claim.

## Records

### D-001 — Tasks can be assigned to one member
- Claim: A task has at most one assignee.
- Evidence: S-001
- Confidence: CONFIRMED
- Product impact: Assignment UI is single-select.
- Engineering impact: tasks.assignee_id is a single nullable reference.
- Status: active

### D-002 — Project membership is optional for tasks
- Claim: Tasks may optionally belong to a project.
- Evidence: S-002
- Confidence: CONFIRMED
- Product impact: Project membership cannot be mandatory.
- Engineering impact: tasks.project_id must be nullable.
- Status: active

### D-003 — The public REST API exposes tasks and projects
- Claim: The developer API offers REST resources for tasks and projects.
- Evidence: S-003
- Confidence: CONFIRMED
- Product impact:
- Engineering impact: An external API surface is part of the product.
- Status: active

### D-004 — Guests may comment on shared tasks
- Claim: Guests can comment on tasks that were shared with them.
- Evidence: S-004
- Confidence: CONFIRMED
- Product impact: Guest is a distinct role with limited rights.
- Engineering impact:
- Status: active

### D-005 — Recurring tasks appear to be supported
- Claim: Users report creating tasks that repeat on a schedule.
- Evidence: S-010, S-011
- Confidence: PROBABLE
- Product impact:
- Engineering impact: A scheduler for recurring work may be needed.
- Status: active

### D-006 — Reviewers praise keyboard shortcuts
- Claim: Small-team reviewers highlight keyboard-driven navigation.
- Evidence: S-012
- Confidence: PROBABLE
- Product impact: Keyboard shortcuts are an expected strength.
- Engineering impact:
- Status: active

### D-007 — Edits by one user show up for others without refresh
- Claim: Changes made by one user appear to other users without a page reload.
- Evidence: S-009, S-015
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-008 — Task changes need near-realtime propagation
- Claim: The system needs near-realtime propagation of task changes to connected clients.
- Evidence: S-009
- Confidence: INFERRED
- Product impact:
- Engineering impact: Requires a realtime event-distribution mechanism.
- Status: active
- Derived from: D-007

### D-009 — Guests are free on every plan
- Claim: The help center says guests are included on every plan.
- Evidence: S-004
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: conflicting-with D-010

### D-010 — Guests require a paid plan
- Claim: The pricing page lists guests as a paid-plan feature.
- Evidence: S-006
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: conflicting-with D-009

### D-011 — Automatic AI triage is rumoured
- Claim: An unverified post claims tasks are triaged automatically by AI.
- Evidence: S-014
- Confidence: UNKNOWN
- Product impact:
- Engineering impact:
- Status: active
- Related unknown: U-003

### D-012 — Every task keeps an activity history
- Claim: Each task shows a history of changes.
- Evidence: S-001
- Confidence: CONFIRMED
- Product impact:
- Engineering impact: An append-only activity log per task.
- Status: active

### D-013 — Labels can be attached to tasks
- Claim: Tasks can carry labels.
- Evidence: S-016
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: superseded-by D-014

### D-014 — Workspaces define a shared set of labels and tasks may carry several
- Claim: Labels are defined per workspace; a task may carry several of them.
- Evidence: S-001
- Confidence: CONFIRMED
- Product impact:
- Engineering impact: Many-to-many tasks↔labels within a workspace.
- Status: active

### D-015 — Tasks can be exported to CSV
- Claim: A third-party walkthrough mentions CSV export.
- Evidence: S-013
- Confidence: PROBABLE
- Product impact:
- Engineering impact:
- Status: rejected
- Reason: The walkthrough appears to describe a different product.

### D-016 — Customer data is encrypted at rest
- Claim: The security overview states data is encrypted at rest.
- Evidence: S-008
- Confidence: CONFIRMED
- Product impact:
- Engineering impact: Storage must support encryption at rest.
- Status: active

### D-017 — Releases ship weekly
- Claim: The changelog shows a weekly release cadence.
- Evidence: S-005
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-018 — Positioned for small teams
- Claim: The homepage positions the product as task tracking for small teams.
- Evidence: S-007
- Confidence: CONFIRMED
- Product impact: Target users are small teams.
- Engineering impact:
- Status: active
