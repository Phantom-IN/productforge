<!--
base: PRODUCT_MODEL
target: spec/DOMAIN_MODEL.md
mode: append
expect: ENTITY_WITHOUT_PERMISSIONS
-->

### E-20 — Reminder
- Responsibility: A scheduled nudge before a task is due
- Identity: Opaque reminder ID (format not public)
- Relationships: E-05 (N:1, required) task
- Lifecycle: scheduled → sent
- Mutable fields: time
- Immutable fields: task
- Deletion semantics: cascade — removed with its task
- Ownership: The task's workspace
- Authorization implications: Follows the task's access rules
- Evidence: D-023
- Confidence: CONFIRMED
