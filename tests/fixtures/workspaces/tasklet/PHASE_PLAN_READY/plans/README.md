# Phase plans — tasklet-alt

Ordered, independently executable phases. Each fits one Claude Code session: open a fresh session,
paste `STARTUP_PROMPT.md`, then say **"execute phase NN"**.

## Phases

| # | Phase | File | Status | Depends on |
|---|---|---|---|---|
| 00 | Repository foundation | [phase-00-repository-foundation.md](phase-00-repository-foundation.md) | Not started | none |
| 01 | Database and tenancy | [phase-01-database-and-tenancy.md](phase-01-database-and-tenancy.md) | Not started | 00 |
| 02 | Sign-in | [phase-02-sign-in.md](phase-02-sign-in.md) | Not started | 01 |
| 03 | Authorization policy | [phase-03-authorization-policy.md](phase-03-authorization-policy.md) | Not started | 02 |
| 04 | Workspaces and members | [phase-04-workspaces-and-members.md](phase-04-workspaces-and-members.md) | Not started | 03 |
| 05 | Projects | [phase-05-projects.md](phase-05-projects.md) | Not started | 04 |
| 06 | Tasks and statuses | [phase-06-tasks-and-statuses.md](phase-06-tasks-and-statuses.md) | Not started | 05 |
| 07 | Board and polling | [phase-07-board-and-polling.md](phase-07-board-and-polling.md) | Not started | 06 |
| 08 | Comments and mentions | [phase-08-comments-and-mentions.md](phase-08-comments-and-mentions.md) | Not started | 06 |
| 09 | Jobs and notifications | [phase-09-jobs-and-notifications.md](phase-09-jobs-and-notifications.md) | Not started | 08 |
| 10 | Attachments | [phase-10-attachments.md](phase-10-attachments.md) | Not started | 06 |
| 11 | Billing | [phase-11-billing.md](phase-11-billing.md) | Not started | 04 |
| 12 | Deployment and hardening | [phase-12-deployment-and-hardening.md](phase-12-deployment-and-hardening.md) | Not started | 07, 09, 10, 11 |

## Dependency graph

<!-- An ASCII or mermaid graph of the phases' dependencies. -->

## How to execute a phase

1. Read the phase file, `IMPLEMENTATION_PLAN.md` and `CLAUDE.md`.
2. Implement every task of that phase only.
3. Run the tests and linters until green; do the manual verification.
4. Tick the phase's Definition of done and set its status to **Done** here.

## Invariants every phase upholds

<!-- One line per INV record: "- INV-NN — <rule>". -->
