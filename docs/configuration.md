# Configuration

Every knob resolves **CLI flag → `.productforge/config.json` → built-in default**. Put only the
values you want to change in the workspace's `.productforge/config.json`, for example:

```json
{"research.max_sources": 40, "observe.screenshots": "blur"}
```

`pf.py` validates the file (unknown keys and wrong types are errors). `robots.txt` is always
honoured and is deliberately not configurable.

Change a knob from the command line (validated, logged to `history.log` as `config-set`):

```bash
python3.11 pf.py config get <key> [--workspace DIR] [--json]
python3.11 pf.py config list [--workspace DIR] [--json]
python3.11 pf.py config set <key> <value> --reason "<why>" [--workspace DIR] [--json]
```

`<value>` is JSON for numbers, booleans, lists and objects (`config set architecture.preferences
'["Next.js"]' --reason "…"`) and plain text for string knobs. Only non-default overrides are stored.

## research

| Key | Default | Meaning |
|---|---|---|
| `research.max_sources` | `80` | Cap on merged sources |
| `research.min_sources_gate` | `15` | DISCOVERY exit requires at least this many sources |
| `research.max_pages_per_domain` | `600` | entries kept per host after ranking |
| `research.request_delay_seconds` | `1.0` | Politeness delay between discover.py requests |
| `research.user_agent` | `"ProductForge/1.0.0 (+https://github.com/Phantom-IN/productforge)"` | User-Agent sent by discover.py |
| `research.min_claims_gate` | `40` | DISCOVERY exit requires at least this many active claims |
| `research.min_scope_depth` | `0.6` | DISCOVERY exit requires this share of in-scope official pages read or excluded |
| `research.max_excluded_share` | `0.25` | Exclusions count toward the scope-depth gate only up to this share of in-scope pages |
| `auto.max_sources_ceiling` | `400` | Autonomous mode raises research.max_sources at most up to this |
| `auto.max_workflows_ceiling` | `40` | Autonomous mode raises model.max_workflows at most up to this |

## model

| Key | Default | Meaning |
|---|---|---|
| `model.max_workflows` | `25` | Workflow reconstruction cap |
| `model.max_unknown_permission_ratio` | `0.2` | Above this share of '?' permission cells, /productforge model runs a gap pass |

## competitors

| Key | Default | Meaning |
|---|---|---|
| `competitors.max` | `5` | Competitor pass cap |
| `competitors.aggregator_names` | `["AlternativeTo", "AlternativeTo.net", "OSSAlt", "G2", "Capterra", "GetApp", "TrustRadius", "SaaSworthy", "Product Hunt", "Slant", "StackShare", "SourceForge", "Software Advice"]` | Comparison, review and directory sites: never offered as competitor candidates |
| `competitors.max_sources` | `10` | Source budget per competitor (warned above it) |
| `competitors.min_researched` | `2` | SCOPE_DEFINED exit requires this many active competitors, or a recorded waiver |
| `scope.headline_categories` | `["homepage", "features", "enterprise", "pricing"]` | Source categories whose cited features count as headline (cut only by reviewed override) |

## scope

| Key | Default | Meaning |
|---|---|---|
| `scope.build_threshold` | `6` | Priority at or above which a feature is built in V1 |
| `scope.defer_threshold` | `-4` | Priority at or above which a feature is deferred (else drop) |
| `scope.weights.core_value` | `3` | Prioritisation weight: Core product value |
| `scope.weights.user_frequency` | `2` | Prioritisation weight: User frequency |
| `scope.weights.dependency_importance` | `3` | Prioritisation weight: Dependency importance (other features need it) |
| `scope.weights.differentiation` | `2` | Prioritisation weight: Differentiation / table-stakes |
| `scope.weights.engineering_complexity` | `2` | Prioritisation weight: Engineering complexity (subtracted) |
| `scope.weights.infrastructure_complexity` | `1` | Prioritisation weight: Infrastructure complexity (subtracted) |
| `scope.weights.security_impact` | `1` | Prioritisation weight: Security impact — risk if done poorly (subtracted) |
| `scope.weights.operational_cost` | `1` | Prioritisation weight: Operational cost (subtracted) |
| `scope.weights.time_to_implement` | `2` | Prioritisation weight: Time to implement (subtracted) |

