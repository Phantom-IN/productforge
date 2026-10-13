### ADR-008 — Object storage with signed URLs
- Topic: files
- Context: Attachments must be durable and private to task readers (R-010, A-010)
- Decision: Files go to S3-compatible object storage; the API issues short-lived signed URLs after a policy check
- Alternatives: database blobs; a local disk volume; a hosted file service
- Reason: Durable and cheap; signed URLs keep the policy check in our API
- Trade-offs: Signed URLs can be shared until they expire (5 minutes)
- Satisfies: R-010, A-010
- Status: accepted
