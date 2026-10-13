# Domain model — Tasklet

The **reconstructed** domain model of Tasklet (https://tasklet.example): the entities its public
behaviour implies (`E-` records) with identity, lifecycle, deletion semantics and ownership. It
describes the target as observed — it is **not** our design. Our own model is decided later in
`spec/ARCHITECTURE.md` and the ADRs, which cite these IDs and state every deviation. Identity
choices shape keys, URLs, APIs and authorization, so each one is an ADR candidate.

`## Relationship tree` and `## Identity decisions` are generated from the records by `pf.py render`
(merge does it automatically) — never edit between the markers.

## Relationship tree

<!-- pf:generated:start relationship-tree -->
- E-01 Workspace
  - E-03 Membership · also E-02 User (N:1)
  - E-04 Project · also E-03 Membership (N:1)
  - E-05 Task · also E-04 Project (N:1), E-03 Membership (N:1), E-07 Label (N:M)
    - E-06 Comment · also E-02 User (N:1)
    - E-08 Attachment
    - E-11 Activity event · also E-02 User (N:1)
  - E-07 Label · also E-05 Task (N:M)
  - E-10 Integration
- E-02 User
  - E-09 Notification · also E-05 Task (N:1)
<!-- pf:generated:end -->

## Identity decisions

<!-- pf:generated:start identity -->
| Entity | Identity scheme | Human-readable key | Stable after creation? | Evidence |
|---|---|---|---|---|
| E-01 Workspace | Opaque workspace ID (format not public) | Workspace name | unknown | D-025, D-027, D-028 |
| E-02 User | Email address (magic link or Google sign-in) | Email address | unknown | D-029, D-026 |
| E-03 Membership | (workspace, user) pair | — | yes | D-026, D-027 |
| E-04 Project | Opaque project ID (format not public) | Project name | unknown | D-021, D-022 |
| E-05 Task | Opaque task ID exposed by the REST API | Task title | unknown | D-001, D-002, D-024, D-003 |
| E-06 Comment | Opaque comment ID (format not public) | — | unknown | D-038, D-004 |
| E-07 Label | Opaque label ID (format not public) | Label name | unknown | D-014 |
| E-08 Attachment | Opaque attachment ID (format not public) | File name | unknown | D-039 |
| E-09 Notification | Opaque notification ID (format not public) | — | unknown | D-019 |
| E-10 Integration | Opaque integration ID (format not public) | Provider name | unknown | D-033, D-034, D-035 |
| E-11 Activity event | Opaque event ID (format not public) | — | yes | D-012 |
<!-- pf:generated:end -->

## Records

### E-01 — Workspace
- Responsibility: Top-level container for members, projects, tasks and labels
- Identity: Opaque workspace ID (format not public)
- Human-readable key: Workspace name
- Stable after creation: unknown
- Relationships: E-03 (1:N, optional) memberships; E-04 (1:N, optional) projects
- Lifecycle: created → active
- Mutable fields: name, plan
- Immutable fields: id, created at
- Deletion semantics: restrict — workspace deletion is not documented
- Ownership: The member with the owner role
- Authorization implications: Every record is scoped to one workspace; every query filters by it
- Features: F-020, F-023
- Evidence: D-025, D-027, D-028
- Confidence: CONFIRMED

### E-02 — User
- Responsibility: A person who signs in
- Identity: Email address (magic link or Google sign-in)
- Human-readable key: Email address
- Stable after creation: unknown
- Relationships: E-03 (1:N, optional) memberships
- Lifecycle: invited → active
- Mutable fields: none — no profile editing is documented
- Immutable fields: id
- Deletion semantics: orphan-allowed — content keeps its author after a member leaves
- Ownership: The user themself
- Authorization implications: Identity is global; rights come from memberships
- Features: F-024
- Evidence: D-029, D-026
- Confidence: CONFIRMED

### E-03 — Membership
- Responsibility: A user's role in one workspace
- Identity: (workspace, user) pair
- Human-readable key: —
- Stable after creation: yes
- Relationships: E-01 (N:1, required) workspace; E-02 (N:1, required) user
- Lifecycle: invited → active → removed
- Mutable fields: role
- Immutable fields: workspace, user
- Deletion semantics: cascade — removing a member deletes only the membership
- Ownership: The workspace
- Authorization implications: Carries the role every permission check reads
- Features: F-021, F-022
- Evidence: D-026, D-027
- Confidence: CONFIRMED

### E-04 — Project
- Responsibility: Groups related tasks under one owner
- Identity: Opaque project ID (format not public)
- Human-readable key: Project name
- Stable after creation: unknown
- Relationships: E-01 (N:1, required) workspace; E-03 (N:1, required) owner
- Lifecycle: active → archived → restored
- Mutable fields: name, owner, archived
- Immutable fields: id, workspace
- Deletion semantics: archive — archived projects can be restored
- Ownership: One owning member
- Authorization implications: Archive is limited to the project's owner
- Features: F-011, F-012
- Evidence: D-021, D-022
- Confidence: CONFIRMED

### E-05 — Task
- Responsibility: The unit of work tracked on boards
- Identity: Opaque task ID exposed by the REST API
- Human-readable key: Task title
- Stable after creation: unknown
- Relationships: E-01 (N:1, required) workspace; E-04 (N:1, optional) project; E-03 (N:1, optional) assignee; E-07 (N:M, optional) labels
- Lifecycle: To do → In progress → Done
- Mutable fields: title, status, assignee, due date, reminder, labels
- Immutable fields: id, workspace
- Deletion semantics: restrict — task deletion is not documented (U-009)
- Ownership: The workspace
- Authorization implications: Guests see only tasks shared with them
- Features: F-001, F-002, F-003, F-004, F-005
- Evidence: D-001, D-002, D-024, D-003
- Confidence: CONFIRMED
- Related unknown: U-009

### E-06 — Comment
- Responsibility: Discussion on a task, with @-mentions
- Identity: Opaque comment ID (format not public)
- Human-readable key: —
- Stable after creation: unknown
- Relationships: E-05 (N:1, required) task; E-02 (N:1, required) author
- Lifecycle: posted
- Mutable fields: body
- Immutable fields: task, author
- Deletion semantics: cascade — removed with its task (inferred)
- Ownership: Its author
- Authorization implications: Guests may comment on shared tasks
- Features: F-014, F-015
- Evidence: D-038, D-004
- Confidence: CONFIRMED

### E-07 — Label
- Responsibility: A workspace-wide tag tasks may carry
- Identity: Opaque label ID (format not public)
- Human-readable key: Label name
- Stable after creation: unknown
- Relationships: E-01 (N:1, required) workspace; E-05 (N:M, optional) tasks
- Lifecycle: created → in use
- Mutable fields: name
- Immutable fields: workspace
- Deletion semantics: cascade — removing a label removes it from tasks (inferred)
- Ownership: The workspace
- Authorization implications: Defined per workspace (U-011)
- Features: F-005
- Evidence: D-014
- Confidence: CONFIRMED
- Related unknown: U-011

### E-08 — Attachment
- Responsibility: A file attached to a task
- Identity: Opaque attachment ID (format not public)
- Human-readable key: File name
- Stable after creation: unknown
- Relationships: E-05 (N:1, required) task
- Lifecycle: uploaded
- Mutable fields: none — files are replaced, not edited
- Immutable fields: task, file
- Deletion semantics: cascade — removed with its task (inferred)
- Ownership: The uploading member
- Authorization implications: Needs object storage with the task's access rules
- Features: F-006
- Evidence: D-039
- Confidence: CONFIRMED

### E-09 — Notification
- Responsibility: An in-app alert for one member
- Identity: Opaque notification ID (format not public)
- Human-readable key: —
- Stable after creation: unknown
- Relationships: E-02 (N:1, required) recipient; E-05 (N:1, optional) task
- Lifecycle: unread → read
- Mutable fields: none
- Immutable fields: recipient, task
- Deletion semantics: orphan-allowed — kept after the task changes
- Ownership: Its recipient
- Authorization implications: Visible only to its recipient
- Features: F-016
- Evidence: D-019
- Confidence: CONFIRMED

### E-10 — Integration
- Responsibility: A connection to a calendar, chat or git service
- Identity: Opaque integration ID (format not public)
- Human-readable key: Provider name
- Stable after creation: unknown
- Relationships: E-01 (N:1, required) workspace
- Lifecycle: connected → disconnected
- Mutable fields: configuration
- Immutable fields: workspace, provider
- Deletion semantics: restrict — disconnecting is documented, deletion is not
- Ownership: The workspace
- Authorization implications: Connecting integrations may need an elevated role (U-011)
- Features: F-028, F-029, F-030
- Evidence: D-033, D-034, D-035
- Confidence: CONFIRMED
- Related unknown: U-011

### E-11 — Activity event
- Responsibility: One entry in a task's history
- Identity: Opaque event ID (format not public)
- Human-readable key: —
- Stable after creation: yes
- Relationships: E-05 (N:1, required) task; E-02 (N:1, optional) actor
- Lifecycle: appended
- Mutable fields: none — append-only
- Immutable fields: everything
- Deletion semantics: cascade — retention is unknown (U-001)
- Ownership: The workspace
- Authorization implications: Readable by whoever can read the task
- Features: F-010
- Evidence: D-012
- Confidence: CONFIRMED
- Related unknown: U-001