## architecture

| Key | Default | Meaning |
|---|---|---|
| `architecture.preferences` | `[]` | Stack preferences for /productforge architect (--stack) |
| `architecture.deployment_target` | `"docker"` | Deployment target: docker, serverless or k8s |
| `architecture.toolchain_concerns` | `["runtime", "language", "framework", "data access", "migrations", "tests", "lint", "package manager", "ci"]` | Concerns G-AR-TOOLCHAIN requires in ## Toolchain (a pinned, verified version each) |

## quality

| Key | Default | Meaning |
|---|---|---|
| `quality.undecided_phrases` | `["TBD", "to be decided", "to be chosen", "not yet chosen", "not chosen", "open spec gap", "ask the user to choose", "choose later", "vendor is open", "library choice"]` | UNDECIDED_CHOICE: phrases (whole, case-insensitive) that leave a build choice open |
| `quality.regulatory_terms` | `["law", "act", "rule", "regulation", "statut", "tax", "compliance", "filing", "deadline"]` | DEFAULT_RULE_UNSOURCED: words marking a regulatory accepted default (needs a number) |

## observe

| Key | Default | Meaning |
|---|---|---|
| `observe.port` | `0` | Observe mode: control-panel port on 127.0.0.1 (0 = any free port) |
| `observe.screenshots` | `"on"` | Observe mode screenshots: on, blur or off |
| `observe.allowed_hosts` | `[]` | Observe mode: hosts to record ([] = the target's host) |
| `observe.max_session_minutes` | `60` | Observe mode: a session stops after this long |
| `observe.retain_days` | `30` | Observe mode: raw sessions older than this are deleted on observe start (0 = keep) |

## quotes

| Key | Default | Meaning |
|---|---|---|
| `quotes.max_words` | `25` | Maximum verbatim quote length from any source |

## phases

| Key | Default | Meaning |
|---|---|---|
| `phases.max_tasks` | `15` | Phase lint: one-session size heuristic (max tasks per phase) |
| `phases.min_acceptance` | `3` | Phase lint: minimum acceptance criteria per phase |

## agents

| Key | Default | Meaning |
|---|---|---|
| `finalize.review_rounds` | `2` | Finalize: consistency-review rounds (references/plan-review.md) while it stages fixes |
| `agents.max_repair_loops` | `2` | Validator → agent repair iterations per run |
| `agents.max_pending_runs` | `4` | pf.py brief refuses new runs while this many are unmerged |
| `agents.max_input_kb` | `400` | pf.py brief adds an INPUT_LARGE warning when the inputs exceed this many KB |

## features

| Key | Default | Meaning |
|---|---|---|
| `features.max_parallel_domains` | `4` | Parallel product-analyst feature passes (one per domain) |

## auto

Used by `pf.py auto` (autonomous driver; see README "Autonomous mode").

| Key | Default | Meaning |
|---|---|---|
| `auto.main_model` | `"opus"` | Autonomous driver: model of the orchestrator session |
| `auto.subagent_model` | `"sonnet"` | Autonomous driver: model of every role agent (CLAUDE_CODE_SUBAGENT_MODEL) |
| `auto.permission_args` | `["--dangerously-skip-permissions"]` | Autonomous driver: permission arguments for each headless claude session (named in the consent text; set a stricter mode here) |
| `auto.max_sessions` | `40` | Autonomous driver: hard stop on the number of claude sessions |
| `auto.max_stalls` | `2` | Autonomous driver: consecutive sessions with an unchanged fingerprint before it stops |
| `auto.retry_wait_seconds` | `900` | Autonomous driver: wait after a failed session (usage limit, network) |
| `auto.max_retries` | `24` | Autonomous driver: failed sessions tolerated before it stops |
| `auto.parallel_runs` | `6` | Autonomous driver: agents.max_pending_runs and features.max_parallel_domains for a run |

## capabilities

| Key | Default | Meaning |
|---|---|---|
| `capabilities.pins` | `{}` | Pinned provider per capability, e.g. {'research.deep': 'builtin'} |
| `capabilities.claude_bin` | `"claude"` | Claude Code CLI used for plugin detection and installs |
| `capabilities.install_scope` | `"project"` | Default scope for consented plugin installs |
