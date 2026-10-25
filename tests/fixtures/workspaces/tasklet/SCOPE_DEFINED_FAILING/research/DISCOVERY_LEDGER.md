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
- Context: Guest access and pricing

### D-010 — Guests require a paid plan
- Claim: The pricing page lists guests as a paid-plan feature.
- Evidence: S-006
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: conflicting-with D-009
- Context: Guest access and pricing

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

### D-019 — Assignees get an in-app notification
- Claim: Members receive an in-app notification when a task is assigned to them.
- Evidence: S-001
- Confidence: CONFIRMED
- Product impact: Assignment is a notification trigger.
- Engineering impact:
- Status: active

### D-020 — Daily email digests summarise activity
- Claim: Members can opt into a daily email digest of activity.
- Evidence: S-004
- Confidence: CONFIRMED
- Product impact:
- Engineering impact: A scheduled digest job per member.
- Status: active

### D-021 — Projects group tasks and have an owner
- Claim: A project collects tasks and has one owning member.
- Evidence: S-002
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-022 — Projects can be archived and restored
- Claim: Archived projects disappear from boards and can be restored later.
- Evidence: S-002
- Confidence: CONFIRMED
- Product impact:
- Engineering impact: Archive is a reversible state, not a delete.
- Status: active

### D-023 — Tasks carry a due date and optional reminder
- Claim: A task can have a due date and a reminder before it.
- Evidence: S-001
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-024 — Task status follows To do, In progress, Done
- Claim: Tasks move through the statuses To do, In progress and Done.
- Evidence: S-001
- Confidence: CONFIRMED
- Product impact:
- Engineering impact: A fixed status set in V1 of the target.
- Status: active

### D-025 — The workspace is the top-level container
- Claim: Members and projects belong to a workspace.
- Evidence: S-002
- Confidence: CONFIRMED
- Product impact:
- Engineering impact: Every record is scoped to one workspace.
- Status: active

### D-026 — Members join a workspace by email invitation
- Claim: Admins invite members to a workspace by email.
- Evidence: S-004
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-027 — Workspace roles are owner, admin, member and guest
- Claim: Each workspace member has one of four roles: owner, admin, member or guest.
- Evidence: S-004, S-006
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-028 — Only owners and admins manage billing
- Claim: Billing settings are limited to owners and admins.
- Evidence: S-006
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-029 — Sign-in uses magic links or Google accounts
- Claim: Users sign in with an emailed link or a Google account.
- Evidence: S-004
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-030 — API access uses personal access tokens
- Claim: API requests authenticate with personal access tokens.
- Evidence: S-003
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-031 — Webhooks report task changes to other systems
- Claim: Webhooks can notify external systems when tasks change.
- Evidence: S-003
- Confidence: CONFIRMED
- Product impact:
- Engineering impact: Outbound event delivery with retries.
- Status: active

### D-032 — List endpoints use cursor pagination
- Claim: API list endpoints are paginated with cursors.
- Evidence: S-003
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-033 — A calendar integration syncs due dates
- Claim: Due dates can be synced to an external calendar.
- Evidence: S-018
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-034 — A chat integration posts task updates
- Claim: Task updates can be posted to chat channels.
- Evidence: S-018
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-035 — Commit messages can close tasks
- Claim: Git commits that reference a task can close it.
- Evidence: S-018
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-036 — Global search spans tasks and projects
- Claim: One search box finds both tasks and projects.
- Evidence: S-017, S-012
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-037 — Boards show columns per status
- Claim: The board view shows one column per task status.
- Evidence: S-017
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-038 — Comments can mention members
- Claim: Comments support @-mentions of workspace members.
- Evidence: S-001
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-039 — Files can be attached to tasks
- Claim: Members can attach files to a task.
- Evidence: S-001
- Confidence: CONFIRMED
- Product impact:
- Engineering impact: Needs object storage for uploads.
- Status: active

### D-040 — The free plan allows five members
- Claim: The free plan is limited to five members per workspace.
- Evidence: S-006
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active
- Context: Free plan member limit

### D-041 — Uptime history is published per component
- Claim: The status page shows historic uptime for each component.
- Evidence: S-019
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-042 — Recurring tasks launched in February 2026
- Claim: Recurring tasks were announced as generally available in February 2026.
- Evidence: S-020
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active

### D-043 — Search needs a combined index
- Claim: Search needs to index tasks and projects together.
- Evidence: S-017
- Confidence: INFERRED
- Product impact:
- Engineering impact: A multi-entity search index.
- Status: active
- Derived from: D-036

### D-044 — Assignment changes must trigger notifications
- Claim: Changing a task's assignee must notify the new assignee.
- Evidence: S-001
- Confidence: INFERRED
- Product impact:
- Engineering impact: Notifications are produced from task events.
- Status: active
- Derived from: D-019, D-001

### D-045 — Attachments are limited to 10 MB
- Claim: Each attachment may be at most 10 MB.
- Evidence: S-001
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: conflicting-with D-046
- Context: Attachment upload limit

### D-046 — The upload cap is 25 MB per file
- Claim: Each attachment may be at most 25 MB.
- Evidence: S-008
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: conflicting-with D-045
- Context: Attachment upload limit
