# Changelog

All notable changes to ProductForge are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Phase 00 scaffold: plugin + marketplace manifests, repository layout (IMPLEMENTATION_PLAN.md §4),
  `productforge` skill stub (`status` only), `pf.py` CLI skeleton with every §8 subcommand stubbed,
  `pflib` (`errors`, `io`), pytest harness, stdlib-only import guard, Makefile, CI.

- Phase 01: record grammar parser/serialiser (`records.py`, byte-identical round trip), ID system
  with provisional IDs and never-reuse high-water marks (`ids.py`, `.productforge/ids.json`), artifact
  catalog with every record schema (`catalog.py`), staging runs + history log (`workspace.py`),
  all-or-nothing staging merge with dedupe/union/ref rewriting (`merge.py`); `pf.py next-id`,
  `staging new`, `merge`; `references/record-format.md`.
- Phase 02: workspace init (`pf.py init`, `pflib/scaffold.py`) and `set-scope`; layered config
  registry (`config.py`, every §5.2 key); lifecycle state machine with one-step transitions, locks
  (append-tolerant snapshots), reopen/stale (`state.py`); declarative gates with not-built
  conditions (`gates.py`); command verdicts (`commands.py`, `pf.py check-command`); `advance`,
  `reopen`; IDEA §6-style `status` (`metrics.py`); `references/stage-gates.md`.
- Phase 03: validator framework (`pflib/validators/`: generic schema/ref/status/identity/quote,
  sources, confidence + conflicts, locks) with 24 declared finding codes; mechanical §11 confidence
  rules with transitive evidence (`confidence.py`); `urls.py`, `taxonomy.py`; tolerant parsing;
  `pf.py validate` / `check`; `G-VALIDATE-CLEAN` gate condition; Tasklet DISCOVERY fixture + one
  invalid overlay per code; `references/confidence-rules.md`, `references/source-tiers.md`.
- Phase 04: full orchestrator `SKILL.md` (dispatch via `check-command`, user-confirmed one-step
  transitions, agent run protocol with preflight + repair loop, inline fallback, end-of-command
  report); `pf.py brief` + `templates/agent-brief.md`; `pf.py merge --check` preflight; merge reports
  list `new_ids`; references `agent-contract.md`, `philosophy.md`, `guardrails.md`; prompt-contract
  tests.
- Phase 05: capability adapters — `capabilities.json` registry (7 capabilities, built-in/none
  fallbacks), `pflib/capabilities.py` (validation, detection via skills dirs / installed plugins /
  `claude plugin list`, resolution, pins), `pflib/deps.py` + `pf.py deps` (doctor, consent-gated
  installs, pins, offered), `pf.py delegate` + 7 adapter files, raw-material section in agent briefs,
  `PROVIDER_REPORT_AS_EVIDENCE` finding, SKILL.md Capabilities and Delegated run protocol sections.
- Phase 06: `pflib/discover.py` (robots-aware reconnaissance: sitemaps incl. gzip/indexes, homepage
  links, subdomain and well-known-path probes, manual on-site redirects, per-host round-robin cap) +
  `discover_rules.py`; `pf.py discover` and `pf.py research-plan` (`research.py`: partitions,
  budgets, coverage, scope advice); `research.max_sources` cap in merge (drops unreferenced new
  sources); `agents/research-agent.md`; research templates; `references/research-playbook.md`;
  SKILL.md research flow with delegation of browse/pdf/repo requests.
- Phase 07: DISCOVERY exit gate (`conditions_discovery.py`: sources, Tier 1, coverage incl.
  unknown-explained categories, overview, surfaces, active claims; conditions load lazily);
  research-agent evidence pass and new `agents/product-analyst.md` (surface pass); ledger/unknowns/
  surfaces templates; `WRONG_REF_TYPE` finding; `research-plan` unmined-source worklist; SKILL.md
  research loop (source → evidence → surface → gate); deterministic fixture generator
  `tests/fixtures/build_tasklet.py` with gate-passing DISCOVERY and DISCOVERY_FAILING snapshots.
- Phase 08: record amendments (`### AMEND <ID>` — Status/Reason/Resolution of open-stage records,
  logged, all-or-nothing refusals) and dedupe passes; generated views (`pflib/render.py`: feature
  hierarchy + matrix, surface → features) re-rendered by every merge, `pf.py render`; prose sections
  (e.g. `## Domains`) merged in record files; `pf.py feature-plan`; feature validators (`BAD_ENUM`,
  `FIELD_NOT_YET_ALLOWED`, `PARENT_DOMAIN_MISMATCH`, `PARENT_CYCLE`, `GENERATED_REGION_EDITED`);
  product-analyst domain split + feature pass; SKILL.md `features`; PRODUCT_MODEL fixture snapshot.
- Phase 09: workflow files (`research/workflows/W-NNN-<slug>.md`) with the step grammar
  `N. [observed|implied-system] <step> — <refs>` (`pflib/workflows.py`); workflow validators
  (`BAD_STEPS`, `BAD_STEP_TAG`, `OBSERVED_STEP_NO_EVIDENCE`, `NO_SYSTEM_STEPS` (warn),
  `WORKFLOW_CONFIDENCE`); `pf.py workflow-candidates`; generated workflow index in
  `research/README.md`; `templates/research/workflow.md`; `agents/ux-analyst.md`; SKILL.md
  `workflows`; merge counts the body of a workflow file that dedupes into an existing workflow as
  ignored prose; 8 Tasklet workflows in the PRODUCT_MODEL fixture.
