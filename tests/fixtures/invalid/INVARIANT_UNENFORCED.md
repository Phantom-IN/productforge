<!--
base: ARCHITECTURE_LOCKED
target: spec/ARCHITECTURE.md
mode: replace INV-06
expect: INVARIANT_UNENFORCED
-->
### INV-06 — Secrets stay encrypted
- Rule: Credentials and tokens are stored only encrypted or hashed
- Reason: A leak must not expose working credentials
- Enforced by: everyone is careful
- Derived from: ADR-009
