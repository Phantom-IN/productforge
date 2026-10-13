# Research — Tasklet

What ProductForge learned about Tasklet (https://tasklet.example) from public sources. This folder
describes the **target**; what *we* will build lives in `../spec/`.

| File | What it holds |
|---|---|
| `sources.md` | Every source (`S-`), with category and tier |
| `product-overview.md` | What the product is, its major areas, scope and source coverage |
| `DISCOVERY_LEDGER.md` | Normalised claims (`D-`) with evidence and confidence |
| `UNKNOWNS.md` | Questions public sources cannot answer (`U-`) and their V1 defaults |
| `product-surfaces.md` | Visible product surfaces (`PS-`) |
| `FEATURE_MATRIX.md` | Feature hierarchy (`F-`) |
| `workflows/` | Reconstructed workflows (`W-`), one per file |
| `architecture-inference.md` | Observations → engineering requirements (`A-`) |
| `COMPETITORS.md` | Optional competitor pass (`C-`, `FS-`) |

Never edit these files by hand: agents stage changes and `pf.py merge` writes them.

## Workflows

<!-- pf:generated:start workflows -->
| W | Name | Actor | Features | Confidence | Observed steps | Implied system steps |
|---|---|---|---|---|---|---|
| W-001 | Create a task | Member | F-001, F-004, F-008 | CONFIRMED | 3 | 6 |
| W-002 | Assign a task | Member | F-002, F-016 | CONFIRMED | 2 | 3 |
| W-003 | Invite a member | Admin | F-021, F-022 | CONFIRMED | 2 | 3 |
| W-004 | Search the workspace | Member | F-019 | CONFIRMED | 1 | 2 |
| W-005 | Comment on a task | Member or guest | F-014, F-015 | CONFIRMED | 1 | 3 |
| W-007 | Change a task's status | Member | F-004, F-009 | CONFIRMED | 2 | 2 |
| W-008 | Archive a project | Member | F-012 | CONFIRMED | 2 | 1 |
<!-- pf:generated:end -->
