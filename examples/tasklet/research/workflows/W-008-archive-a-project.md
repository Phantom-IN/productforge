### W-008 — Archive a project
- Actor: Member
- Trigger: Project owner archives a project
- Features: F-012
- Surfaces: PS-04
- Evidence: D-022
- Confidence: CONFIRMED
- Preconditions: The member owns the project
- Outcome: The project and its tasks leave the boards until restored

## Steps

1. [observed] The owner archives the project; it disappears from boards — D-022
2. [observed] The project can be restored later — D-022
3. [implied-system] Mark the project archived without deleting its tasks — F-012

## Variations & edge cases


## Engineering requirements surfaced

- Step 3: archive is a reversible state, not a delete

## Open questions

- None yet.
