# Permissions matrix — Tasklet

Who may do what in Tasklet, as its public documentation describes it: roles (`RL-`) and
one permission rule (`PR-`) per resource × action. `## Matrix` is generated from the rules by
`pf.py render` (merge does it automatically) — never edit between the markers.

Cells: ✓ allowed · ✗ denied · Limited (the rule's `Limited means` says how) · ? unknown (the rule's
`Related unknown` names the question) · — no cell yet (a validator error).

## Matrix

<!-- pf:generated:start permissions -->
| Resource | Action | RL-01 Owner | RL-02 Admin | RL-03 Member | RL-04 Guest | Rule |
|---|---|---|---|---|---|---|
| E-01 Workspace | manage-billing | ✓ | ✓ | ✗ | ✗ | PR-001 |
| E-03 Membership | create | ✓ | ✓ | ? | ✗ | PR-002 |
| E-03 Membership | update | ✓ | ? | ✗ | ✗ | PR-003 |
| E-04 Project | create | ✓ | ✓ | ✓ | ✗ | PR-004 |
| E-04 Project | archive | ✓ | ✓ | Limited | ✗ | PR-005 |
| E-05 Task | create | ✓ | ✓ | ✓ | ✗ | PR-006 |
| E-05 Task | read | ✓ | ✓ | ✓ | Limited | PR-007 |
| E-05 Task | update | ✓ | ✓ | ✓ | ✗ | PR-008 |
| E-05 Task | delete | ✓ | ✓ | ? | ✗ | PR-009 |
| E-06 Comment | create | ✓ | ✓ | ✓ | Limited | PR-010 |
| E-07 Label | manage | ✓ | ✓ | ? | ✗ | PR-011 |
| E-08 Attachment | create | ✓ | ✓ | ✓ | ✗ | PR-012 |
| E-10 Integration | manage | ✓ | ✓ | ? | ✗ | PR-013 |
<!-- pf:generated:end -->

## Roles

### RL-01 — Owner
- Description: Owns the workspace; everything an admin can do
- Scope: workspace
- Inherits: RL-02
- Evidence: D-027
- Confidence: CONFIRMED

### RL-02 — Admin
- Description: Manages members, billing and settings
- Scope: workspace
- Inherits: RL-03
- Evidence: D-027, D-028
- Confidence: CONFIRMED

### RL-03 — Member
- Description: Creates and works on tasks and projects
- Scope: workspace
- Inherits: none
- Evidence: D-027
- Confidence: CONFIRMED

### RL-04 — Guest
- Description: Comments on tasks shared with them
- Scope: workspace
- Inherits: none
- Evidence: D-027, D-004
- Confidence: CONFIRMED

## Rules

### PR-001 — Manage workspace billing
- Resource: E-01
- Action: manage-billing
- Grants: RL-01 ✓, RL-02 ✓, RL-03 ✗, RL-04 ✗
- Limited means:
- Evidence: D-028
- Confidence: CONFIRMED

### PR-002 — Create membership
- Resource: E-03
- Action: create
- Grants: RL-01 ✓, RL-02 ✓, RL-03 ?, RL-04 ✗
- Limited means:
- Evidence: D-026
- Confidence: PROBABLE
- Related unknown: U-010

### PR-003 — Change a member's role
- Resource: E-03
- Action: update
- Grants: RL-01 ✓, RL-02 ?, RL-03 ✗, RL-04 ✗
- Limited means:
- Evidence: D-027
- Confidence: PROBABLE
- Related unknown: U-010

### PR-004 — Create project
- Resource: E-04
- Action: create
- Grants: RL-01 ✓, RL-02 ✓, RL-03 ✓, RL-04 ✗
- Limited means:
- Evidence: D-021, D-004
- Confidence: CONFIRMED

### PR-005 — Archive project
- Resource: E-04
- Action: archive
- Grants: RL-01 ✓, RL-02 ✓, RL-03 Limited, RL-04 ✗
- Limited means: RL-03: only the project's owner
- Evidence: D-022
- Confidence: CONFIRMED

### PR-006 — Create task
- Resource: E-05
- Action: create
- Grants: RL-01 ✓, RL-02 ✓, RL-03 ✓, RL-04 ✗
- Limited means:
- Evidence: D-004, D-024
- Confidence: CONFIRMED

### PR-007 — Read task
- Resource: E-05
- Action: read
- Grants: RL-01 ✓, RL-02 ✓, RL-03 ✓, RL-04 Limited
- Limited means: RL-04: only tasks shared with them
- Evidence: D-004
- Confidence: CONFIRMED

### PR-008 — Update task
- Resource: E-05
- Action: update
- Grants: RL-01 ✓, RL-02 ✓, RL-03 ✓, RL-04 ✗
- Limited means:
- Evidence: D-004, D-001
- Confidence: CONFIRMED

### PR-009 — Delete task
- Resource: E-05
- Action: delete
- Grants: RL-01 ✓, RL-02 ✓, RL-03 ?, RL-04 ✗
- Limited means:
- Evidence: D-027
- Confidence: PROBABLE
- Related unknown: U-009

### PR-010 — Create comment
- Resource: E-06
- Action: create
- Grants: RL-01 ✓, RL-02 ✓, RL-03 ✓, RL-04 Limited
- Limited means: RL-04: only on tasks shared with them
- Evidence: D-004, D-038
- Confidence: CONFIRMED

### PR-011 — Manage labels
- Resource: E-07
- Action: manage
- Grants: RL-01 ✓, RL-02 ✓, RL-03 ?, RL-04 ✗
- Limited means:
- Evidence: D-014
- Confidence: PROBABLE
- Related unknown: U-011

### PR-012 — Create attachment
- Resource: E-08
- Action: create
- Grants: RL-01 ✓, RL-02 ✓, RL-03 ✓, RL-04 ✗
- Limited means:
- Evidence: D-039, D-004
- Confidence: CONFIRMED

### PR-013 — Manage integrations
- Resource: E-10
- Action: manage
- Grants: RL-01 ✓, RL-02 ✓, RL-03 ?, RL-04 ✗
- Limited means:
- Evidence: D-033
- Confidence: PROBABLE
- Related unknown: U-011
