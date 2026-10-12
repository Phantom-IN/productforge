### W-001 — Create a task
- Actor: Member
- Trigger: Member adds a task on the board
- Features: F-001, F-004, F-008
- Surfaces: PS-03
- Evidence: D-024, D-037
- Confidence: CONFIRMED
- Preconditions: Member belongs to the workspace
- Outcome: A new task appears on the board

## Steps

1. [observed] Member opens the board and adds a task to a status column — D-037
2. [observed] Member enters a title; the task starts in To do — D-024
3. [observed] Member may set an assignee, a due date and labels — D-001, D-023, D-014
4. [implied-system] Check the member may create tasks in this workspace — F-022
5. [implied-system] Persist the task with its workspace and optional project — F-001, D-002
6. [implied-system] Append an activity entry for the task — F-010
7. [implied-system] Index the task for search — F-019
8. [implied-system] Broadcast the change to connected clients — F-009
9. [implied-system] Notify the assignee, if one was set — F-016

## Variations & edge cases

- Guests can only comment, not create tasks (D-004)
- Free plans are limited to five members (D-040)

## Engineering requirements surfaced

- Step 5: tasks reference a workspace and an optional project
- Step 7: a search index over tasks
- Step 8: realtime fan-out of task changes
- Step 9: notifications triggered by task events

## Open questions

- None yet.
