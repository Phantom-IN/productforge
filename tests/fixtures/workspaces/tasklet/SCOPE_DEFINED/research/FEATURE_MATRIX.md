# Feature matrix — Tasklet

The canonical feature inventory of Tasklet: every user-visible capability as an `F-` record
with evidence and confidence. `## Hierarchy` and `## Matrix` are generated from the records by
`pf.py render` (merge does it automatically) — never edit between the markers. `MVP`, `Decision`
and `Score` are filled during scoping (SCOPE_DEFINED).

## Domains

- Tasks & boards: creating, assigning and tracking tasks on boards (D-001, D-037)
- Projects: grouping related tasks (D-021)
- Collaboration: comments, notifications, guests and search (D-038, D-019, D-004)
- Workspace & access: workspaces, members, roles, billing and sign-in (D-025, D-027)
- Integrations & API: the developer API and third-party integrations (D-003, D-033)

## Hierarchy

<!-- pf:generated:start hierarchy -->
- **Collaboration**
  - F-014 Comments
    - F-015 Mentions
  - F-016 In-app notifications
    - F-017 Email digests
  - F-018 Guest access
  - F-019 Global search
- **Integrations & API**
  - F-025 Public REST API
    - F-026 Personal access tokens
    - F-027 Webhooks
  - F-028 Calendar sync
  - F-029 Chat notifications
  - F-030 Git commit linking
- **Projects**
  - F-011 Projects
    - F-012 Project archive and restore
    - F-013 Optional project membership
- **Tasks & boards**
  - F-001 Tasks
    - F-002 Assignment
    - F-003 Due dates and reminders
    - F-004 Statuses
    - F-005 Labels
    - F-006 Attachments
    - F-007 Recurring tasks
    - F-010 Activity history
  - F-008 Board view
  - F-009 Live updates
- **Workspace & access**
  - F-020 Workspaces
    - F-021 Member invitations
    - F-022 Roles
    - F-023 Billing management
  - F-024 Sign-in
  - F-031 Plans and pricing
<!-- pf:generated:end -->

## Matrix

