# Unknowns

Questions public sources cannot answer. Unknowns never block planning; each gets a V1 default during scoping.

## Records

### U-001 — How long is task activity history retained?
- Question: How long does the product keep task activity history?
- Reason it matters: Drives audit storage and data-retention design.
- Available evidence: D-012
- V1 default:
- Impact: Medium
- Related: D-012

### U-002 — Are guests free or a paid feature?
- Question: Are guest accounts included on every plan or only on paid plans?
- Reason it matters: Changes billing rules and the permission model for guests.
- Available evidence: D-009, D-010
- V1 default:
- Impact: High
- Related: D-009, D-010

### U-003 — Does the product ship AI triage?
- Question: Is automatic AI triage a real feature?
- Reason it matters: Would add an ML pipeline to the architecture.
- Available evidence: S-014
- V1 default:
- Impact: Low
- Related: D-011

### U-004 — Does Tasklet publish public repositories?
- Question: Are any SDKs or components published as public repositories?
- Reason it matters: Public code would be first-hand evidence for the developer surface.
- Available evidence: S-003
- V1 default:
- Impact: Low
- Related:

### U-005 — Is there an enterprise offering?
- Question: Does Tasklet sell an enterprise plan (SSO, audit log, contracts)?
- Reason it matters: Enterprise features change identity and audit requirements.
- Available evidence: S-006
- V1 default:
- Impact: Medium
- Related:

### U-006 — Have Tasklet staff given public talks?
- Question: Are there talks or podcasts by Tasklet staff about the product?
- Reason it matters: Talks often reveal observable behaviour not covered by docs.
- Available evidence: S-009
- V1 default:
- Impact: Low
- Related:

### U-007 — Are there official tutorials outside the docs?
- Question: Does Tasklet publish tutorials or courses beyond the documentation?
- Reason it matters: Tutorials show intended workflows end to end.
- Available evidence: S-001
- V1 default:
- Impact: Low
- Related:

### U-008 — Which channels deliver notifications?
- Question: Are notifications delivered in-app only, or also by email and push?
- Reason it matters: Each channel needs its own delivery pipeline and preferences.
- Available evidence: D-019, D-020
- V1 default:
- Impact: Medium
- Related: D-019, D-020

### U-009 — Who may delete tasks?
- Question: Can members delete tasks, or only owners and admins?
- Reason it matters: Decides the delete permission and whether deletion is soft.
- Available evidence: D-024, D-027
- V1 default:
- Impact: Medium
- Related: D-027

### U-010 — Who may invite members and change roles?
- Question: Can members invite people or change roles, or only owners and admins?
- Reason it matters: Shapes the membership permissions and the invitation flow.
- Available evidence: D-026, D-027
- V1 default:
- Impact: Medium
- Related: D-026, D-027

### U-011 — Who manages labels and integrations?
- Question: May any member define labels and connect integrations, or only admins?
- Reason it matters: Workspace-wide settings usually need an elevated role.
- Available evidence: D-014, D-033
- V1 default:
- Impact: Low
- Related: D-014, D-033

## V1 defaults

### UD-001 — U-001: Keep activity history for the life of the task
- Unknown: U-001
- V1 default: Keep activity history for the life of the task
- Rationale: Simplest rule; storage is small
- Impact if wrong: Low — a retention job can be added later

### UD-002 — U-002: Guests are allowed on every plan
- Unknown: U-002
- V1 default: Guests are allowed on every plan
- Rationale: Matches the help center, the more specific source
- Impact if wrong: Medium — billing rules change if guests become paid

### UD-003 — U-003: No AI triage
- Unknown: U-003
- V1 default: No AI triage
- Rationale: Only an unverified rumour mentions it
- Impact if wrong: Low

### UD-004 — U-004: No public SDK in V1
- Unknown: U-004
- V1 default: No public SDK in V1
- Rationale: No public repositories are known
- Impact if wrong: Low

### UD-005 — U-005: No enterprise plan in V1
- Unknown: U-005
- V1 default: No enterprise plan in V1
- Rationale: No evidence of one
- Impact if wrong: Medium — SSO and audit would be needed

### UD-006 — U-006: Talks are not needed for V1
- Unknown: U-006
- V1 default: Talks are not needed for V1
- Rationale: Talks only add evidence
- Impact if wrong: None

### UD-007 — U-007: Official tutorials are not needed for V1
- Unknown: U-007
- V1 default: Official tutorials are not needed for V1
- Rationale: Tutorials only add evidence
- Impact if wrong: None

### UD-008 — U-008: In-app notifications only
- Unknown: U-008
- V1 default: In-app notifications only
- Rationale: The only channel the evidence confirms for alerts
- Impact if wrong: Medium — email delivery may be expected

### UD-009 — U-009: Only owners and admins delete tasks
- Unknown: U-009
- V1 default: Only owners and admins delete tasks
- Rationale: The safer choice for shared work
- Impact if wrong: Low — easy to widen

### UD-010 — U-010: Only owners and admins invite members and change roles
- Unknown: U-010
- V1 default: Only owners and admins invite members and change roles
- Rationale: Least privilege
- Impact if wrong: Low — easy to widen

### UD-011 — U-011: Only owners and admins manage labels and integrations
- Unknown: U-011
- V1 default: Only owners and admins manage labels and integrations
- Rationale: Workspace-wide settings need an elevated role
- Impact if wrong: Low — easy to widen