- Phase 10: reconstructed domain model and permissions — `spec/DOMAIN_MODEL.md` (E) and
  `spec/PERMISSIONS_MATRIX.md` (RL, PR) templates; field grammars for relationships, deletion
  semantics and grants (`pflib/domain.py`); generated relationship tree, identity table and
  permissions matrix; validators (`BAD_RELATIONSHIP`, `RELATIONSHIP_INCONSISTENT` (warn),
  `BAD_DELETION_SEMANTICS`, `BAD_GRANT`, `PERMISSION_CELL_MISSING`, `UNKNOWN_CELL_NO_U`,
  `LIMITED_WITHOUT_MEANS`, `ENTITY_WITHOUT_PERMISSIONS`, `DUPLICATE_PERMISSION_RULE`; self-supersede
  flagged); `agents/domain-architect.md` (no network); SKILL.md `model` (part 1) and a general
  research-request protocol; merge seeds a new canonical file from its template; `pf.py status`
  reports permission rules and unknown cells; Tasklet domain model fixture (11 entities, 4 roles,
  13 rules).
- Phase 11: integrations (`spec/INTEGRATIONS.md`, I) and architecture inference
  (`research/architecture-inference.md`, A) templates with generated summary, requirement-area and
  workflow-coverage views; no-architecture-hallucination validators (`TARGET_IMPL_UNSUPPORTED`,
  `REQUIREMENT_NOT_MEASURABLE` (warn), `TECH_ASSERTION_IN_OBSERVATION` (warn), `pflib/tech_terms.py`);
  reserved fields per record type (A `Proposed implementation`); the PRODUCT_MODEL gate
  (`pflib/conditions_product_model.py`, all seven `G-PM-*` conditions); product-analyst integration
  pass; `agents/systems-architect.md` (inference pass); SKILL.md `model` with skip-if-done passes;
  `references/product-model-playbook.md`; gate-passing PRODUCT_MODEL fixture (6 integrations, 15
  inferences) and `PRODUCT_MODEL_FAILING`.
- Phase 12: optional competitive research — `research/COMPETITORS.md` template with generated
  landscape, signals-by-feature and missing-in-target views; `pf.py competitor-candidates`
  (evidence-derived names, user confirms); table stakes counted by scripts from competitor offers
  (`competitors.offers`, `metrics.table_stakes`), FS signals for judgment calls; validators
  (`BAD_FEATURE_SIGNAL`, `TABLE_STAKES_UNDERSUPPORTED`, `COMPLAINT_SOURCE_TIER`,
  `COMPETITOR_SOURCE_AS_EVIDENCE`); product-analyst competitor pass; SKILL.md `competitors`; three
  synthetic competitors in the Tasklet fixture; `competitors.max_sources` budget
  (`COMPETITOR_OVER_BUDGET`, warn).
- Phase 13: scope reduction — `pflib/score.py` (weighted priority, ordered decision rules with a
  dependency floor, table-stakes bonus; calibrated thresholds `scope.build_threshold` 6 /
  `scope.defer_threshold` −4); `pf.py score [--write]` and `pf.py override` (user decisions as
  logged score-card amendments; `records.AMENDABLE_EXTRA`); `spec/PARITY_MATRIX.md` and
  `spec/PRODUCT_SPEC.md` templates with generated parity matrix, overrides, reduction funnel and
  accepted defaults; feature-matrix MVP/Decision/Score columns generated from score cards;
  `metrics.funnel`; scope validators (`BAD_SCORE`, `OVERRIDE_NO_REASON`, `SIMPLIFICATION_MISSING`,
  `EXTERNAL_SERVICE_MISSING`, `FEATURE_UNSCORED`, `DUPLICATE_SCORE`, `FEATURE_WITHOUT_REQUIREMENT`);
  the SCOPE_DEFINED gate (all seven `G-SC-*`); `agents/scope-editor.md`;
  `references/prioritisation-model.md`; stage procedures moved out of SKILL.md into
  `references/commands-product-model.md` and `references/commands-scope.md`; SCOPE_DEFINED and
  SCOPE_DEFINED_FAILING fixtures.
- Phase 14: architecture design — `spec/ARCHITECTURE.md` and `spec/adr.md` templates (generated
  decisions and requirement-coverage views), AP proposals in `## Proposals`, `pflib/architecture.py`
  (stack, components, coverage, topics), `pflib/repotree.py`; validators (`ADR_NO_ALTERNATIVES`,
  `INVARIANT_UNENFORCED`, `ARCHITECTURE_DISCLAIMER_MISSING`, `STACK_INCOMPLETE`, `BAD_REPO_TREE`,
  `UNJUSTIFIED_COMPONENT` (warn), `REQUIREMENT_UNADDRESSED`, `INFERENCE_UNPROPOSED`,
  `ADR_TOPIC_MISSING`, `SUPERSEDED_DECISION_CITED` (warn)); the ARCHITECTURE_LOCKED gate;
  `pf.py set-preferences` (`architecture.preferences`, `architecture.deployment_target`); AP
  proposals amendable; systems-architect design pass; `references/architecture-playbook.md`,
  `references/commands-architecture.md`; ARCHITECTURE_LOCKED fixtures (11 ADRs, 7 invariants).

### Fixed
- Briefing more runs than `agents.max_pending_runs` is refused (`RUN_LIMIT`); `pf.py staging list` /
  `staging discard`; orchestrator resumes leftover runs first; per-domain feature budget.
- `NEAR_DUPLICATE_TITLE` no longer compares superseded/rejected records.
- `agents/README.md` was registered by Claude Code as a bogus `productforge:README` agent; moved to
  `docs/agents.md`.

### Changed
- `ruff format` is enforced by `make lint`.
- Python floor raised to **3.11**: the plugin, Makefile and docs invoke `python3.11`; `pf.py` refuses
  older interpreters with a clear message; CI runs 3.11 + 3.12.
