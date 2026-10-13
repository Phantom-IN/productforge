<!--
base: PRODUCT_MODEL
target: spec/DOMAIN_MODEL.md
mode: append
expect: ENTITY_LOOKS_LIKE_UI_STATE
-->

### E-20 — Board filter state
- Responsibility: Which filters a member has applied on a board
- Identity: Opaque ID (format not public)
- Relationships: E-05 (N:1, required) task
- Lifecycle: created
- Mutable fields: none
- Immutable fields: task
- Deletion semantics: cascade — removed with its task
- Ownership: The member
- Authorization implications: Private to the member
- Evidence: D-037
- Confidence: CONFIRMED
