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