<!-- pf:generated:start matrix -->
| ID | Domain | Feature | Parent | Surface | Evidence | Confidence | Plan tier | Complexity | MVP | Decision | Score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F-014 | Collaboration | Comments | — | PS-03 | D-038 | CONFIRMED | all | Low | yes | BUILD NOW | 19 |
| F-015 | Collaboration | Mentions | F-014 | PS-03 | D-038 | CONFIRMED | all | Low | yes | BUILD NOW | 7 |
| F-016 | Collaboration | In-app notifications | — | PS-05 | D-019 | CONFIRMED | all | Medium | yes | BUILD NOW | 9 |
| F-017 | Collaboration | Email digests | F-016 | PS-05 | D-020 | CONFIRMED | all | Medium | no | DEFER | -1 |
| F-018 | Collaboration | Guest access | — | PS-06 | D-004 | CONFIRMED | unknown | Medium | no | DEFER | -4 |
| F-019 | Collaboration | Global search | — | PS-03 | D-036 | CONFIRMED | all | Medium | no | DEFER | -4 |
| F-025 | Integrations & API | Public REST API | — | PS-07 | D-003, D-032 | CONFIRMED | all | High | no | DEFER | -2 |
| F-026 | Integrations & API | Personal access tokens | F-025 | PS-07 | D-030 | CONFIRMED | all | Low | no | DEFER | -4 |
| F-027 | Integrations & API | Webhooks | F-025 | PS-07 | D-031 | CONFIRMED | all | Medium | no | DROP | -10 |
| F-028 | Integrations & API | Calendar sync | — | PS-06 | D-033 | CONFIRMED | all | Medium | no | DEFER | -4 |
| F-029 | Integrations & API | Chat notifications | — | PS-06 | D-034 | CONFIRMED | all | Low | no | DEFER | -1 |
| F-030 | Integrations & API | Git commit linking | — | PS-06 | D-035 | CONFIRMED | all | Medium | no | DROP | -9 |
| F-011 | Projects | Projects | — | PS-04 | D-021, D-002 | CONFIRMED | all | Low | yes | BUILD NOW | 18 |
| F-012 | Projects | Project archive and restore | F-011 | PS-04 | D-022 | CONFIRMED | all | Low | no | DEFER | 1 |
| F-013 | Projects | Optional project membership | F-011 | PS-04 | D-002 | CONFIRMED | all | Low | yes | BUILD NOW | 9 |
| F-001 | Tasks & boards | Tasks | — | PS-03 | D-001, D-024 | CONFIRMED | all | Medium | yes | BUILD NOW | 19 |
| F-002 | Tasks & boards | Assignment | F-001 | PS-03 | D-001, D-019 | CONFIRMED | all | Low | yes | BUILD NOW | 12 |
| F-003 | Tasks & boards | Due dates and reminders | F-001 | PS-03 | D-023 | CONFIRMED | all | Low | yes | BUILD NOW | 6 |
| F-004 | Tasks & boards | Statuses | F-001 | PS-03 | D-024 | CONFIRMED | all | Low | yes | BUILD NOW | 19 |
| F-005 | Tasks & boards | Labels | F-001 | PS-03 | D-014 | CONFIRMED | all | Low | no | DEFER | 5 |
| F-006 | Tasks & boards | Attachments | F-001 | PS-03 | D-039 | CONFIRMED | all | Medium | yes | USE EXTERNAL SERVICE | 0 |
| F-007 | Tasks & boards | Recurring tasks | F-001 | PS-03 | D-042, D-005 | CONFIRMED | all | Medium | no | DEFER | -4 |
| F-008 | Tasks & boards | Board view | — | PS-03 | D-037 | CONFIRMED | all | Medium | yes | BUILD NOW | 19 |
| F-009 | Tasks & boards | Live updates | — | PS-03 | D-007 | CONFIRMED | all | High | yes | BUILD SIMPLIFIED (override) | 1 |
| F-010 | Tasks & boards | Activity history | F-001 | PS-05 | D-012 | CONFIRMED | all | Medium | yes | BUILD NOW | 11 |
| F-020 | Workspace & access | Workspaces | — | PS-06 | D-025 | CONFIRMED | all | Low | yes | BUILD NOW | 17 |
| F-021 | Workspace & access | Member invitations | F-020 | PS-02 | D-026 | CONFIRMED | all | Low | yes | BUILD NOW | 8 |
| F-022 | Workspace & access | Roles | F-020 | PS-06 | D-027 | CONFIRMED | all | Medium | yes | BUILD NOW | 8 |
| F-023 | Workspace & access | Billing management | F-020 | PS-06 | D-028, D-040 | CONFIRMED | paid | Medium | yes | USE EXTERNAL SERVICE | -9 |
| F-024 | Workspace & access | Sign-in | — | PS-02 | D-029 | CONFIRMED | all | Medium | yes | USE EXTERNAL SERVICE | 11 |
| F-031 | Workspace & access | Plans and pricing | — | PS-01 | D-040 | CONFIRMED | all | Low | no | DEFER | 1 |
<!-- pf:generated:end -->

## Records

### F-001 — Tasks
- Domain: Tasks & boards
- Feature: Tasks
- Parent:
- Surface: PS-03
- Evidence: D-001, D-024
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Medium
- Notes: Core object of the product.

### F-002 — Assignment
- Domain: Tasks & boards
- Feature: Assignment
- Parent: F-001
- Surface: PS-03
- Evidence: D-001, D-019
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Low
- Notes: Single assignee.

### F-003 — Due dates and reminders
- Domain: Tasks & boards
- Feature: Due dates and reminders
- Parent: F-001
- Surface: PS-03
- Evidence: D-023
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Low
- Notes:

### F-004 — Statuses
- Domain: Tasks & boards
- Feature: Statuses
- Parent: F-001
- Surface: PS-03
- Evidence: D-024
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Low
- Notes: Fixed status set.

### F-005 — Labels
- Domain: Tasks & boards
- Feature: Labels
- Parent: F-001
- Surface: PS-03
- Evidence: D-014
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Low
- Notes: Defined per workspace.

### F-006 — Attachments
- Domain: Tasks & boards
- Feature: Attachments
- Parent: F-001
- Surface: PS-03
- Evidence: D-039
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Medium
- Notes: Needs object storage.

### F-007 — Recurring tasks
- Domain: Tasks & boards
- Feature: Recurring tasks
- Parent: F-001
- Surface: PS-03
- Evidence: D-042, D-005
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Medium
- Notes: Needs a scheduler.

### F-008 — Board view
- Domain: Tasks & boards
- Feature: Board view
- Parent:
- Surface: PS-03
- Evidence: D-037
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Medium
- Notes:

### F-009 — Live updates
- Domain: Tasks & boards
- Feature: Live updates
- Parent:
- Surface: PS-03
- Evidence: D-007
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: High
- Notes: Realtime propagation to clients.

