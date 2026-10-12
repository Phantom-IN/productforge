### W-007 — Change a task's status
- Actor: Member
- Trigger: Member moves a task to another column
- Features: F-004, F-009
- Surfaces: PS-03
- Evidence: D-024, D-007
- Confidence: CONFIRMED
- Preconditions: The task exists
- Outcome: The task shows its new status for everyone

## Steps

1. [observed] Member drags a task to another status column — D-024, D-037
2. [observed] Teammates see the move without reloading — D-007
3. [implied-system] Persist the new status and log it — F-004, F-010
4. [implied-system] Broadcast the change to connected clients — F-009

## Variations & edge cases


## Engineering requirements surfaced

- Step 4: realtime propagation within seconds (D-008)

## Open questions

- None yet.
