# Dogfood v3: autonomous run

Status: **done**, 2026-10-24. On shlink.io (an open-source URL shortener), `pf.py auto start`
went from a URL to a completed PHASE_PLAN_READY with no one at the keyboard. The run took three
segments. The two stops were the driver's stall guard catching real defects, both fixed and listed
under Issues. The third segment ran to completion with no stall.

## Purpose

Prove that `pf.py auto start` takes a small real public product from a URL to a completed
PHASE_PLAN_READY unattended, using the v3 passes: depth, unknown audit, competitors, headline review,
vendor ADRs and consistency review.

It passes when:
- `ORCHESTRATOR_PROMPT.md` exists;
- the gate shows no `UNDECIDED_CHOICE` or `PHASE_OPEN_DECISION`;
- the run is recorded below.

## Runbook

Keep it small: low caps and one pair of competitors.

```bash
PF="python3.11 skills/productforge/scripts/pf.py"
$PF init https://shlink.io --out .dogfood/shlink-v3 --name shortkit \
  --scope "URL shortening: short URL creation and management, tags, visit tracking and statistics, multiple domains, REST API and integrations"
# low caps (config.json takes dotted keys; `pf.py config set` validates and logs each change)
$PF config set research.max_sources 30 --reason "dogfood: small run" --workspace .dogfood/shlink-v3
$PF config set research.min_sources_gate 12 --reason "dogfood" --workspace .dogfood/shlink-v3
$PF config set research.min_claims_gate 20 --reason "dogfood" --workspace .dogfood/shlink-v3
$PF config set model.max_workflows 5 --reason "dogfood: deliberately below the domain count" --workspace .dogfood/shlink-v3
$PF config set competitors.max 2 --reason "dogfood" --workspace .dogfood/shlink-v3
$PF config set auto.max_sources_ceiling 60 --reason "dogfood" --workspace .dogfood/shlink-v3
$PF config set auto.main_model sonnet --reason "dogfood: cheaper orchestrator" --workspace .dogfood/shlink-v3
# preview, then run (the first call without --confirmed prints the consent text and its hash)
$PF auto start --workspace .dogfood/shlink-v3 --dry-run
$PF auto start --workspace .dogfood/shlink-v3 --json          # shows consent text + text_sha256
caffeinate -is $PF auto start --workspace .dogfood/shlink-v3 --text-sha256 <sha> --confirmed --json
```

Follow the run with `pf.py auto status` or `.productforge/auto.log`, and stop it with
`pf.py auto stop`. Re-running `auto start` resumes. The workspace stays under the git-ignored
`.dogfood/`.

## Results

| Item | Value |
|---|---|
| Product and scope | Shlink (shlink.io) as our "shortkit": short URLs, tags, visit statistics, multiple domains, REST API |
| Models | Sonnet for the orchestrator and for every subagent |
| Sessions, retries, stalls | 13 headless sessions in 3 segments, 0 retries, 2 stalls (both real defects, fixed between segments) |
| Wall-clock time | about 1 h 50 min of running (21:10–23:03 UTC), not counting the fixes between segments |
| Research | 59 sources, 137 claims, 59 unknowns, 16 surfaces. Discovery index: 19 in-scope candidates, 14 read (depth 0.74 ≥ 0.6), no unread navigation pages |
| Model | 129 features in 8 domains, 8 workflows, 8 entities, 6 roles, 58 permission rules, 19 integrations, 16 inferences |
| Competitors | 2 (Kutt, YOURLS), found by the competitor-discovery pass from the comparison sources |
| Scope | 16 requirements. 7 headline features cut (6 DEFER, 1 DROP), each with a reviewed reason in `PRODUCT_SPEC.md` |
| Architecture | 14 ADRs, 3 of them `Topic: vendor` (MaxMind GeoLite2, PostgreSQL, GitHub Actions/GHCR). Toolchain of 11 concerns, every version verified against its registry on 2026-10-25. Env contract of 13 variables |
| Plan | 16 phases. `lint-phases` clean, `trace` 16/16 requirements with 0 errors, `ORCHESTRATOR_PROMPT.md` written (163 lines) |
| Decisions logged | 6: workflow cap 5→8; source budget raised for competitors; competitors Kutt and YOURLS; remaining findings accepted after the repair passes; headline cuts kept with reasons; scope accepted |
| Final state | PHASE_PLAN_READY completed (`auto-complete`). Gate 7/7. `validate`: 0 errors, 6 warnings (4 `UNKNOWN_UNREAD_CANDIDATES` from unknowns added after DISCOVERY closed, 2 near-duplicate titles) |

## Issues

Each issue below was fixed before the next segment, with a regression test, and is listed under
"Fixed (dogfood)" in `CHANGELOG.md`.

1. **The workflow cap was below the number of required domains.**
   - Cause: `model.max_workflows` was 5 for 8 domains. The candidate selector filled the cap alphabetically and dropped the three core domains, so `G-PM-WORKFLOW-PER-DOMAIN` could never pass.
   - Fix: the selector now always returns one candidate per gate-required domain, largest first, and reports `cap_below_required` and `effective_cap`. The driver raises the cap (bounded by `auto.max_workflows_ceiling`) and logs a decision. On the next segment this happened automatically.
2. **There was no supported way to change a cap during a run.**
   - Cause: the orchestrator may not edit `.productforge/config.json`.
   - Fix: `pf.py config get|list|set --reason`, which validates the value and logs a `config-set` history event.
3. **Superseded records failed the confidence rules.**
   - Cause: three UNKNOWN features had been corrected and superseded, but `CONFIDENCE_RULE` still flagged the originals, so `G-VALIDATE-CLEAN` failed. This bug predates v3.
   - Fix: confidence rules skip inactive records.
4. **The orchestrator merged runs before repairing them.**
   - Cause: in the features pass it merged three runs whose preflight had errors without spending its repair passes.
   - Fix: `merge` refuses (`MERGE_BEFORE_REPAIR`) while repair passes remain, unless `--accept-findings`.
5. **Autonomous sessions stopped to ask.**
   - Cause: two sessions ended with a question to the user, about the workflow cap and about competitors.
   - Fix: autonomous mode now applies the recommended option through `pf.py`, logs it with `decide`, and never ends a session with a question. A prompt-contract test covers this.
6. **Competitors could not run where the gate needs them.**
   - Cause: `G-SC-COMPETITOR-SIGNAL` lives in SCOPE_DEFINED, but `competitors` was a PRODUCT_MODEL-only command and `next_command` never suggested it. PRODUCT_MODEL closed without competitors, and the only way back was `reopen`. `competitor-candidates` also offered comparison sites ("AlternativeTo", "OSSAlt") and the junk name "URL".
   - Fix:
     - `competitors` is allowed while SCOPE_DEFINED is open (new C, FS and S records are appends);
     - `next_command` suggests it whenever the signal is missing and not waived;
     - aggregator sites and generic one-word names are filtered out (`competitors.aggregator_names`);
     - a competitor-discovery pass names the direct alternatives from the comparison sources, with citations.

## Notes

- **Depth gate.** This small site needed no extra depth pass: discovery's ranked index made the first source pass already read the in-scope pages. The Legistify failure mode (ranking by URL depth, dropping 950 URLs) did not recur.
- **Decision logging.** In the first segment the orchestrator chose the domain split without logging a decision. The "never ask, always log" rule fixed this from the second segment on, which logged 6.
- **Sonnet as orchestrator.** It followed the stage protocol in every completed session. Its two deviations (issues 4 and 5) are now enforced in `pf.py` or covered by tests, not left to prompt text alone.
