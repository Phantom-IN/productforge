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

### Fixed
- `agents/README.md` was registered by Claude Code as a bogus `productforge:README` agent; moved to
  `docs/agents.md`.

### Changed
- `ruff format` is enforced by `make lint`.
- Python floor raised to **3.11**: the plugin, Makefile and docs invoke `python3.11`; `pf.py` refuses
  older interpreters with a clear message; CI runs 3.11 + 3.12.
