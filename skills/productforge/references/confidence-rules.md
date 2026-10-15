# Confidence rules

Every claim-bearing record carries a `Confidence`, and `pf.py validate` checks it mechanically
(code in `scripts/pflib/confidence.py`). Never pick a confidence by feel:
pick the strongest one the evidence satisfies.

## The rules

| Confidence | Requirement | Typical evidence |
|---|---|---|
| `CONFIRMED` | `Evidence` resolves to ≥1 source with **Tier ≤ 2** | Official docs page describing the feature |
| `PROBABLE` | ≥2 sources with **Tier ≤ 4 on distinct sites**, or ≥1 source with **Tier ≤ 3** | Two community threads on different sites; one solid review |
| `INFERRED` | `Derived from` cites ≥1 observation record (a claim, feature, workflow, inference — not a source or unknown) | "Live updates across clients ⇒ realtime propagation needed" |
| `UNKNOWN` | `Related unknown` cites a `U-` record | Public evidence is missing or contradictory |

- **Evidence resolves transitively.** `Evidence` may cite sources (`S-`) or other records; a feature
  citing `D-041` inherits D-041's sources. The rules apply to the sources found that way.
- **Distinct sites** means different registrable domains: `docs.tasklet.example` and
  `tasklet.example` are the same site; `community.example` and `social.example` are not.
- **Tier 5 caps at INFERRED.** Unverified-only evidence can never be CONFIRMED or PROBABLE.
- The enum is case-sensitive: `CONFIRMED`, not `Confirmed`.

## Worked examples

Good CONFIRMED — an official docs source (Tier 1):

```markdown
### D-002 — Project membership is optional for tasks
- Claim: Tasks may optionally belong to a project.
- Evidence: S-002
- Confidence: CONFIRMED
- Product impact: Project membership cannot be mandatory.
- Engineering impact: tasks.project_id must be nullable.
- Status: active
```

Bad CONFIRMED — a single forum thread (Tier 4) → `CONFIDENCE_RULE`. Downgrade it to `PROBABLE`
once a second, independent site agrees; until then it is at best `INFERRED` from other claims.

PROBABLE from two Tier-4 sources on different sites:

```markdown
### D-005 — Recurring tasks appear to be supported
- Claim: Users report creating tasks that repeat on a schedule.
- Evidence: S-010, S-011
- Confidence: PROBABLE
```

INFERRED — an engineering conclusion from an observation, not a fact about the product:

```markdown
### D-008 — Task changes need near-realtime propagation
- Claim: The system needs near-realtime propagation of task changes to connected clients.
- Evidence: S-009
- Confidence: INFERRED
- Derived from: D-007
```

UNKNOWN — a rumour that public sources cannot settle:

```markdown
### D-011 — Automatic AI triage is rumoured
- Evidence: S-014
- Confidence: UNKNOWN
- Related unknown: U-003
```

## One fact, one claim

The same fact seen on many pages is **one** D record with several evidence IDs, not many records.
Before adding a claim, look for an existing one: if you find it, stage a record with the same claim
text — merge adds your evidence to the existing claim (and may strengthen what it can support).
`NEAR_DUPLICATE_TITLE` warnings flag likely duplicates.

## Conflicts

When sources disagree, keep both claims and make the disagreement explicit:

1. Mark both: `Status: conflicting-with D-010` on D-009 and `Status: conflicting-with D-009` on
   D-010 (one-sided declarations are `CONFLICT_ASYMMETRIC` errors).
2. Explain it, in one of two ways:
   - a `U-` record whose `Related` (or `Available evidence`) cites both claims, or
   - a `Resolution:` line naming the deciding source (e.g. "S-004 is newer Tier 1 documentation").
3. Never silently drop or overwrite one side. Unexplained conflicts are `CONFLICT_UNRESOLVED`
   warnings during DISCOVERY and PRODUCT_MODEL, and block the SCOPE_DEFINED gate.

## Superseding and rejecting

- A claim replaced by a better one: `Status: superseded-by D-014` (the target must be a D record
  that exists). Never delete it.
- A claim found to be wrong: `Status: rejected` plus `- Reason: …`.
