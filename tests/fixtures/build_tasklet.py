"""Deterministic generator for the synthetic Tasklet fixture workspaces (dev-only).

    python3.11 tests/fixtures/build_tasklet.py          # rewrite the snapshots
    python3.11 tests/fixtures/build_tasklet.py --check  # exit 1 if the committed files differ

Snapshots (tests/fixtures/workspaces/tasklet/):
- DISCOVERY          — a gate-passing DISCOVERY workspace.
- DISCOVERY_FAILING  — fails exactly G-DISC-TIER1 and G-DISC-MIN-CLAIMS (no Tier 1 source, too few
                       claims) while validating cleanly.

Everything is fictional ("Tasklet", *.example hosts). Never put real third-party content here.
Existing records must stay byte-identical (lock/overlay tests depend on them): append, don't edit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "workspaces" / "tasklet"

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
    return {"DISCOVERY": full, "DISCOVERY_FAILING": failing}


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