### F-010 — Activity history
- Domain: Tasks & boards
- Feature: Activity history
- Parent: F-001
- Surface: PS-05
- Evidence: D-012
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Medium
- Notes: Append-only log.

### F-011 — Projects
- Domain: Projects
- Feature: Projects
- Parent:
- Surface: PS-04
- Evidence: D-021, D-002
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Low
- Notes:

### F-012 — Project archive and restore
- Domain: Projects
- Feature: Project archive and restore
- Parent: F-011
- Surface: PS-04
- Evidence: D-022
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Low
- Notes:

### F-013 — Optional project membership
- Domain: Projects
- Feature: Optional project membership
- Parent: F-011
- Surface: PS-04
- Evidence: D-002
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Low
- Notes:

### F-014 — Comments
- Domain: Collaboration
- Feature: Comments
- Parent:
- Surface: PS-03
- Evidence: D-038
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Low
- Notes:

### F-015 — Mentions
- Domain: Collaboration
- Feature: Mentions
- Parent: F-014
- Surface: PS-03
- Evidence: D-038
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Low
- Notes:

### F-016 — In-app notifications
- Domain: Collaboration
- Feature: In-app notifications
- Parent:
- Surface: PS-05
- Evidence: D-019
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Medium
- Notes:

### F-017 — Email digests
- Domain: Collaboration
- Feature: Email digests
- Parent: F-016
- Surface: PS-05
- Evidence: D-020
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Medium
- Notes: Scheduled job per member.

### F-018 — Guest access
- Domain: Collaboration
- Feature: Guest access
- Parent:
- Surface: PS-06
- Evidence: D-004
- Confidence: CONFIRMED
- Plan tier: unknown
- Complexity: Medium
- Notes: Plan gating disputed (U-002).

### F-019 — Global search
- Domain: Collaboration
- Feature: Global search
- Parent:
- Surface: PS-03
- Evidence: D-036
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Medium
- Notes: Spans tasks and projects.

### F-020 — Workspaces
- Domain: Workspace & access
- Feature: Workspaces
- Parent:
- Surface: PS-06
- Evidence: D-025
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Low
- Notes: Top-level container.

### F-021 — Member invitations
- Domain: Workspace & access
- Feature: Member invitations
- Parent: F-020
- Surface: PS-02
- Evidence: D-026
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Low
- Notes:

### F-022 — Roles
- Domain: Workspace & access
- Feature: Roles
- Parent: F-020
- Surface: PS-06
- Evidence: D-027
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Medium
- Notes: Owner, admin, member, guest.

### F-023 — Billing management
- Domain: Workspace & access
- Feature: Billing management
- Parent: F-020
- Surface: PS-06
- Evidence: D-028, D-040
- Confidence: CONFIRMED
- Plan tier: paid
- Complexity: Medium
- Notes:

### F-024 — Sign-in
- Domain: Workspace & access
- Feature: Sign-in
- Parent:
- Surface: PS-02
- Evidence: D-029
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Medium
- Notes: Magic links and Google.

### F-025 — Public REST API
- Domain: Integrations & API
- Feature: Public REST API
- Parent:
- Surface: PS-07
- Evidence: D-003, D-032
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: High
- Notes:

### F-026 — Personal access tokens
- Domain: Integrations & API
- Feature: Personal access tokens
- Parent: F-025
- Surface: PS-07
- Evidence: D-030
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Low
- Notes:

### F-027 — Webhooks
- Domain: Integrations & API
- Feature: Webhooks
- Parent: F-025
- Surface: PS-07
- Evidence: D-031
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Medium
- Notes: Outbound delivery with retries.

### F-028 — Calendar sync
- Domain: Integrations & API
- Feature: Calendar sync
- Parent:
- Surface: PS-06
- Evidence: D-033
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Medium
- Notes:

### F-029 — Chat notifications
- Domain: Integrations & API
- Feature: Chat notifications
- Parent:
- Surface: PS-06
- Evidence: D-034
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Low
- Notes:

### F-030 — Git commit linking
- Domain: Integrations & API
- Feature: Git commit linking
- Parent:
- Surface: PS-06
- Evidence: D-035
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Medium
- Notes:

### F-031 — Plans and pricing
- Domain: Workspace & access
- Feature: Plans and pricing
- Parent:
- Surface: PS-01
- Evidence: D-040
- Confidence: CONFIRMED
- Plan tier: all
- Complexity: Low
- Notes: Free plan up to five members.
