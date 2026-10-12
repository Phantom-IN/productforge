<!--
base: PRODUCT_MODEL
target: spec/DOMAIN_MODEL.md
mode: replace E-07
expect: RELATIONSHIP_INCONSISTENT
-->
### E-07 — Label
- Responsibility: A workspace-wide tag tasks may carry
- Identity: Opaque label ID (format not public)
- Human-readable key: Label name
- Stable after creation: unknown
- Relationships: E-01 (N:1, required) workspace; E-05 (N:1, optional) tasks
- Lifecycle: created → in use
- Mutable fields: name
- Immutable fields: workspace
- Deletion semantics: cascade — removing a label removes it from tasks (inferred)
- Ownership: The workspace
- Authorization implications: Defined per workspace (U-011)
- Features: F-005
- Evidence: D-014
- Confidence: CONFIRMED
- Related unknown: U-011
