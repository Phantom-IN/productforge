# Configuration

Every knob resolves **CLI flag → `.productforge/config.json` → built-in default**. Put only the
values you want to change in the workspace's `.productforge/config.json`, for example:

```json
{"research.max_sources": 40, "observe.screenshots": "blur"}
```

`pf.py` validates the file (unknown keys and wrong types are errors). `robots.txt` is always
honoured and is deliberately not configurable.

## research

| Key | Default | Meaning |
|---|---|---|
| `research.max_sources` | `80` | Cap on merged sources |
| `research.min_sources_gate` | `15` | DISCOVERY exit requires at least this many sources |
| `research.max_pages_per_domain` | `40` | discover.py crawl cap per host |
| `research.request_delay_seconds` | `1.0` | Politeness delay between discover.py requests |
| `research.user_agent` | `"ProductForge/1.0.0 (+https://github.com/Phantom-IN/productforge)"` | User-Agent sent by discover.py |
| `research.min_claims_gate` | `40` | DISCOVERY exit requires at least this many active claims |

## model

| Key | Default | Meaning |
|---|---|---|
| `model.max_workflows` | `25` | Workflow reconstruction cap |
| `model.max_unknown_permission_ratio` | `0.2` | Above this share of '?' permission cells, /productforge model runs a gap pass |

## competitors

| Key | Default | Meaning |
|---|---|---|
| `competitors.max` | `5` | Competitor pass cap |
| `competitors.max_sources` | `10` | Source budget per competitor (warned above it) |

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
| `agents.max_repair_loops` | `2` | Validator → agent repair iterations per run |
| `agents.max_pending_runs` | `4` | pf.py brief refuses new runs while this many are unmerged |

## features

| Key | Default | Meaning |
|---|---|---|
| `features.max_parallel_domains` | `4` | Parallel product-analyst feature passes (one per domain) |

## capabilities

| Key | Default | Meaning |
|---|---|---|
| `capabilities.pins` | `{}` | Pinned provider per capability, e.g. {'research.deep': 'builtin'} |
| `capabilities.claude_bin` | `"claude"` | Claude Code CLI used for plugin detection and installs |
| `capabilities.install_scope` | `"project"` | Default scope for consented plugin installs |
