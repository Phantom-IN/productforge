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

### Changed
- `ruff format` is enforced by `make lint`.
- Python floor raised to **3.11**: the plugin, Makefile and docs invoke `python3.11`; `pf.py` refuses
  older interpreters with a clear message; CI runs 3.11 + 3.12.
