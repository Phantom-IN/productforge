# Discovery ledger — {{product_name}}

Normalised claims about what {{product_name}} visibly does. **One observable fact = one claim**;
seeing the same fact again adds evidence to the existing claim instead of creating a new one.

Confidence (rules: `references/confidence-rules.md`): `CONFIRMED` — a Tier ≤ 2 source states it ·
`PROBABLE` — two independent sites (Tier ≤ 4) or one Tier ≤ 3 source · `INFERRED` — an engineering
conclusion `Derived from` other records · `UNKNOWN` — tied to an open question (`Related unknown`).

Conflicting claims stay visible (`Status: conflicting-with …`) until an unknown or a `Resolution`
explains them. Records are added only by `pf.py merge`.

## Records
