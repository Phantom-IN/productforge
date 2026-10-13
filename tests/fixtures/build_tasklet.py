"""Deterministic generator for the synthetic Tasklet fixture workspaces (dev-only).

    python3.11 tests/fixtures/build_tasklet.py          # rewrite the snapshots
    python3.11 tests/fixtures/build_tasklet.py --check  # exit 1 if the committed files differ

Snapshots (tests/fixtures/workspaces/tasklet/):
- DISCOVERY          — a gate-passing DISCOVERY workspace.
- DISCOVERY_FAILING  — fails exactly G-DISC-TIER1 and G-DISC-MIN-CLAIMS (no Tier 1 source, too few
                       claims) while validating cleanly.
- PRODUCT_MODEL      — DISCOVERY advanced (locks written) + a 31-feature matrix across 5 domains;
                       generated regions are rendered by pflib itself.

Everything is fictional ("Tasklet", *.example hosts). Never put real third-party content here.
Existing records must stay byte-identical (lock/overlay tests depend on them): append, don't edit.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "workspaces" / "tasklet"
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "productforge" / "scripts"))

STATE = {
    "schema_version": 1,
    "product": {"name": "Tasklet", "target_url": "https://tasklet.example", "slug": "tasklet",
                "our_name": "tasklet-alt", "needs_rename": True},
    "scope": {"text": "task tracking for small teams", "source": "user", "accepted": True},
    "state": "DISCOVERY",
    "stale": [],
    "stages": {"DISCOVERY": {"opened_at": "2026-10-08T00:00:00Z", "completed_at": None}},
    "locks": {},
}  # fmt: skip

# (id, title, url, category, tier, authority, area, published, notes)
SOURCES = [
    ("S-001", "Tasklet docs: tasks", "https://docs.tasklet.example/tasks", "docs", 1, "High", "Tasks", "unknown", "Task fields, assignment, activity history and labels."),
    ("S-002", "Tasklet docs: projects", "https://docs.tasklet.example/projects", "docs", 1, "High", "Projects", "unknown", "Explains that project membership is optional."),
    ("S-003", "Tasklet API reference", "https://developers.tasklet.example/api", "api-docs", 1, "High", "Developer API", "unknown", "REST resources for tasks and projects."),
    ("S-004", "Help center: guests", "https://help.tasklet.example/guests", "help-center", 1, "High", "Sharing", "2026-05-01", "Says guests are free on every plan."),
    ("S-005", "Release notes", "https://tasklet.example/changelog", "changelog", 1, "High", "Releases", "2026-10-01", "Weekly release cadence."),
    ("S-006", "Plans and pricing", "https://tasklet.example/pricing", "pricing", 2, "High", "Billing", "unknown", "Lists guests under the paid plan."),
    ("S-007", "Homepage", "https://tasklet.example/", "homepage", 2, "Medium", "Positioning", "unknown", "Positions the product for small teams."),
    ("S-008", "Security overview", "https://tasklet.example/security", "security", 1, "High", "Security", "unknown", "Encryption at rest and in transit."),
    ("S-009", "Engineering blog: live sync", "https://tasklet.example/blog/engineering/live-sync", "engineering-blog", 2, "High", "Sync", "2026-03-12", "Describes instant updates across clients."),
    ("S-010", "Community thread on repeating work", "https://community.example/t/repeating-work", "forums", 4, "Low", "Tasks", "2026-02-20", "Users describe recurring tasks."),
    ("S-011", "Social post by a team lead", "https://social.example/posts/1234", "social", 4, "Low", "Tasks", "2026-04-02", "Mentions recurring tasks."),
    ("S-012", "Review for small teams", "https://reviews.example/tasklet", "review-sites", 3, "Medium", "Usability", "2026-06-15", "Praises keyboard shortcuts."),
    ("S-013", "Third-party API walkthrough", "https://techblog.example/building-on-the-api", "technical-blogs", 3, "Medium", "Developer API", "2026-01-10", "Mentions a CSV export, possibly for another product."),
    ("S-014", "Rumour about automatic triage", "https://rumors.example/tasklet-ai", "unverified", 5, "Low", "AI", "unknown", "Unsourced claim about AI triage."),
    ("S-015", "Intro webinar", "https://tasklet.example/webinars/intro", "official-demo", 2, "Medium", "Sync", "2026-07-01", "Demo shows a teammate's edit appearing live."),
    ("S-016", "Legacy labels page", "https://docs.tasklet.example/legacy/labels", "docs", 2, "Medium", "Labels", "2024-11-01", "Lowered from Tier 1: page is marked legacy and may be outdated."),
    # ---- Phase 07 additions
    ("S-017", "Features overview", "https://tasklet.example/features", "features", 2, "High", "Product", "unknown", "Lists boards, search, recurring tasks, guests and integrations."),
    ("S-018", "Integrations directory", "https://tasklet.example/integrations", "integrations", 2, "High", "Integrations", "unknown", "Calendar, chat and Git integrations with setup notes."),
    ("S-019", "Status page", "https://status.tasklet.example/", "status", 2, "Medium", "Reliability", "unknown", "Uptime history per component."),
    ("S-020", "Launch post: recurring tasks", "https://tasklet.example/blog/recurring-tasks", "product-blog", 2, "Medium", "Tasks", "2026-02-01", "Announces recurring tasks."),
]  # fmt: skip


def d(i: int, title: str, claim: str, ev: str, conf: str, pi: str = "", ei: str = "",
      status: str = "active", **extra: str) -> str:  # fmt: skip
    s = (
        f"\n### D-{i:03d} — {title}\n- Claim: {claim}\n- Evidence: {ev}\n- Confidence: {conf}\n"
        f"- Product impact:{' ' + pi if pi else ''}\n- Engineering impact:{' ' + ei if ei else ''}\n"
        f"- Status: {status}\n"
    )
    for k, v in extra.items():
        s += f"- {k.replace('_', ' ').capitalize()}: {v}\n"
    return s


CLAIMS = [
    d(1, "Tasks can be assigned to one member", "A task has at most one assignee.", "S-001", "CONFIRMED", "Assignment UI is single-select.", "tasks.assignee_id is a single nullable reference."),
    d(2, "Project membership is optional for tasks", "Tasks may optionally belong to a project.", "S-002", "CONFIRMED", "Project membership cannot be mandatory.", "tasks.project_id must be nullable."),
    d(3, "The public REST API exposes tasks and projects", "The developer API offers REST resources for tasks and projects.", "S-003", "CONFIRMED", "", "An external API surface is part of the product."),
    d(4, "Guests may comment on shared tasks", "Guests can comment on tasks that were shared with them.", "S-004", "CONFIRMED", "Guest is a distinct role with limited rights."),
    d(5, "Recurring tasks appear to be supported", "Users report creating tasks that repeat on a schedule.", "S-010, S-011", "PROBABLE", "", "A scheduler for recurring work may be needed."),
    d(6, "Reviewers praise keyboard shortcuts", "Small-team reviewers highlight keyboard-driven navigation.", "S-012", "PROBABLE", "Keyboard shortcuts are an expected strength."),
    d(7, "Edits by one user show up for others without refresh", "Changes made by one user appear to other users without a page reload.", "S-009, S-015", "CONFIRMED"),
    d(8, "Task changes need near-realtime propagation", "The system needs near-realtime propagation of task changes to connected clients.", "S-009", "INFERRED", "", "Requires a realtime event-distribution mechanism.", derived_from="D-007"),
    d(9, "Guests are free on every plan", "The help center says guests are included on every plan.", "S-004", "CONFIRMED", "", "", status="conflicting-with D-010"),
    d(10, "Guests require a paid plan", "The pricing page lists guests as a paid-plan feature.", "S-006", "CONFIRMED", "", "", status="conflicting-with D-009"),
    d(11, "Automatic AI triage is rumoured", "An unverified post claims tasks are triaged automatically by AI.", "S-014", "UNKNOWN", related_unknown="U-003"),
    d(12, "Every task keeps an activity history", "Each task shows a history of changes.", "S-001", "CONFIRMED", "", "An append-only activity log per task."),
    d(13, "Labels can be attached to tasks", "Tasks can carry labels.", "S-016", "CONFIRMED", "", "", status="superseded-by D-014"),
    d(14, "Workspaces define a shared set of labels and tasks may carry several", "Labels are defined per workspace; a task may carry several of them.", "S-001", "CONFIRMED", "", "Many-to-many tasks↔labels within a workspace."),
    d(15, "Tasks can be exported to CSV", "A third-party walkthrough mentions CSV export.", "S-013", "PROBABLE", "", "", status="rejected", reason="The walkthrough appears to describe a different product."),
    d(16, "Customer data is encrypted at rest", "The security overview states data is encrypted at rest.", "S-008", "CONFIRMED", "", "Storage must support encryption at rest."),
    d(17, "Releases ship weekly", "The changelog shows a weekly release cadence.", "S-005", "CONFIRMED"),
    d(18, "Positioned for small teams", "The homepage positions the product as task tracking for small teams.", "S-007", "CONFIRMED", "Target users are small teams."),
    # ---- Phase 07 additions (nothing may cite D-018: the LOCK_DELETED overlay deletes it)
    d(19, "Assignees get an in-app notification", "Members receive an in-app notification when a task is assigned to them.", "S-001", "CONFIRMED", "Assignment is a notification trigger."),
    d(20, "Daily email digests summarise activity", "Members can opt into a daily email digest of activity.", "S-004", "CONFIRMED", "", "A scheduled digest job per member."),
    d(21, "Projects group tasks and have an owner", "A project collects tasks and has one owning member.", "S-002", "CONFIRMED"),
    d(22, "Projects can be archived and restored", "Archived projects disappear from boards and can be restored later.", "S-002", "CONFIRMED", "", "Archive is a reversible state, not a delete."),
    d(23, "Tasks carry a due date and optional reminder", "A task can have a due date and a reminder before it.", "S-001", "CONFIRMED"),
    d(24, "Task status follows To do, In progress, Done", "Tasks move through the statuses To do, In progress and Done.", "S-001", "CONFIRMED", "", "A fixed status set in V1 of the target."),
    d(25, "The workspace is the top-level container", "Members and projects belong to a workspace.", "S-002", "CONFIRMED", "", "Every record is scoped to one workspace."),
    d(26, "Members join a workspace by email invitation", "Admins invite members to a workspace by email.", "S-004", "CONFIRMED"),
    d(27, "Workspace roles are owner, admin, member and guest", "Each workspace member has one of four roles: owner, admin, member or guest.", "S-004, S-006", "CONFIRMED"),
    d(28, "Only owners and admins manage billing", "Billing settings are limited to owners and admins.", "S-006", "CONFIRMED"),
    d(29, "Sign-in uses magic links or Google accounts", "Users sign in with an emailed link or a Google account.", "S-004", "CONFIRMED"),
    d(30, "API access uses personal access tokens", "API requests authenticate with personal access tokens.", "S-003", "CONFIRMED"),
    d(31, "Webhooks report task changes to other systems", "Webhooks can notify external systems when tasks change.", "S-003", "CONFIRMED", "", "Outbound event delivery with retries."),
    d(32, "List endpoints use cursor pagination", "API list endpoints are paginated with cursors.", "S-003", "CONFIRMED"),
    d(33, "A calendar integration syncs due dates", "Due dates can be synced to an external calendar.", "S-018", "CONFIRMED"),
    d(34, "A chat integration posts task updates", "Task updates can be posted to chat channels.", "S-018", "CONFIRMED"),
    d(35, "Commit messages can close tasks", "Git commits that reference a task can close it.", "S-018", "CONFIRMED"),
    d(36, "Global search spans tasks and projects", "One search box finds both tasks and projects.", "S-017, S-012", "CONFIRMED"),
    d(37, "Boards show columns per status", "The board view shows one column per task status.", "S-017", "CONFIRMED"),
    d(38, "Comments can mention members", "Comments support @-mentions of workspace members.", "S-001", "CONFIRMED"),
    d(39, "Files can be attached to tasks", "Members can attach files to a task.", "S-001", "CONFIRMED", "", "Needs object storage for uploads."),
    d(40, "The free plan allows five members", "The free plan is limited to five members per workspace.", "S-006", "CONFIRMED"),
    d(41, "Uptime history is published per component", "The status page shows historic uptime for each component.", "S-019", "CONFIRMED"),
    d(42, "Recurring tasks launched in February 2026", "Recurring tasks were announced as generally available in February 2026.", "S-020", "CONFIRMED"),
    d(43, "Search needs a combined index", "Search needs to index tasks and projects together.", "S-017", "INFERRED", "", "A multi-entity search index.", derived_from="D-036"),
    d(44, "Assignment changes must trigger notifications", "Changing a task's assignee must notify the new assignee.", "S-001", "INFERRED", "", "Notifications are produced from task events.", derived_from="D-019, D-001"),
]  # fmt: skip

UNKNOWNS = """
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
"""
NEW_UNKNOWNS = """
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
"""


def ps(i: int, title: str, purpose: str, users: str, caps: str, routes: str, ev: str,
       deps: str = "", questions: str = "") -> str:  # fmt: skip
    return (
        f"\n### PS-{i:02d} — {title}\n- Purpose: {purpose}\n- Users: {users}\n"
        f"- Visible capabilities: {caps}\n- Related features:\n- Known routes: {routes}\n"
        f"- Evidence: {ev}\n- Confidence: CONFIRMED\n- Dependencies:{' ' + deps if deps else ''}\n"
        f"- Unanswered questions:{' ' + questions if questions else ''}\n"
    )


SURFACES = [
    ps(1, "Marketing website", "Explain the product and its plans to prospects.", "Visitors", "Positioning, feature overview, plan comparison.", "/, /features, /pricing", "S-007, S-017, S-006", "", "U-005"),
    ps(2, "Sign-in and onboarding", "Let people sign in and join a workspace.", "New and returning members", "Magic-link and Google sign-in, invitation acceptance.", "/login, /join", "D-029, D-026"),
    ps(3, "Task board", "Plan and track the team's tasks.", "Members, guests", "Columns per status, assignment, due dates, labels.", "/w/<workspace>/board", "D-037, D-024, D-001", "Projects"),
    ps(4, "Projects", "Group related tasks.", "Members", "Create, archive and restore projects; project owner.", "/w/<workspace>/projects", "D-021, D-022"),
    ps(5, "Notifications and activity", "Keep members informed about changes.", "Members", "In-app notifications, daily digest, task history.", "/w/<workspace>/inbox", "D-019, D-020, D-012", "", "U-008"),
    ps(6, "Workspace settings and members", "Administer the workspace.", "Owners, admins", "Invitations, roles, billing.", "/w/<workspace>/settings", "D-025, D-026, D-027, D-028"),
    ps(7, "Developer API", "Let developers integrate with Tasklet.", "Developers", "REST resources, tokens, webhooks, pagination.", "https://developers.tasklet.example/api", "D-030, D-031, D-032", "Workspace settings and members"),
]  # fmt: skip

COVERAGE = {
    "docs": "S-001, S-002, S-016", "api-docs": "S-003", "help-center": "S-004",
    "changelog": "S-005", "security": "S-008", "official-repo": "U-004", "homepage": "S-007",
    "features": "S-017", "pricing": "S-006", "enterprise": "U-005", "integrations": "S-018",
    "status": "S-019", "engineering-blog": "S-009", "product-blog": "S-020",
    "official-demo": "S-015", "official-talk": "U-006", "official-tutorial": "U-007",
}  # fmt: skip


def overview(coverage: dict[str, str]) -> str:
    lines = "\n".join(f"- {k}: {v}" for k, v in coverage.items())
    return f"""# Product overview — Tasklet

