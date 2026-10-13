### W-002 — Assign a task
- Actor: Member
- Trigger: Member picks an assignee on a task
- Features: F-002, F-016
- Surfaces: PS-03, PS-05
- Evidence: D-001, D-019
- Confidence: CONFIRMED
- Preconditions: The task exists
- Outcome: The task has one assignee who is notified

## Steps

1. [observed] Member chooses one assignee from the workspace members — D-001
2. [observed] The assignee receives an in-app notification — D-019
3. [implied-system] Replace any previous assignee (one assignee per task) — F-002
4. [implied-system] Record the change in the task's activity — F-010
5. [implied-system] Create the notification for the new assignee — F-016

## Variations & edge cases

- Reassigning notifies the new assignee only (D-044)

## Engineering requirements surfaced

- Step 3: single nullable assignee reference
- Step 5: notification on assignment change

## Open questions

- None yet.
