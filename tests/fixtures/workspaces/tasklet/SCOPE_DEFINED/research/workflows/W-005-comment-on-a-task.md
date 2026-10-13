### W-005 — Comment on a task
- Actor: Member or guest
- Trigger: Someone writes a comment
- Features: F-014, F-015
- Surfaces: PS-03
- Evidence: D-038, D-004
- Confidence: CONFIRMED
- Preconditions: Access to the task
- Outcome: The comment appears and mentioned members are told

## Steps

1. [observed] A member or guest writes a comment, optionally mentioning members — D-038, D-004
2. [implied-system] Persist the comment on the task — F-014
3. [implied-system] Notify mentioned members — F-015, F-016
4. [implied-system] Broadcast the new comment to viewers of the task — F-009

## Variations & edge cases

- Guests may comment only on tasks shared with them (D-004)

## Engineering requirements surfaced

- Step 3: mention parsing and notifications

## Open questions

- None yet.
