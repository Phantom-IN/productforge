### ADR-015 — Stowage for object storage
- Topic: vendor
- Context: Attachments are stored privately and served by signed URL (R-010, ADR-008)
- Decision: Use Stowage (https://stowage.example), an S3-compatible object store. Pricing: per stored gigabyte and per outbound gigabyte. Sandbox: a local S3-compatible emulator in development and a test bucket in CI. Webhooks: none used. Fallback: any S3-compatible store, because the code uses only the S3 protocol
- Alternatives: A database blob column; a self-hosted S3-compatible server
- Reason: S3-compatible access with encryption at rest and no servers to run
- Trade-offs: Outbound traffic is billed; signed URLs expire in 5 minutes
- Satisfies: R-010
- Status: accepted
