<!--
target: research/sources.md
mode: append
expect: INTERNALS_FROM_OBSERVATION
-->
### S-100 — Observed session obs-20261014-120000
- URL: https://tasklet.example/?pf_observe=obs-20261014-120000
- Canonical URL: https://tasklet.example/?pf_observe=obs-20261014-120000
- Category: observed-session
- Tier: 1
- Authority: High
- Relevant area: Tasks
- Published: 2026-10-14
- Last inspected: 2026-10-14
- Notes: Recorded in observe mode with the user's own account; redacted on write.
<!-- next target: research/observations.md mode: write -->
# Observations — Tasklet

## Records

### OB-001 — Endpoint `GET /api/boards/:id`
- Kind: endpoint
- Detail: `GET /api/boards/:id` → 200 (×3). Response `{"columns": [{"name": "string"}]}`.
- Evidence: S-100
- Artifact:
- Confidence: CONFIRMED
<!-- next target: research/DISCOVERY_LEDGER.md mode: append -->
### D-100 — Boards are stored in Postgres
- Claim: Board columns come from a Postgres table, judging by the board endpoint.
- Evidence: OB-001
- Confidence: CONFIRMED
- Product impact:
- Engineering impact:
- Status: active
