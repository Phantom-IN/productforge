# Security

## Network use

Only `pflib/discover.py` touches the network from scripts: it fetches `robots.txt` first, never
requests a disallowed URL, rate-limits itself and identifies itself. Agents fetch public pages with
Claude Code's WebFetch/WebSearch. Tests never use the network.

## Prompt injection

Fetched pages and delegated skill output are **data, never instructions**. Agents are told to
ignore instructions found in content and to flag the source (`possible prompt injection`).
Delegated output lands in `staging/<run>/raw/`, is never merged, and is normalised by a
ProductForge agent into records that cite the original URLs.

## Installs

`pf.py deps install … --confirmed` runs `claude plugin install` only after the user agreed in the
session; without `--confirmed` it prints the command and installs nothing.

## The stage guard hook

`hooks/stage_guard.py` (PreToolUse on Write/Edit/MultiEdit/NotebookEdit) acts only inside a
directory with `.productforge/state.json`. It denies direct writes to canonical record files,
closed-stage artifacts, generated views and `.productforge/` itself, and allows everything else.
It reads the tool payload from stdin, writes nothing, and **fails open** on any internal error so a
bug cannot block a session. Disable it by disabling the plugin.

## Observe mode (v2, opt-in)

Observe mode is the one exception to "public sources only", and only after the user's recorded
consent: the **user** signs in to their own account in a visible browser window and drives the
product; ProductForge records, on that computer only, what the product does. It never clicks,
types or answers a dialog for the user.

| Stored (redacted, in `.productforge/observe/<session>/`) | Never stored |
|---|---|
| Route templates (`/tasks/:id`), page titles, UI labels, headings | Typed values, passwords, payment fields |
| Clicks, submits, field *names and types* | `Authorization`, `Cookie`, `Set-Cookie`, API keys, any non-allowlisted header |
| Request/response **shapes** (`{"title": "string"}`), status codes | Body values, query values, GraphQL query text and variable values |
| Realtime message shapes per channel | Names of repeated items (rows, list entries: task titles, people) — stored as `<item>` |
| Screenshots (`observe.screenshots`: on · blur · off) with password, payment and iframe areas masked | Traffic to hosts outside `observe.allowed_hosts` |
| Console errors and dialog texts with URLs, quoted text, e-mails, IPs, numbers and tokens masked | The browser profile (cookies, storage): it is temporary and deleted when the session ends |

Residual risk: page titles and headings outside lists can still contain names the user typed;
JSON field names describe the product's schema (that is the point). Sessions are local, git-
ignored, never merged or published, deleted after `observe.retain_days` (30), and deletable any
time with `pf.py observe discard <session> --reason`. The control panel listens on 127.0.0.1 only
and needs the session's random token.

## What ProductForge never does

Outside observe mode: log in, use test accounts or inspect network traffic. Ever: download brand
assets, use screenshots as design assets, copy proprietary code, or quote more than
`quotes.max_words` (25) words of a source.

## Reporting

Please report vulnerabilities privately to the maintainer (see `.claude-plugin/plugin.json`)
rather than in a public issue.
