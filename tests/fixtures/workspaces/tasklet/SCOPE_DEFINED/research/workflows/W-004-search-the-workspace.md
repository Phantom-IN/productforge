### W-004 — Search the workspace
- Actor: Member
- Trigger: Member types in the search box
- Features: F-019
- Surfaces: PS-03
- Evidence: D-036
- Confidence: CONFIRMED
- Preconditions:
- Outcome: Matching tasks and projects are listed

## Steps

1. [observed] Member types a query and sees tasks and projects together — D-036
2. [implied-system] Query a combined index of tasks and projects scoped to the workspace — F-019, D-043
3. [implied-system] Return only results the member may see — F-022

## Variations & edge cases

- Guests see only shared tasks (D-004)

## Engineering requirements surfaced

- Step 2: multi-entity search scoped by workspace
- Step 3: permission filtering of results

## Open questions

- None yet.
