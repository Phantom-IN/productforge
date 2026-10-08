# Research — {{product_name}}

What ProductForge learned about {{product_name}} ({{target_url}}) from public sources. This folder
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
