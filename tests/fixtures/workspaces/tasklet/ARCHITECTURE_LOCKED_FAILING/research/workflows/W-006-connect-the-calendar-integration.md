### W-006 — Connect the calendar integration
- Actor: Member
- Trigger: Member enables calendar sync
- Features: F-028
- Surfaces: PS-06
- Evidence: D-033
- Confidence: CONFIRMED
- Preconditions:
- Outcome: Due dates appear in the external calendar

## Steps

1. [observed] Member connects a calendar from the integrations settings — D-033
2. [implied-system] Store the integration credentials encrypted — F-028, D-016
3. [implied-system] Sync due dates to the calendar when they change — F-028, F-003

## Variations & edge cases

- Disconnecting stops the sync

## Engineering requirements surfaced

- Step 2: encrypted third-party credentials
- Step 3: outbound sync job

## Open questions

- None yet.
