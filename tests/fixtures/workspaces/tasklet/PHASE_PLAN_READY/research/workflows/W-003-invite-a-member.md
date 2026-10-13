### W-003 — Invite a member
- Actor: Admin
- Trigger: Admin invites someone by email
- Features: F-021, F-022
- Surfaces: PS-06, PS-02
- Evidence: D-026, D-027
- Confidence: CONFIRMED
- Preconditions: Admin role in the workspace
- Outcome: The invitee joins with a role

## Steps

1. [observed] Admin enters an email address and a role — D-026, D-027
2. [observed] The invitee follows the emailed link and signs in — D-029
3. [implied-system] Check the admin may invite members — F-022
4. [implied-system] Create a pending invitation and send the email — F-021
5. [implied-system] On acceptance create the membership with the chosen role — F-020

## Variations & edge cases

- Free plan member limit blocks extra invitations (D-040)

## Engineering requirements surfaced

- Step 4: invitation tokens with expiry
- Step 5: workspace membership with a role

## Open questions

- U-002