What Tasklet (https://tasklet.example) visibly is, from public sources. Every statement cites
`S-` IDs.

## Product

Tasklet is a hosted task tracker for small teams: tasks live on boards inside projects, grouped
into workspaces, with notifications, search and integrations (S-007, S-017, S-001).

## One-line description

Task tracking for small teams (S-007).

## Target users

Small teams that plan shared work; guests can be invited to collaborate (S-007, S-004).

## Category

Work management / task tracking (S-007, S-017).

## Pricing model

Free plan up to five members, paid plans per member; guests appear on the paid plan (S-006).

## Major areas

- Tasks and boards (S-001, S-017)
- Projects (S-002)
- Notifications and activity (S-001, S-004)
- Workspaces, members and roles (S-004, S-006)
- Integrations (S-018)
- Developer API (S-003)

## Recommended scope

Not needed: six major areas fit one research scope.

## Accepted scope

task tracking for small teams

## Coverage

{lines}
"""


def sources_md(rows: list[tuple]) -> str:
    out = ["# Sources\n",
           "\nEvery source ProductForge used, with its tier (1 = most authoritative). "
           "See `references/source-tiers.md`.\n", "\n## Records\n"]  # fmt: skip
    for sid, title, url, cat, tier, auth, area, pub, notes in rows:
        out.append(
            f"\n### {sid} — {title}\n- URL: {url}\n- Canonical URL: {url}\n- Category: {cat}\n"
            f"- Tier: {tier}\n- Authority: {auth}\n- Relevant area: {area}\n- Published: {pub}\n"
            f"- Last inspected: 2026-10-08\n- Notes: {notes}\n"
        )
    return "".join(out)


LEDGER_HEAD = ("# Discovery ledger\n\nOne observable fact per claim; repeated sightings add evidence "
               "to the same claim.\n\n## Records\n")  # fmt: skip
UNKNOWNS_HEAD = (
    "# Unknowns\n\nQuestions public sources cannot answer. Unknowns never block planning; each gets "
    "a V1 default during scoping.\n\n## Records\n"
)
SURFACES_HEAD = (
    "# Product surfaces\n\nEvery visible surface of the product; `Related features` is filled "
    "during PRODUCT_MODEL.\n\n## Records\n"
)


DOMAINS = """
- Tasks & boards: creating, assigning and tracking tasks on boards (D-001, D-037)
- Projects: grouping related tasks (D-021)
- Collaboration: comments, notifications, guests and search (D-038, D-019, D-004)
- Workspace & access: workspaces, members, roles, billing and sign-in (D-025, D-027)
- Integrations & API: the developer API and third-party integrations (D-003, D-033)
"""


def f(i: int, feature: str, domain: str, parent: str, surface: str, ev: str, tier: str,
      complexity: str, notes: str = "") -> str:  # fmt: skip
    return (
        f"\n### F-{i:03d} — {feature}\n- Domain: {domain}\n- Feature: {feature}\n"
        f"- Parent:{' ' + parent if parent else ''}\n- Surface: {surface}\n- Evidence: {ev}\n"
        f"- Confidence: CONFIRMED\n- Plan tier: {tier}\n- Complexity: {complexity}\n"
        f"- Notes:{' ' + notes if notes else ''}\n"
    )


TB, PJ, CO, WA, IA = (
    "Tasks & boards",
    "Projects",
    "Collaboration",
    "Workspace & access",
    "Integrations & API",
)
FEATURES = [
    f(1, "Tasks", TB, "", "PS-03", "D-001, D-024", "all", "Medium", "Core object of the product."),
    f(2, "Assignment", TB, "F-001", "PS-03", "D-001, D-019", "all", "Low", "Single assignee."),
    f(3, "Due dates and reminders", TB, "F-001", "PS-03", "D-023", "all", "Low"),
    f(4, "Statuses", TB, "F-001", "PS-03", "D-024", "all", "Low", "Fixed status set."),
    f(5, "Labels", TB, "F-001", "PS-03", "D-014", "all", "Low", "Defined per workspace."),
    f(6, "Attachments", TB, "F-001", "PS-03", "D-039", "all", "Medium", "Needs object storage."),
    f(7, "Recurring tasks", TB, "F-001", "PS-03", "D-042, D-005", "all", "Medium", "Needs a scheduler."),
    f(8, "Board view", TB, "", "PS-03", "D-037", "all", "Medium"),
    f(9, "Live updates", TB, "", "PS-03", "D-007", "all", "High", "Realtime propagation to clients."),
    f(10, "Activity history", TB, "F-001", "PS-05", "D-012", "all", "Medium", "Append-only log."),
    f(11, "Projects", PJ, "", "PS-04", "D-021, D-002", "all", "Low"),
    f(12, "Project archive and restore", PJ, "F-011", "PS-04", "D-022", "all", "Low"),
    f(13, "Optional project membership", PJ, "F-011", "PS-04", "D-002", "all", "Low"),
    f(14, "Comments", CO, "", "PS-03", "D-038", "all", "Low"),
    f(15, "Mentions", CO, "F-014", "PS-03", "D-038", "all", "Low"),
    f(16, "In-app notifications", CO, "", "PS-05", "D-019", "all", "Medium"),
    f(17, "Email digests", CO, "F-016", "PS-05", "D-020", "all", "Medium", "Scheduled job per member."),
    f(18, "Guest access", CO, "", "PS-06", "D-004", "unknown", "Medium", "Plan gating disputed (U-002)."),
    f(19, "Global search", CO, "", "PS-03", "D-036", "all", "Medium", "Spans tasks and projects."),
    f(20, "Workspaces", WA, "", "PS-06", "D-025", "all", "Low", "Top-level container."),
    f(21, "Member invitations", WA, "F-020", "PS-02", "D-026", "all", "Low"),
    f(22, "Roles", WA, "F-020", "PS-06", "D-027", "all", "Medium", "Owner, admin, member, guest."),
    f(23, "Billing management", WA, "F-020", "PS-06", "D-028, D-040", "paid", "Medium"),
    f(24, "Sign-in", WA, "", "PS-02", "D-029", "all", "Medium", "Magic links and Google."),
    f(25, "Public REST API", IA, "", "PS-07", "D-003, D-032", "all", "High"),
    f(26, "Personal access tokens", IA, "F-025", "PS-07", "D-030", "all", "Low"),
    f(27, "Webhooks", IA, "F-025", "PS-07", "D-031", "all", "Medium", "Outbound delivery with retries."),
    f(28, "Calendar sync", IA, "", "PS-06", "D-033", "all", "Medium"),
    f(29, "Chat notifications", IA, "", "PS-06", "D-034", "all", "Low"),
    f(30, "Git commit linking", IA, "", "PS-06", "D-035", "all", "Medium"),
    f(31, "Plans and pricing", WA, "", "PS-01", "D-040", "all", "Low", "Free plan up to five members."),
]  # fmt: skip


def wf(i: int, name: str, actor: str, trigger: str, feats: str, surfaces: str, ev: str,
       pre: str, outcome: str, steps: list[str], variations: list[str], reqs: list[str],
       questions: str = "") -> tuple[str, str]:  # fmt: skip
    from pflib import catalog

    body = (
        f"### W-{i:03d} — {name}\n- Actor: {actor}\n- Trigger: {trigger}\n- Features: {feats}\n"
        f"- Surfaces: {surfaces}\n- Evidence: {ev}\n- Confidence: CONFIRMED\n"
        f"- Preconditions:{' ' + pre if pre else ''}\n- Outcome: {outcome}\n\n## Steps\n\n"
        + "".join(f"{n}. {s}\n" for n, s in enumerate(steps, 1))
        + "\n## Variations & edge cases\n\n"
        + "".join(f"- {v}\n" for v in variations)
        + "\n## Engineering requirements surfaced\n\n"
        + "".join(f"- {r}\n" for r in reqs)
        + "\n## Open questions\n\n"
        + (f"- {questions}\n" if questions else "- None yet.\n")
    )
    return f"research/workflows/W-{i:03d}-{catalog.slugify(name)}.md", body


OBS, SYS = "[observed]", "[implied-system]"
WORKFLOWS = [
    wf(1, "Create a task", "Member", "Member adds a task on the board", "F-001, F-004, F-008", "PS-03", "D-024, D-037",
       "Member belongs to the workspace", "A new task appears on the board",
       [f"{OBS} Member opens the board and adds a task to a status column — D-037",
        f"{OBS} Member enters a title; the task starts in To do — D-024",
        f"{OBS} Member may set an assignee, a due date and labels — D-001, D-023, D-014",
        f"{SYS} Check the member may create tasks in this workspace — F-022",
        f"{SYS} Persist the task with its workspace and optional project — F-001, D-002",
        f"{SYS} Append an activity entry for the task — F-010",
        f"{SYS} Index the task for search — F-019",
        f"{SYS} Broadcast the change to connected clients — F-009",
        f"{SYS} Notify the assignee, if one was set — F-016"],
       ["Guests can only comment, not create tasks (D-004)", "Free plans are limited to five members (D-040)"],
       ["Step 5: tasks reference a workspace and an optional project", "Step 7: a search index over tasks",
        "Step 8: realtime fan-out of task changes", "Step 9: notifications triggered by task events"]),
    wf(2, "Assign a task", "Member", "Member picks an assignee on a task", "F-002, F-016", "PS-03, PS-05", "D-001, D-019",
       "The task exists", "The task has one assignee who is notified",
       [f"{OBS} Member chooses one assignee from the workspace members — D-001",
        f"{OBS} The assignee receives an in-app notification — D-019",
        f"{SYS} Replace any previous assignee (one assignee per task) — F-002",
        f"{SYS} Record the change in the task's activity — F-010",
        f"{SYS} Create the notification for the new assignee — F-016"],
       ["Reassigning notifies the new assignee only (D-044)"],
       ["Step 3: single nullable assignee reference", "Step 5: notification on assignment change"]),
    wf(3, "Invite a member", "Admin", "Admin invites someone by email", "F-021, F-022", "PS-06, PS-02", "D-026, D-027",
       "Admin role in the workspace", "The invitee joins with a role",
       [f"{OBS} Admin enters an email address and a role — D-026, D-027",
        f"{OBS} The invitee follows the emailed link and signs in — D-029",
        f"{SYS} Check the admin may invite members — F-022",
        f"{SYS} Create a pending invitation and send the email — F-021",
        f"{SYS} On acceptance create the membership with the chosen role — F-020"],
       ["Free plan member limit blocks extra invitations (D-040)"],
       ["Step 4: invitation tokens with expiry", "Step 5: workspace membership with a role"], "U-002"),
    wf(4, "Search the workspace", "Member", "Member types in the search box", "F-019", "PS-03", "D-036",
       "", "Matching tasks and projects are listed",
       [f"{OBS} Member types a query and sees tasks and projects together — D-036",
        f"{SYS} Query a combined index of tasks and projects scoped to the workspace — F-019, D-043",
        f"{SYS} Return only results the member may see — F-022"],
       ["Guests see only shared tasks (D-004)"],
       ["Step 2: multi-entity search scoped by workspace", "Step 3: permission filtering of results"]),
    wf(5, "Comment on a task", "Member or guest", "Someone writes a comment", "F-014, F-015", "PS-03", "D-038, D-004",
       "Access to the task", "The comment appears and mentioned members are told",
       [f"{OBS} A member or guest writes a comment, optionally mentioning members — D-038, D-004",
        f"{SYS} Persist the comment on the task — F-014",
        f"{SYS} Notify mentioned members — F-015, F-016",
        f"{SYS} Broadcast the new comment to viewers of the task — F-009"],
       ["Guests may comment only on tasks shared with them (D-004)"],
       ["Step 3: mention parsing and notifications"]),
    wf(6, "Connect the calendar integration", "Member", "Member enables calendar sync", "F-028", "PS-06", "D-033",
       "", "Due dates appear in the external calendar",
       [f"{OBS} Member connects a calendar from the integrations settings — D-033",
        f"{SYS} Store the integration credentials encrypted — F-028, D-016",
        f"{SYS} Sync due dates to the calendar when they change — F-028, F-003"],
       ["Disconnecting stops the sync"], ["Step 2: encrypted third-party credentials", "Step 3: outbound sync job"]),
    wf(7, "Change a task's status", "Member", "Member moves a task to another column", "F-004, F-009", "PS-03", "D-024, D-007",
       "The task exists", "The task shows its new status for everyone",
       [f"{OBS} Member drags a task to another status column — D-024, D-037",
        f"{OBS} Teammates see the move without reloading — D-007",
        f"{SYS} Persist the new status and log it — F-004, F-010",
        f"{SYS} Broadcast the change to connected clients — F-009"],
       [], ["Step 4: realtime propagation within seconds (D-008)"]),
    wf(8, "Archive a project", "Member", "Project owner archives a project", "F-012", "PS-04", "D-022",
       "The member owns the project", "The project and its tasks leave the boards until restored",
       [f"{OBS} The owner archives the project; it disappears from boards — D-022",
        f"{OBS} The project can be restored later — D-022",
        f"{SYS} Mark the project archived without deleting its tasks — F-012"],
       [], ["Step 3: archive is a reversible state, not a delete"]),
]  # fmt: skip


# ---- Phase 10: domain model, roles and permission rules (appended after the DISCOVERY lock)
MODEL_UNKNOWNS = """
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
"""


def ent(i: int, title: str, resp: str, identity: str, key: str, stable: str, rels: str,
        lifecycle: str, mutable: str, immutable: str, deletion: str, owner: str, authz: str,
        feats: str, ev: str, conf: str = "CONFIRMED", **extra: str) -> str:  # fmt: skip
    s = (
        f"\n### E-{i:02d} — {title}\n- Responsibility: {resp}\n- Identity: {identity}\n"
        f"- Human-readable key: {key}\n- Stable after creation: {stable}\n"
        f"- Relationships: {rels}\n- Lifecycle: {lifecycle}\n- Mutable fields: {mutable}\n"
        f"- Immutable fields: {immutable}\n- Deletion semantics: {deletion}\n"
        f"- Ownership: {owner}\n- Authorization implications: {authz}\n- Features: {feats}\n"
        f"- Evidence: {ev}\n- Confidence: {conf}\n"
    )
    for k, v in extra.items():
        s += f"- {k.replace('_', ' ').capitalize()}: {v}\n"
    return s


ENTITIES = [
    ent(1, "Workspace", "Top-level container for members, projects, tasks and labels", "Opaque workspace ID (format not public)", "Workspace name", "unknown",
        "E-03 (1:N, optional) memberships; E-04 (1:N, optional) projects", "created → active", "name, plan", "id, created at",
        "restrict — workspace deletion is not documented", "The member with the owner role", "Every record is scoped to one workspace; every query filters by it",
        "F-020, F-023", "D-025, D-027, D-028"),
    ent(2, "User", "A person who signs in", "Email address (magic link or Google sign-in)", "Email address", "unknown",
        "E-03 (1:N, optional) memberships", "invited → active", "none — no profile editing is documented", "id",
        "orphan-allowed — content keeps its author after a member leaves", "The user themself", "Identity is global; rights come from memberships",
        "F-024", "D-029, D-026"),
    ent(3, "Membership", "A user's role in one workspace", "(workspace, user) pair", "—", "yes",
        "E-01 (N:1, required) workspace; E-02 (N:1, required) user", "invited → active → removed", "role", "workspace, user",
        "cascade — removing a member deletes only the membership", "The workspace", "Carries the role every permission check reads",
        "F-021, F-022", "D-026, D-027"),
    ent(4, "Project", "Groups related tasks under one owner", "Opaque project ID (format not public)", "Project name", "unknown",
        "E-01 (N:1, required) workspace; E-03 (N:1, required) owner", "active → archived → restored", "name, owner, archived", "id, workspace",
        "archive — archived projects can be restored", "One owning member", "Archive is limited to the project's owner",
        "F-011, F-012", "D-021, D-022"),
    ent(5, "Task", "The unit of work tracked on boards", "Opaque task ID exposed by the REST API", "Task title", "unknown",
        "E-01 (N:1, required) workspace; E-04 (N:1, optional) project; E-03 (N:1, optional) assignee; E-07 (N:M, optional) labels",
        "To do → In progress → Done", "title, status, assignee, due date, reminder, labels", "id, workspace",
        "restrict — task deletion is not documented (U-009)", "The workspace", "Guests see only tasks shared with them",
        "F-001, F-002, F-003, F-004, F-005", "D-001, D-002, D-024, D-003", "CONFIRMED", related_unknown="U-009"),
    ent(6, "Comment", "Discussion on a task, with @-mentions", "Opaque comment ID (format not public)", "—", "unknown",
        "E-05 (N:1, required) task; E-02 (N:1, required) author", "posted", "body", "task, author",
        "cascade — removed with its task (inferred)", "Its author", "Guests may comment on shared tasks",
        "F-014, F-015", "D-038, D-004"),
    ent(7, "Label", "A workspace-wide tag tasks may carry", "Opaque label ID (format not public)", "Label name", "unknown",
        "E-01 (N:1, required) workspace; E-05 (N:M, optional) tasks", "created → in use", "name", "workspace",
        "cascade — removing a label removes it from tasks (inferred)", "The workspace", "Defined per workspace (U-011)",
        "F-005", "D-014", "CONFIRMED", related_unknown="U-011"),
    ent(8, "Attachment", "A file attached to a task", "Opaque attachment ID (format not public)", "File name", "unknown",
        "E-05 (N:1, required) task", "uploaded", "none — files are replaced, not edited", "task, file",
        "cascade — removed with its task (inferred)", "The uploading member", "Needs object storage with the task's access rules",
        "F-006", "D-039"),
    ent(9, "Notification", "An in-app alert for one member", "Opaque notification ID (format not public)", "—", "unknown",
        "E-02 (N:1, required) recipient; E-05 (N:1, optional) task", "unread → read", "none", "recipient, task",
        "orphan-allowed — kept after the task changes", "Its recipient", "Visible only to its recipient",
        "F-016", "D-019"),
    ent(10, "Integration", "A connection to a calendar, chat or git service", "Opaque integration ID (format not public)", "Provider name", "unknown",
        "E-01 (N:1, required) workspace", "connected → disconnected", "configuration", "workspace, provider",
        "restrict — disconnecting is documented, deletion is not", "The workspace", "Connecting integrations may need an elevated role (U-011)",
        "F-028, F-029, F-030", "D-033, D-034, D-035", "CONFIRMED", related_unknown="U-011"),
    ent(11, "Activity event", "One entry in a task's history", "Opaque event ID (format not public)", "—", "yes",
        "E-05 (N:1, required) task; E-02 (N:1, optional) actor", "appended", "none — append-only", "everything",
        "cascade — retention is unknown (U-001)", "The workspace", "Readable by whoever can read the task",
        "F-010", "D-012", "CONFIRMED", related_unknown="U-001"),
]  # fmt: skip


def role(i: int, title: str, desc: str, inherits: str, ev: str) -> str:
    return (
        f"\n### RL-{i:02d} — {title}\n- Description: {desc}\n- Scope: workspace\n"
        f"- Inherits: {inherits}\n- Evidence: {ev}\n- Confidence: CONFIRMED\n"
    )


ROLES = [
    role(1, "Owner", "Owns the workspace; everything an admin can do", "RL-02", "D-027"),
    role(2, "Admin", "Manages members, billing and settings", "RL-03", "D-027, D-028"),
    role(3, "Member", "Creates and works on tasks and projects", "none", "D-027"),
    role(4, "Guest", "Comments on tasks shared with them", "none", "D-027, D-004"),
]


def rule(i: int, resource: str, action: str, grants: str, ev: str, limited: str = "",
         conf: str = "CONFIRMED", unknown: str = "", title: str = "") -> str:  # fmt: skip
    s = (
        f"\n### PR-{i:03d} — {title or action.capitalize() + ' ' + NAMES[resource]}\n"
        f"- Resource: {resource}\n- Action: {action}\n"
        f"- Grants: {grants}\n- Limited means:{' ' + limited if limited else ''}\n"
        f"- Evidence: {ev}\n- Confidence: {conf}\n"
    )
    return s + (f"- Related unknown: {unknown}\n" if unknown else "")


NAMES = {"E-01": "workspace", "E-03": "membership", "E-04": "project", "E-05": "task",
         "E-06": "comment", "E-07": "labels", "E-08": "attachment", "E-10": "integrations"}  # fmt: skip
ALL = "RL-01 ✓, RL-02 ✓, RL-03 ✓"
RULES = [
    rule(1, "E-01", "manage-billing", "RL-01 ✓, RL-02 ✓, RL-03 ✗, RL-04 ✗", "D-028", title="Manage workspace billing"),
    rule(2, "E-03", "create", "RL-01 ✓, RL-02 ✓, RL-03 ?, RL-04 ✗", "D-026", conf="PROBABLE", unknown="U-010"),
    rule(3, "E-03", "update", "RL-01 ✓, RL-02 ?, RL-03 ✗, RL-04 ✗", "D-027", conf="PROBABLE", unknown="U-010", title="Change a member's role"),
    rule(4, "E-04", "create", f"{ALL}, RL-04 ✗", "D-021, D-004"),
    rule(5, "E-04", "archive", "RL-01 ✓, RL-02 ✓, RL-03 Limited, RL-04 ✗", "D-022", limited="RL-03: only the project's owner"),
    rule(6, "E-05", "create", f"{ALL}, RL-04 ✗", "D-004, D-024"),
    rule(7, "E-05", "read", f"{ALL}, RL-04 Limited", "D-004", limited="RL-04: only tasks shared with them"),
    rule(8, "E-05", "update", f"{ALL}, RL-04 ✗", "D-004, D-001"),
    rule(9, "E-05", "delete", "RL-01 ✓, RL-02 ✓, RL-03 ?, RL-04 ✗", "D-027", conf="PROBABLE", unknown="U-009"),
    rule(10, "E-06", "create", f"{ALL}, RL-04 Limited", "D-004, D-038", limited="RL-04: only on tasks shared with them"),
    rule(11, "E-07", "manage", "RL-01 ✓, RL-02 ✓, RL-03 ?, RL-04 ✗", "D-014", conf="PROBABLE", unknown="U-011"),
    rule(12, "E-08", "create", f"{ALL}, RL-04 ✗", "D-039, D-004"),
    rule(13, "E-10", "manage", "RL-01 ✓, RL-02 ✓, RL-03 ?, RL-04 ✗", "D-033", conf="PROBABLE", unknown="U-011"),
]  # fmt: skip


# ---- Phase 11: integrations and architecture inference
def integ(i: int, title: str, purpose: str, direction: str, auth: str, events: str, data: str,
          config: str, failure: str, sync: str, ev: str, category: str, conf: str = "CONFIRMED") -> str:  # fmt: skip
    return (
        f"\n### I-{i:02d} — {title}\n- Purpose: {purpose}\n- Direction: {direction}\n"
        f"- Authentication: {auth}\n- Events: {events}\n- Data exchanged: {data}\n"
        f"- User configuration: {config}\n- Failure behaviour: {failure}\n"
        f"- Sync requirements: {sync}\n- Provider category: {category}\n- Evidence: {ev}\n"
        f"- Confidence: {conf}\n"
    )


INTEGRATIONS = [
    integ(1, "Public REST API", "Read and change tasks and projects from other programs", "inbound", "Personal access tokens", "none — request and response",
          "Tasks and projects", "A member creates a personal access token", "Not documented", "List endpoints page with cursors", "D-003, D-030, D-032", "api"),
    integ(2, "Webhooks", "Tell other systems when tasks change", "outbound", "Not documented (signing is not described)", "Task changes",
          "The changed task", "Not documented", "Not documented; delivery needs retries", "Near-realtime after each change", "D-031", "webhooks"),
    integ(3, "Calendar sync", "Show task due dates in an external calendar", "outbound", "Not documented (account connection)", "Due-date changes",
          "Due dates and task titles", "A member connects a calendar", "Not documented", "Due-date changes follow the task", "D-033", "calendar"),
    integ(4, "Chat notifications", "Post task updates to chat channels", "outbound", "Not documented (workspace connection)", "Task updates",
          "Task summaries", "Choose the channel to post to", "Not documented", "Posted after each update", "D-034", "chat"),
    integ(5, "Git commit linking", "Close tasks from commit messages", "inbound", "Not documented (repository connection)", "Pushed commits that reference a task",
          "Commit references to tasks", "Connect a repository", "Not documented", "On each push", "D-035", "scm"),
    integ(6, "Google sign-in", "Sign in with a Google account", "inbound", "Google account (single sign-on)", "Sign-in",
          "Account email and name", "None — offered on the sign-in page", "Fall back to an emailed sign-in link", "At each sign-in", "D-029", "identity"),
]  # fmt: skip


def infer(i: int, title: str, area: str, obs: str, ev: str, impl: str, req: str, derived: str,
          conf: str = "CONFIRMED") -> str:  # fmt: skip
    return (
        f"\n### A-{i:03d} — {title}\n- Area: {area}\n- Observation: {obs}\n- Evidence: {ev}\n"
        f"- Confidence: {conf}\n- Engineering implication: {impl}\n- Target implementation: UNKNOWN\n"
        f"- Our requirement: {req}\n- Derived from: {derived}\n"
    )


INFERENCES = [
    infer(1, "Task changes reach other users live", "realtime", "Edits by one user appear for others without a reload", "D-007",
          "The server pushes changes to connected clients", "Task changes must be visible to other connected clients within 2 s", "W-001, W-007, F-009, D-007"),
    infer(2, "One search spans tasks and projects", "search", "One search box finds both tasks and projects", "D-036",
          "A combined index over several entity types", "Search must return tasks and projects together; a new task must be searchable within 5 s", "W-004, F-019, D-043"),
    infer(3, "Assignment notifies the assignee", "notifications", "Members are notified in-app when a task is assigned to them", "D-019",
          "Notifications are produced from task events", "A new assignee must get an in-app notification within 5 s", "W-002, W-001, F-016"),
    infer(4, "Every task keeps its history", "audit", "Each task shows a history of its changes", "D-012",
          "An append-only activity log per task", "Every task change must append an activity entry that is never edited", "W-001, W-007, F-010, E-11"),
    infer(5, "Guests see only what is shared with them", "authz", "Guests can comment only on tasks shared with them", "D-004",
          "Every read and write is checked against the actor's role", "Every request must be authorized by workspace role; a guest must never read an unshared task", "W-005, W-003, PR-007, PR-010"),
    infer(6, "The workspace bounds all data", "tenancy", "Members and projects belong to a workspace", "D-025",
          "Every record carries its workspace", "Every record must belong to exactly one workspace; no query may cross workspaces", "W-003, E-01"),
    infer(7, "Webhooks report task changes", "integrations", "External systems can be notified when tasks change", "D-031",
          "Outbound delivery that survives receiver outages", "Each webhook delivery must be retried at least 3 times with backoff", "I-02, F-027"),
    infer(8, "Due dates sync to calendars", "integrations", "Due dates can be synced to an external calendar", "D-033",
          "A connected-account sync that follows task changes", "A due-date change must reach the connected calendar within 5 minutes", "W-006, I-03, F-028"),
    infer(9, "Daily digests are scheduled", "async", "Members can opt into a daily email digest", "D-020",
          "A scheduler runs per-member jobs", "The digest job must run once per day for every opted-in member", "F-017, D-020"),
    infer(10, "Files attach to tasks", "files", "Members can attach files to a task", "D-039",
          "Durable file storage with the task's access rules", "Attachments must be stored durably and served only to members who may read the task", "F-006, E-08"),
    infer(11, "Customer data is encrypted at rest", "security", "The security overview says data is encrypted at rest", "D-016",
          "Every store that holds customer data encrypts it", "Customer data must be encrypted at rest in every store", "D-016"),
    infer(12, "Archive is reversible", "storage", "Archived projects disappear from boards and can be restored", "D-022",
          "Archive is a state, not a delete", "Archiving must never delete tasks; restore must return the project and its tasks unchanged", "W-008, E-04"),
    infer(13, "Commits close tasks", "integrations", "Git commits that reference a task can close it", "D-035",
          "Inbound events from a repository host change task state", "A commit referencing a task must close it within 1 minute of the push being received", "I-05, F-030"),
    infer(14, "Two sign-in methods", "authn", "Users sign in with an emailed link or a Google account", "D-029",
          "Passwordless links plus an external identity provider", "Sign-in must accept one-time emailed links and Google accounts; a link must expire after first use", "I-06, F-024, W-003"),
    infer(15, "API lists page with cursors", "performance", "API list endpoints are paginated with cursors", "D-032",
          "Stable cursors over changing lists", "Every API list endpoint must page with cursors, at most 100 items per page", "I-01, F-025"),
]  # fmt: skip


# ---- Phase 12: competitors (synthetic, on .example domains; appended after the DISCOVERY lock)
COMPETITOR_SOURCES = [
    ("S-021", "Tasklet vs Taskmate vs Doable for small teams", "https://compare.example/tasklet-taskmate-doable", "comparison-articles", 3, "Medium", "Category", "2026-05-02", "Compares three small-team task trackers."),
    ("S-022", "Listwise alternatives: five task trackers compared", "https://roundups.example/listwise-alternatives", "comparison-articles", 3, "Medium", "Category", "2026-06-11", "Roundup of task trackers."),
    ("S-023", "Taskmate homepage", "https://taskmate.example/", "homepage", 2, "Medium", "competitor:C-01", "unknown", "Competitor homepage."),
    ("S-024", "Taskmate pricing", "https://taskmate.example/pricing", "pricing", 2, "High", "competitor:C-01", "unknown", "Competitor plans."),
    ("S-025", "Doable features", "https://doable.example/features", "features", 2, "High", "competitor:C-02", "unknown", "Competitor feature list."),
    ("S-026", "Doable reviews", "https://reviews.example/doable", "review-sites", 3, "Medium", "competitor:C-02", "2026-04-20", "User reviews of Doable."),
    ("S-027", "Listwise homepage", "https://listwise.example/", "homepage", 2, "Medium", "competitor:C-03", "unknown", "Competitor homepage."),
    ("S-028", "Forum thread on Listwise sync", "https://community.example/t/listwise-sync", "forums", 4, "Low", "competitor:C-03", "2026-03-15", "Users discuss sync problems."),
]  # fmt: skip


def comp(i: int, name: str, url: str, positioning: str, users: str, pricing: str, stakes: str,
         diffs: str, complaints: str, ev: str) -> str:  # fmt: skip
    return (
        f"\n### C-{i:02d} — {name}\n- Name: {name}\n- URL: {url}\n- Positioning: {positioning}\n"
        f"- Target users: {users}\n- Pricing model: {pricing}\n- Table-stakes features: {stakes}\n"
        f"- Differentiators: {diffs}\n- Common complaints: {complaints}\n- Evidence: {ev}\n"
        f"- Confidence: CONFIRMED\n"
    )


COMPETITORS = [
    comp(1, "Taskmate", "https://taskmate.example/", "Task lists with built-in time tracking", "Freelancers and small agencies",
         "Free tier; per-seat paid plans", "F-001, F-008, F-014", "Time tracking on every task", "Setup is slow for new teams (S-021)", "S-023, S-024"),
    comp(2, "Doable", "https://doable.example/", "Fast search across everything a team tracks", "Small product teams",
         "Per-seat subscription", "F-001, F-008, F-014", "Search across tasks, files and comments", "Mobile app lags behind the web app (S-026)", "S-025"),
    comp(3, "Listwise", "https://listwise.example/", "Lists first, with developer integrations", "Engineering teams",
         "Free for small teams; paid add-ons", "F-001, F-014", "Links commits and pull requests to tasks", "Sync between devices is unreliable (S-028)", "S-027"),
]  # fmt: skip


def signal(i: int, feature: str, kind: str, comps: str, ev: str, notes: str = "",
           name: str = "") -> str:  # fmt: skip
    return (
        f"\n### FS-{i:03d} — {name or feature} is {kind}\n- Feature: {feature}\n- Signal: {kind}\n"
        f"- Competitors: {comps}\n- Evidence: {ev}\n- Notes:{' ' + notes if notes else ''}\n"
    )


SIGNALS = [
    signal(1, "F-001", "table-stakes", "C-01, C-02, C-03", "S-023, S-025, S-027", name="Tasks"),
    signal(2, "F-019", "differentiator", "C-02", "S-025", "Doable markets search as its edge",
           name="Global search"),
    signal(3, "F-030", "rare", "C-03", "S-027", name="Git commit linking"),
    signal(4, "Time tracking", "absent-in-target", "C-01", "S-023", "Taskmate's headline feature"),
]  # fmt: skip


# ---- Phase 13: scope (score cards, requirements, V1 defaults)
WORDS = {
    "Core value": ("peripheral to tracking work", "supports the core loop", "important to daily work", "the reason the product exists"),
    "User frequency": ("rarely used", "used now and then", "used weekly", "used every session"),
    "Dependency importance": ("nothing depends on it", "one feature builds on it", "several features build on it", "most features need it"),
    "Differentiation": ("not a selling point", "expected but unremarkable", "a visible strength", "a reason to choose the product"),
    "Engineering complexity": ("trivial", "straightforward CRUD", "new moving parts", "hard: realtime, search or payments"),
    "Infrastructure complexity": ("no new infrastructure", "a small addition", "a new service to run", "significant new infrastructure"),
    "Security impact": ("no security risk", "minor risk", "exposes data if wrong", "security-critical"),
    "Operational cost": ("none", "small", "noticeable", "high"),
    "Time to implement": ("hours", "days", "about a week", "weeks"),
    "External availability": ("no service fits", "partial services exist", "good services exist", "mature services cover it"),
}  # fmt: skip

# F: core, freq, dep, diff, eng, infra, sec, ops, time, external, future, extra fields
SCORES = {
    "F-001": (3, 3, 3, 2, 2, 1, 1, 1, 2, 0, "yes", {}),
    "F-002": (2, 3, 1, 1, 1, 0, 1, 0, 1, 0, "yes", {}),
    "F-003": (2, 2, 0, 1, 1, 1, 0, 1, 1, 1, "yes", {}),
    "F-004": (3, 3, 2, 1, 1, 0, 0, 0, 1, 0, "yes", {}),
    "F-005": (1, 2, 0, 1, 1, 0, 0, 0, 1, 0, "yes", {}),
    "F-006": (2, 2, 0, 1, 2, 2, 2, 2, 1, 3, "yes", {"External service": "Object storage with signed download links"}),
    "F-007": (1, 1, 0, 1, 2, 2, 0, 1, 2, 0, "yes", {}),
    "F-008": (3, 3, 2, 2, 2, 0, 0, 0, 2, 0, "yes", {}),
    "F-009": (2, 3, 1, 2, 3, 3, 1, 2, 3, 1, "yes", {
        "Override decision": "BUILD SIMPLIFIED",
        "Override reason": "Live updates are the target's selling point (D-007); V1 polls instead of pushing",
        "Simplification": "Boards refresh on focus and every 30 s; no push channel in V1"}),
    "F-010": (2, 2, 2, 1, 1, 1, 1, 1, 1, 0, "yes", {}),
    "F-011": (3, 3, 2, 1, 1, 0, 1, 0, 1, 0, "yes", {}),
    "F-012": (1, 1, 0, 0, 1, 0, 0, 0, 1, 0, "yes", {}),
    "F-013": (2, 2, 1, 0, 1, 0, 0, 0, 1, 0, "yes", {}),
    "F-014": (3, 3, 1, 2, 1, 0, 1, 0, 1, 0, "yes", {}),
    "F-015": (2, 2, 0, 1, 1, 0, 1, 0, 1, 0, "yes", {}),
    "F-016": (2, 3, 1, 1, 2, 1, 0, 1, 1, 1, "yes", {}),
    "F-017": (1, 1, 0, 0, 1, 1, 0, 1, 1, 2, "yes", {}),
    "F-018": (1, 1, 0, 1, 2, 0, 3, 0, 2, 0, "yes", {}),
    "F-019": (2, 2, 0, 2, 3, 3, 1, 2, 3, 2, "yes", {}),
    "F-020": (3, 3, 3, 0, 1, 1, 2, 0, 1, 0, "yes", {}),
    "F-021": (2, 1, 2, 0, 1, 0, 2, 0, 1, 1, "yes", {}),
    "F-022": (2, 1, 3, 0, 2, 0, 3, 0, 1, 0, "yes", {}),
    "F-023": (1, 0, 1, 0, 3, 1, 3, 1, 2, 3, "yes", {"External service": "A payment and subscription provider"}),
    "F-024": (3, 3, 3, 0, 2, 1, 3, 1, 2, 3, "yes", {"External service": "An identity provider for magic links and Google sign-in"}),
    "F-025": (2, 1, 0, 1, 2, 1, 2, 1, 2, 0, "yes", {}),
    "F-026": (0, 1, 0, 0, 1, 0, 2, 0, 1, 0, "maybe", {}),
    "F-027": (0, 0, 0, 1, 2, 2, 1, 1, 2, 1, "maybe", {}),
    "F-028": (1, 1, 0, 1, 2, 1, 1, 1, 2, 1, "yes", {}),
    "F-029": (0, 1, 0, 1, 1, 1, 0, 0, 1, 1, "maybe", {}),
    "F-030": (0, 0, 0, 1, 2, 1, 1, 1, 2, 0, "no", {}),
    "F-031": (1, 0, 0, 0, 0, 0, 0, 0, 1, 0, "maybe", {}),
}  # fmt: skip
FEATURE_NAMES = {
    m.group(1): m.group(2) for m in re.finditer(r"^### (F-\d+) — (.+)$", "".join(FEATURES), re.M)
}


def score_card(i: int, fid: str) -> str:
    *vals, future, extra = SCORES[fid]
    lines = [f"\n### SC-{i:03d} — {FEATURE_NAMES[fid]}\n- Feature: {fid}\n"]
    for (name, words), v in zip(WORDS.items(), vals, strict=True):
        lines.append(f"- {name}: {v} — {words[v]}\n")
    lines.append(f"- Future: {future}\n")
    lines += [f"- {k}: {v}\n" for k, v in extra.items()]
    return "".join(lines)


def req(
    i: int, title: str, statement: str, derived: str, signal: str, prio: str, feats: str
) -> str:
    return (
        f"\n### R-{i:03d} — {title}\n- Statement: {statement}\n- Derived from: {derived}\n"
        f"- Acceptance signal: {signal}\n- Priority: {prio}\n- Features: {feats}\n"
    )


REQUIREMENTS = [
    req(1, "Tasks move through a fixed status set", "Members create tasks with a title, an optional assignee, due date and reminder, and move them through To do, In progress and Done", "W-001, W-002, W-007, D-024, A-004", "A task created on the board shows in To do and can reach Done in two moves", "must", "F-001, F-002, F-003, F-004"),
    req(2, "Boards show tasks by status and stay current", "The board shows one column per status and reflects other members' changes within 30 s", "W-007, A-001, D-037", "A status change made in one browser appears in another within 30 s", "must", "F-008, F-009"),
    req(3, "Projects group tasks", "Members group tasks into projects with one owner; a task may have no project", "W-008, D-021, D-002", "A task can be created with and without a project", "must", "F-011, F-013"),
    req(4, "Every task keeps its history", "Every change to a task appends an entry to its activity history that is never edited", "A-004, D-012", "Editing a task three times shows three history entries", "must", "F-010"),
    req(5, "Members discuss tasks", "Members comment on tasks and mention other members", "W-005, D-038", "A mention in a comment notifies the mentioned member", "must", "F-014, F-015"),
    req(6, "Members are notified in the app", "Members get an in-app notification when assigned or mentioned, within 5 s", "A-003, W-002", "Assigning a task produces a notification for the assignee within 5 s", "should", "F-016"),
    req(7, "Workspaces hold members", "Every record belongs to one workspace; admins invite members by email", "W-003, A-006, E-01", "An invited member joins and sees only that workspace's data", "must", "F-020, F-021"),
    req(8, "Roles decide what members may do", "Owner, admin, member and guest roles are enforced on every request as in the permissions matrix", "A-005, PR-007, E-03", "A guest cannot read a task that was not shared with them", "must", "F-022"),
    req(9, "Sign-in uses an identity provider", "Members sign in with an emailed one-time link or a Google account through an identity provider", "A-014, I-06", "A sign-in link works once and then expires", "must", "F-024"),
    req(10, "Files attach to tasks", "Members attach files to tasks; files are stored by an object-storage service and served only to readers of the task", "A-010", "A member without access to the task cannot download its file", "should", "F-006"),
    req(11, "Billing runs through a payment provider", "Owners and admins manage the subscription through a payment provider; we never store card data", "D-028, D-040", "Upgrading a workspace changes its plan without our system seeing card numbers", "should", "F-023"),
]  # fmt: skip


def default(i: int, uid: str, value: str, why: str, impact: str) -> str:
    return (
        f"\n### UD-{i:03d} — {uid}: {value}\n- Unknown: {uid}\n- V1 default: {value}\n"
        f"- Rationale: {why}\n- Impact if wrong: {impact}\n"
    )


DEFAULTS = [
    default(1, "U-001", "Keep activity history for the life of the task", "Simplest rule; storage is small", "Low — a retention job can be added later"),
    default(2, "U-002", "Guests are allowed on every plan", "Matches the help center, the more specific source", "Medium — billing rules change if guests become paid"),
    default(3, "U-003", "No AI triage", "Only an unverified rumour mentions it", "Low"),
    default(4, "U-004", "No public SDK in V1", "No public repositories are known", "Low"),
    default(5, "U-005", "No enterprise plan in V1", "No evidence of one", "Medium — SSO and audit would be needed"),
    default(6, "U-006", "Talks are not needed for V1", "Talks only add evidence", "None"),
    default(7, "U-007", "Official tutorials are not needed for V1", "Tutorials only add evidence", "None"),
    default(8, "U-008", "In-app notifications only", "The only channel the evidence confirms for alerts", "Medium — email delivery may be expected"),
    default(9, "U-009", "Only owners and admins delete tasks", "The safer choice for shared work", "Low — easy to widen"),
    default(10, "U-010", "Only owners and admins invite members and change roles", "Least privilege", "Low — easy to widen"),
    default(11, "U-011", "Only owners and admins manage labels and integrations", "Workspace-wide settings need an elevated role", "Low — easy to widen"),
]  # fmt: skip

SPEC_NARRATIVE = {
    "## Product summary": "tasklet-alt is task tracking for small teams: tasks on boards, grouped into projects, discussed in comments, inside one workspace per team.\n",
    "## Users": "Small teams (S-007): owners and admins who run the workspace, members who do the work, and guests who comment on shared tasks.\n",
    "## V1 goals": "- Track tasks from To do to Done on a board (R-001, R-002)\n- Collaborate with comments, mentions and notifications (R-005, R-006)\n- Run a workspace with roles and invitations (R-007, R-008)\n",
    "## V1 non-goals": "- Push-based live sync (polling in V1, see SC-009)\n- Search, recurring tasks, integrations and the public API (deferred in the parity matrix)\n",
}  # fmt: skip


def scope_defined(pm: dict[str, str], failing: bool = False) -> dict[str, str]:
    """PRODUCT_MODEL advanced to SCOPE_DEFINED (PRODUCT_MODEL locked) with the scope artifacts.

    ``failing``: U-009…U-011 have no V1 default and late research found two conflicting claims
    with no explanation — the gate fails exactly G-SC-UNKNOWNS-DEFAULTED and
    G-SC-CONFLICTS-RESOLVED while validation stays clean (the conflict is a warning).
    """
    from pflib import render, state

    files = dict(pm)
    cards = "".join(score_card(i, fid) for i, fid in enumerate(sorted(SCORES), start=1))
    reqs = REQUIREMENTS
    defaults = DEFAULTS[:8] if failing else DEFAULTS
    spec = spec_file("PRODUCT_SPEC.md", {"## Requirements": "".join(reqs)}).replace(
        "{{our_name}}", "tasklet-alt"
    )
    for heading, body in SPEC_NARRATIVE.items():
        spec = spec.replace(
            f"{heading}\n\n_To be written by the scope editor._\n", f"{heading}\n\n{body}"
        )
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        for rel, text in files.items():
            (ws / rel).parent.mkdir(parents=True, exist_ok=True)
            (ws / rel).write_text(text, encoding="utf-8")
        st = state.load(ws)
        st.locks["PRODUCT_MODEL"] = state.snapshot_locks(ws, state.State.PRODUCT_MODEL)
        state.transition(st, state.State.SCOPE_DEFINED, "2026-10-13T00:00:00Z")
        state.save(ws, st)
        extra = {
            "spec/PARITY_MATRIX.md": spec_file("PARITY_MATRIX.md", {"## Scores": cards}),
            "spec/PRODUCT_SPEC.md": spec,
            "research/UNKNOWNS.md": files["research/UNKNOWNS.md"]
            + "\n## V1 defaults\n"
            + "".join(defaults),
        }
        if failing:
            extra["research/DISCOVERY_LEDGER.md"] = files["research/DISCOVERY_LEDGER.md"] + "".join([
                d(45, "Attachments are limited to 10 MB", "Each attachment may be at most 10 MB.", "S-001", "CONFIRMED", status="conflicting-with D-046"),
                d(46, "The upload cap is 25 MB per file", "Each attachment may be at most 25 MB.", "S-008", "CONFIRMED", status="conflicting-with D-045"),
            ])  # fmt: skip
        for rel, text in extra.items():
            (ws / rel).write_text(text, encoding="utf-8")
        files.update(extra)
        render.render_all(ws)
        return {rel: (ws / rel).read_text(encoding="utf-8") for rel in files}


def spec_file(name: str, sections: dict[str, str]) -> str:
    """A template (``spec/`` unless a folder is given) with record blocks under the headings."""
    rel = name if "/" in name else f"spec/{name}"
    text = (
        Path(__file__).resolve().parents[2] / f"skills/productforge/templates/{rel}"
    ).read_text()
    text = text.replace("{{product_name}}", "Tasklet").replace(
        "{{target_url}}", "https://tasklet.example"
    )
    for heading, body in sections.items():
        head, sep, rest = text.partition(f"\n{heading}\n")
        assert sep, heading
        nxt = rest.find("\n## ")
        rest = rest + body if nxt < 0 else rest[:nxt] + body + rest[nxt:]
        text = head + sep + rest
    return text


def feature_matrix() -> str:
    template = (
        Path(__file__).resolve().parents[2]
        / "skills/productforge/templates/research/FEATURE_MATRIX.md"
    ).read_text()
    text = template.replace("{{product_name}}", "Tasklet")
    head, _, rest = text.partition("## Domains\n")
    rest = rest.split("\n## Hierarchy", 1)[1]
    return head + "## Domains\n" + DOMAINS + "\n## Hierarchy" + rest + "".join(FEATURES)


def product_model(discovery: dict[str, str], failing: bool = False) -> dict[str, str]:
    """DISCOVERY advanced to PRODUCT_MODEL with real lock snapshots and rendered views.

    ``failing``: no integrations, no Integrations & API workflow (W-006) and W-008 uncovered by
    inferences — the gate fails exactly G-PM-WORKFLOW-PER-DOMAIN, -INTEGRATIONS-COMPLETE and
    -INFERENCE-COMPLETE while validation stays clean.
    """
    from pflib import render, state

    files = dict(discovery)
    files["research/FEATURE_MATRIX.md"] = feature_matrix()
    for rel, body in WORKFLOWS:
        if not (failing and "/W-006-" in rel):
            files[rel] = body
    readme = (
        Path(__file__).resolve().parents[2]
        / "skills/productforge/templates/research/research-README.md"
    ).read_text()
    files["research/README.md"] = readme.replace("{{product_name}}", "Tasklet").replace(
        "{{target_url}}", "https://tasklet.example"
    )
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        for rel, text in files.items():
            (ws / rel).parent.mkdir(parents=True, exist_ok=True)
            (ws / rel).write_text(text, encoding="utf-8")
        st = state.load(ws)
        st.locks["DISCOVERY"] = state.snapshot_locks(ws, state.State.DISCOVERY)
        state.transition(st, state.State.PRODUCT_MODEL, "2026-10-09T00:00:00Z")
        state.save(ws, st)
        # PRODUCT_MODEL work: unknowns appended to the locked DISCOVERY file, spec/ model files
        extra = {
            "research/UNKNOWNS.md": files["research/UNKNOWNS.md"] + MODEL_UNKNOWNS,
            "spec/DOMAIN_MODEL.md": spec_file("DOMAIN_MODEL.md", {"## Records": "".join(ENTITIES)}),
            "spec/PERMISSIONS_MATRIX.md": spec_file(
                "PERMISSIONS_MATRIX.md", {"## Roles": "".join(ROLES), "## Rules": "".join(RULES)}
            ),
        }
        inferences = INFERENCES
        if failing:
            dropped = ("W-006", "W-008")
            inferences = [
                re.sub(r"I-\d\d, ", "", a) for a in INFERENCES if not any(w in a for w in dropped)
            ]
        else:
            extra["spec/INTEGRATIONS.md"] = spec_file(
                "INTEGRATIONS.md", {"## Records": "".join(INTEGRATIONS)}
            )
        extra["research/architecture-inference.md"] = spec_file(
            "research/architecture-inference.md", {"## Records": "".join(inferences)}
        )
        extra["research/sources.md"] = (
            files["research/sources.md"]
            + sources_md(COMPETITOR_SOURCES).split("\n## Records\n", 1)[1]
        )
        extra["research/COMPETITORS.md"] = spec_file(
            "research/COMPETITORS.md",
            {"## Records": "".join(COMPETITORS), "## Feature signals": "".join(SIGNALS)},
        )
        for rel, text in extra.items():
            (ws / rel).parent.mkdir(parents=True, exist_ok=True)
            (ws / rel).write_text(text, encoding="utf-8")
        files.update(extra)
        render.render_all(ws)
        return {rel: (ws / rel).read_text(encoding="utf-8") for rel in files}


def snapshots() -> dict[str, dict[str, str]]:
    state = json.dumps(STATE, indent=2) + "\n"
    full = {
        ".productforge/state.json": state,
        ".productforge/config.json": "{}\n",
        "research/sources.md": sources_md(SOURCES),
        "research/DISCOVERY_LEDGER.md": LEDGER_HEAD + "".join(CLAIMS),
        "research/UNKNOWNS.md": UNKNOWNS_HEAD + UNKNOWNS + NEW_UNKNOWNS,
        "research/product-surfaces.md": SURFACES_HEAD + "".join(SURFACES),
        "research/product-overview.md": overview(COVERAGE),
        "spec/decisions/.gitkeep": "",
        "plans/.gitkeep": "",
    }
    # Failing variant: every Tier 1 source lowered to Tier 2 (with a reason) and only 12 claims;
    # records whose references would dangle are left out, so validation stays clean.
    lowered = [
        (s[0], s[1], s[2], s[3], 2, s[5], s[6], s[7], s[8] + " Lowered from Tier 1 for this fixture.")
        if s[4] == 1 else s
        for s in SOURCES
    ]  # fmt: skip
    failing = dict(full)
    failing["research/sources.md"] = sources_md(lowered)
    failing["research/DISCOVERY_LEDGER.md"] = LEDGER_HEAD + "".join(CLAIMS[:12])
    failing["research/UNKNOWNS.md"] = (
        UNKNOWNS_HEAD + UNKNOWNS + NEW_UNKNOWNS.split("\n### U-008")[0] + "\n"
    )
    failing["research/product-surfaces.md"] = SURFACES_HEAD + SURFACES[0]
    pm = product_model(full)
    return {
        "DISCOVERY": full,
        "DISCOVERY_FAILING": failing,
        "PRODUCT_MODEL": pm,
        "PRODUCT_MODEL_FAILING": product_model(full, failing=True),
        "SCOPE_DEFINED": scope_defined(pm),
        "SCOPE_DEFINED_FAILING": scope_defined(pm, failing=True),
    }


def main(argv: list[str]) -> int:
    check = "--check" in argv
    stale = []
    for name, files in snapshots().items():
        base = ROOT / name
        for rel, text in files.items():
            path = base / rel
            if check:
                if not path.is_file() or path.read_text(encoding="utf-8") != text:
                    stale.append(f"{name}/{rel}")
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
    if check and stale:
        print("stale fixtures (run tests/fixtures/build_tasklet.py):\n  " + "\n  ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
