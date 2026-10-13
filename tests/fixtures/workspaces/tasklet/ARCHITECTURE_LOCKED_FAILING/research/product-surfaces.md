# Product surfaces

Every visible surface of the product; `Related features` is filled during PRODUCT_MODEL.

## Records

### PS-01 — Marketing website
- Purpose: Explain the product and its plans to prospects.
- Users: Visitors
- Visible capabilities: Positioning, feature overview, plan comparison.
- Related features:
- Known routes: /, /features, /pricing
- Evidence: S-007, S-017, S-006
- Confidence: CONFIRMED
- Dependencies:
- Unanswered questions: U-005

### PS-02 — Sign-in and onboarding
- Purpose: Let people sign in and join a workspace.
- Users: New and returning members
- Visible capabilities: Magic-link and Google sign-in, invitation acceptance.
- Related features:
- Known routes: /login, /join
- Evidence: D-029, D-026
- Confidence: CONFIRMED
- Dependencies:
- Unanswered questions:

### PS-03 — Task board
- Purpose: Plan and track the team's tasks.
- Users: Members, guests
- Visible capabilities: Columns per status, assignment, due dates, labels.
- Related features:
- Known routes: /w/<workspace>/board
- Evidence: D-037, D-024, D-001
- Confidence: CONFIRMED
- Dependencies: Projects
- Unanswered questions:

### PS-04 — Projects
- Purpose: Group related tasks.
- Users: Members
- Visible capabilities: Create, archive and restore projects; project owner.
- Related features:
- Known routes: /w/<workspace>/projects
- Evidence: D-021, D-022
- Confidence: CONFIRMED
- Dependencies:
- Unanswered questions:

### PS-05 — Notifications and activity
- Purpose: Keep members informed about changes.
- Users: Members
- Visible capabilities: In-app notifications, daily digest, task history.
- Related features:
- Known routes: /w/<workspace>/inbox
- Evidence: D-019, D-020, D-012
- Confidence: CONFIRMED
- Dependencies:
- Unanswered questions: U-008

### PS-06 — Workspace settings and members
- Purpose: Administer the workspace.
- Users: Owners, admins
- Visible capabilities: Invitations, roles, billing.
- Related features:
- Known routes: /w/<workspace>/settings
- Evidence: D-025, D-026, D-027, D-028
- Confidence: CONFIRMED
- Dependencies:
- Unanswered questions:

### PS-07 — Developer API
- Purpose: Let developers integrate with Tasklet.
- Users: Developers
- Visible capabilities: REST resources, tokens, webhooks, pagination.
- Related features:
- Known routes: https://developers.tasklet.example/api
- Evidence: D-030, D-031, D-032
- Confidence: CONFIRMED
- Dependencies: Workspace settings and members
- Unanswered questions:

## Surface → features

<!-- pf:generated:start surface-features -->
| Surface | Features |
|---|---|
| PS-01 Marketing website | F-031 |
| PS-02 Sign-in and onboarding | F-021, F-024 |
| PS-03 Task board | F-001, F-002, F-003, F-004, F-005, F-006, F-007, F-008, F-009, F-014, F-015, F-019 |
| PS-04 Projects | F-011, F-012, F-013 |
| PS-05 Notifications and activity | F-010, F-016, F-017 |
| PS-06 Workspace settings and members | F-018, F-020, F-022, F-023, F-028, F-029, F-030 |
| PS-07 Developer API | F-025, F-026, F-027 |
<!-- pf:generated:end -->
