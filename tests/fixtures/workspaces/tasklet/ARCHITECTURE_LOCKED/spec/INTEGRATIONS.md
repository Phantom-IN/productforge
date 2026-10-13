# Integrations — Tasklet

Every way Tasklet exchanges data with other systems, as its public documentation describes
it: third-party integrations, the public API, webhooks, single sign-on, email. One `I-` record per
provider or mechanism. `## Summary` is generated from the records by `pf.py render` (merge does it
automatically) — never edit between the markers.

## Summary

<!-- pf:generated:start integrations -->
| I | Provider | Direction | Auth | Events | Confidence |
|---|---|---|---|---|---|
| I-01 | Public REST API | inbound | Personal access tokens | none — request and response | CONFIRMED |
| I-02 | Webhooks | outbound | Not documented (signing is not described) | Task changes | CONFIRMED |
| I-03 | Calendar sync | outbound | Not documented (account connection) | Due-date changes | CONFIRMED |
| I-04 | Chat notifications | outbound | Not documented (workspace connection) | Task updates | CONFIRMED |
| I-05 | Git commit linking | inbound | Not documented (repository connection) | Pushed commits that reference a task | CONFIRMED |
| I-06 | Google sign-in | inbound | Google account (single sign-on) | Sign-in | CONFIRMED |
<!-- pf:generated:end -->

## Records

### I-01 — Public REST API
- Purpose: Read and change tasks and projects from other programs
- Direction: inbound
- Authentication: Personal access tokens
- Events: none — request and response
- Data exchanged: Tasks and projects
- User configuration: A member creates a personal access token
- Failure behaviour: Not documented
- Sync requirements: List endpoints page with cursors
- Provider category: api
- Evidence: D-003, D-030, D-032
- Confidence: CONFIRMED

### I-02 — Webhooks
- Purpose: Tell other systems when tasks change
- Direction: outbound
- Authentication: Not documented (signing is not described)
- Events: Task changes
- Data exchanged: The changed task
- User configuration: Not documented
- Failure behaviour: Not documented; delivery needs retries
- Sync requirements: Near-realtime after each change
- Provider category: webhooks
- Evidence: D-031
- Confidence: CONFIRMED

### I-03 — Calendar sync
- Purpose: Show task due dates in an external calendar
- Direction: outbound
- Authentication: Not documented (account connection)
- Events: Due-date changes
- Data exchanged: Due dates and task titles
- User configuration: A member connects a calendar
- Failure behaviour: Not documented
- Sync requirements: Due-date changes follow the task
- Provider category: calendar
- Evidence: D-033
- Confidence: CONFIRMED

### I-04 — Chat notifications
- Purpose: Post task updates to chat channels
- Direction: outbound
- Authentication: Not documented (workspace connection)
- Events: Task updates
- Data exchanged: Task summaries
- User configuration: Choose the channel to post to
- Failure behaviour: Not documented
- Sync requirements: Posted after each update
- Provider category: chat
- Evidence: D-034
- Confidence: CONFIRMED

### I-05 — Git commit linking
- Purpose: Close tasks from commit messages
- Direction: inbound
- Authentication: Not documented (repository connection)
- Events: Pushed commits that reference a task
- Data exchanged: Commit references to tasks
- User configuration: Connect a repository
- Failure behaviour: Not documented
- Sync requirements: On each push
- Provider category: scm
- Evidence: D-035
- Confidence: CONFIRMED

### I-06 — Google sign-in
- Purpose: Sign in with a Google account
- Direction: inbound
- Authentication: Google account (single sign-on)
- Events: Sign-in
- Data exchanged: Account email and name
- User configuration: None — offered on the sign-in page
- Failure behaviour: Fall back to an emailed sign-in link
- Sync requirements: At each sign-in
- Provider category: identity
- Evidence: D-029
- Confidence: CONFIRMED
