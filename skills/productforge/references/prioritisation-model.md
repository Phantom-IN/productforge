# Prioritisation model

How SCOPE_DEFINED reduces the reconstructed product to a realistic V1 (IMPLEMENTATION_PLAN.md §14,
IDEA §20–§22). The scope editor scores; **`pf.py score` does all arithmetic and applies the rules**
(`pflib/score.py`). Nobody types a priority or a decision.

## Score cards

One `SC` record per feature in `spec/PARITY_MATRIX.md` `## Scores`. Every criterion is
`<0-3> — <rationale>` (`BAD_SCORE` otherwise); the rationale cites what justifies it (workflows,
inferences, entities, integrations, claims).

| Criterion | Weight | Direction | 0 | 1 | 2 | 3 |
|---|---:|---|---|---|---|---|
| Core value | 3 | + | peripheral | supports the core loop | important daily | the reason the product exists |
| User frequency | 2 | + | rarely | now and then | weekly | every session |
| Dependency importance | 3 | + | nothing needs it | one feature | several features | most features need it |
| Differentiation | 2 | + | not a selling point | expected | a visible strength | a reason to choose it |
| Engineering complexity | 2 | − | trivial | CRUD | new moving parts | realtime, search, payments, sync |
| Infrastructure complexity | 1 | − | none | small addition | a new service | significant infrastructure |
| Security impact | 1 | − | none | minor | exposes data if wrong | security-critical |
| Operational cost | 1 | − | none | small | noticeable | high |
| Time to implement | 2 | − | hours | days | about a week | weeks |
| External availability | — | decision only | no service fits | partial | good services | mature services cover it |

Weights are config knobs (`scope.weights.*`).

```text
priority = Σ weight × score (benefits) − Σ weight × score (costs)   (range −21 … 30)
         + 2 when ≥ 2 competitors offer the feature (table stakes, Phase 12)
```

## Decision rules (in order)

| Rule | When | Decision |
|---|---|---|
| R2 | External availability 3 and Engineering complexity ≥ 2 | USE EXTERNAL SERVICE |
| R3 | priority ≥ `scope.build_threshold` and Engineering complexity 3 | BUILD SIMPLIFIED |
| R4 | priority ≥ `scope.build_threshold` | BUILD NOW |
| R5 | priority ≥ `scope.defer_threshold` | DEFER |
| R6 | otherwise | DROP |
| R1 | **floor**: Dependency importance 3 and the result is DEFER/DROP | BUILD SIMPLIFIED if Engineering complexity ≥ 2, else BUILD NOW |

R1 is applied last so a dependency can still go to an external service (sign-in → an identity
provider) but is **never deferred or dropped**. `BUILD SIMPLIFIED` needs `Simplification` (what V1
leaves out); `USE EXTERNAL SERVICE` needs `External service` (the *kind* of service — choosing a
vendor is an architecture decision).

## Thresholds and calibration

`scope.build_threshold` = **6**, `scope.defer_threshold` = **−4**. Calibrated on the Tasklet
fixture: with honest 0–3 scores the core loop (tasks, statuses, boards, projects, comments)
scores 17–19, everyday supporting features (assignment, mentions, notifications, invitations,
roles) 6–12, nice-to-haves (labels, archive, digests, guests, integrations) −4…5, and features
whose cost clearly exceeds their value −9 and below. In words: **build** when weighted benefits
beat weighted costs by 6, **defer** when net cost is at most 4, **drop** beyond that. The plan's
first guess (18/8) left only the five top features in V1. Revisit after the Phase 17 dogfood run;
record any change here and in the CHANGELOG.

## Overrides

A computed decision may be overridden — by the scope editor in its review pass, or by the user —
only with `Override decision` **and** `Override reason` (`OVERRIDE_NO_REASON`). Overrides are
amendments of the score card (logged with their `Why`), shown in `## Overrides` and marked
"(override)" in every view. The user's adjustments are recorded with
`pf.py override <F-ID> --decision <D> --reason "<their words>"` (or `--clear`).

## Examples

- **Sign-in** — core 3, dependency 3, engineering 2, external 3 → R2 USE EXTERNAL SERVICE
  (an identity provider); R1 would have kept it in V1 anyway.
- **Live updates** — computes DEFER (engineering 3, infra 3, time 3); overridden to BUILD SIMPLIFIED
  because realtime is the target's selling point: V1 refreshes boards on focus and polls.
- **SAML single sign-on** (IDEA §21) — core 1, frequency 0, dependency 0, differentiation 1,
  engineering 3, infrastructure 1, security 3, operations 1, time 3, external 1 → priority
  5 − 17 = **−12** → R6 DROP. Enterprise buyers ask for it, so the scope editor overrides to DEFER
  ("an enterprise plan is a V1 non-goal; keep SAML on the roadmap").

## Outputs

- `spec/PARITY_MATRIX.md` `## Matrix` — `Feature | Target | Our V1 | Future | Decision | Notes`
  (Our V1: ✓ · Simplified · External · ✗) and `## Overrides`, generated.
- `research/FEATURE_MATRIX.md` — the `MVP`, `Decision`, `Score` columns, generated (F records stay
  locked).
- `spec/PRODUCT_SPEC.md` — `R` requirements for every V1 feature (`FEATURE_WITHOUT_REQUIREMENT`),
  the generated reduction funnel and accepted defaults.
- `research/UNKNOWNS.md` `## V1 defaults` — one `UD` per unknown (`G-SC-UNKNOWNS-DEFAULTED`).
