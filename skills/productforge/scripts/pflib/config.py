"""Configuration registry.

Every knob resolves **CLI flag → ``.productforge/config.json`` → coded default**. New knobs
are added to ``DEFAULTS`` (with a description) and to ``docs/configuration.md`` — never hardcoded at
the call site. ``config.json`` stores only non-default overrides.

``research.respect_robots`` deliberately does not exist: robots.txt is always honoured.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pflib import __version__
from pflib.errors import CheckFailed, UsageError
from pflib.io import atomic_write_text

CONFIG_FILE = "config.json"


@dataclass(frozen=True)
class ConfigKey:
    default: Any
    type: type
    description: str


def _k(default: Any, description: str, typ: type | None = None) -> ConfigKey:
    return ConfigKey(default, typ or type(default), description)


# Prioritisation weights. "External service availability" has no weight: it
# modifies the decision, not the score.
_WEIGHTS = {
    "core_value": (3, "Core product value"),
    "user_frequency": (2, "User frequency"),
    "dependency_importance": (3, "Dependency importance (other features need it)"),
    "differentiation": (2, "Differentiation / table-stakes"),
    "engineering_complexity": (2, "Engineering complexity (subtracted)"),
    "infrastructure_complexity": (1, "Infrastructure complexity (subtracted)"),
    "security_impact": (1, "Security impact — risk if done poorly (subtracted)"),
    "operational_cost": (1, "Operational cost (subtracted)"),
    "time_to_implement": (2, "Time to implement (subtracted)"),
}

DEFAULTS: dict[str, ConfigKey] = {
    "research.max_sources": _k(80, "Cap on merged sources"),
    "research.min_sources_gate": _k(15, "DISCOVERY exit requires at least this many sources"),
    "research.max_pages_per_domain": _k(600, "entries kept per host after ranking"),
    "research.request_delay_seconds": _k(1.0, "Politeness delay between discover.py requests"),
    "research.user_agent": _k(
        f"ProductForge/{__version__} (+https://github.com/Phantom-IN/productforge)",
        "User-Agent sent by discover.py",
    ),
    "research.min_claims_gate": _k(40, "DISCOVERY exit requires at least this many active claims"),
    "research.min_scope_depth": _k(
        0.6, "DISCOVERY exit requires this share of in-scope official pages read or excluded"
    ),
    "research.max_excluded_share": _k(
        0.25,
        "Exclusions count toward the scope-depth gate only up to this share of in-scope pages",
    ),
    "auto.max_sources_ceiling": _k(
        400, "Autonomous mode raises research.max_sources at most up to this"
    ),
    "auto.max_workflows_ceiling": _k(
        40, "Autonomous mode raises model.max_workflows at most up to this"
    ),
    "model.max_workflows": _k(25, "Workflow reconstruction cap"),
    "competitors.max": _k(5, "Competitor pass cap"),
    "competitors.aggregator_names": _k(
        [
            "AlternativeTo",
            "AlternativeTo.net",
            "OSSAlt",
            "G2",
            "Capterra",
            "GetApp",
            "TrustRadius",
            "SaaSworthy",
            "Product Hunt",
            "Slant",
            "StackShare",
            "SourceForge",
            "Software Advice",
        ],
        "Comparison, review and directory sites: never offered as competitor candidates",
    ),
    "model.max_unknown_permission_ratio": _k(
        0.2, "Above this share of '?' permission cells, /productforge model runs a gap pass"
    ),
    "competitors.min_researched": _k(
        2, "SCOPE_DEFINED exit requires this many active competitors, or a recorded waiver"
    ),
    "scope.headline_categories": _k(
        ["homepage", "features", "enterprise", "pricing"],
        "Source categories whose cited features count as headline (cut only by reviewed override)",
    ),
    "competitors.max_sources": _k(10, "Source budget per competitor (warned above it)"),
    "scope.build_threshold": _k(6, "Priority at or above which a feature is built in V1"),
    "scope.defer_threshold": _k(-4, "Priority at or above which a feature is deferred (else drop)"),
    "architecture.preferences": _k([], "Stack preferences for /productforge architect (--stack)"),
    "architecture.deployment_target": _k("docker", "Deployment target: docker, serverless or k8s"),
    "architecture.toolchain_concerns": _k(
        [
            "runtime",
            "language",
            "framework",
            "data access",
            "migrations",
            "tests",
            "lint",
            "package manager",
            "ci",
        ],
        "Concerns G-AR-TOOLCHAIN requires in ## Toolchain (a pinned, verified version each)",
    ),
    "quality.undecided_phrases": _k(
        [
            "TBD",
            "to be decided",
            "to be chosen",
            "not yet chosen",
            "not chosen",
            "open spec gap",
            "ask the user to choose",
            "choose later",
            "vendor is open",
            "library choice",
        ],
        "UNDECIDED_CHOICE: phrases (whole, case-insensitive) that leave a build choice open",
    ),
    "quality.regulatory_terms": _k(
        ["law", "act", "rule", "regulation", "statut", "tax", "compliance", "filing", "deadline"],
        "DEFAULT_RULE_UNSOURCED: words marking a regulatory accepted default (needs a number)",
    ),
    "observe.port": _k(0, "Observe mode: control-panel port on 127.0.0.1 (0 = any free port)"),
    "observe.screenshots": _k("on", "Observe mode screenshots: on, blur or off"),
    "observe.allowed_hosts": _k([], "Observe mode: hosts to record ([] = the target's host)"),
    "observe.max_session_minutes": _k(60, "Observe mode: a session stops after this long"),
    "observe.retain_days": _k(
        30, "Observe mode: raw sessions older than this are deleted on observe start (0 = keep)"
    ),
    "quotes.max_words": _k(25, "Maximum verbatim quote length from any source"),
    **{
        f"scope.weights.{name}": _k(weight, f"Prioritisation weight: {label}")
        for name, (weight, label) in _WEIGHTS.items()
    },
    "phases.max_tasks": _k(15, "Phase lint: one-session size heuristic (max tasks per phase)"),
    "phases.min_acceptance": _k(3, "Phase lint: minimum acceptance criteria per phase"),
    "finalize.review_rounds": _k(
        2, "Finalize: consistency-review rounds (references/plan-review.md) while it stages fixes"
    ),
    "agents.max_repair_loops": _k(2, "Validator → agent repair iterations per run"),
    "agents.max_pending_runs": _k(4, "pf.py brief refuses new runs while this many are unmerged"),
    "agents.max_input_kb": _k(
        400, "pf.py brief adds an INPUT_LARGE warning when the inputs exceed this many KB"
    ),
    "features.max_parallel_domains": _k(
        4, "Parallel product-analyst feature passes (one per domain)"
    ),
    "auto.main_model": _k("opus", "Autonomous driver: model of the orchestrator session"),
    "auto.subagent_model": _k(
        "sonnet", "Autonomous driver: model of every role agent (CLAUDE_CODE_SUBAGENT_MODEL)"
    ),
    "auto.permission_args": _k(
        ["--dangerously-skip-permissions"],
        "Autonomous driver: permission arguments for each headless claude session",
    ),
    "auto.max_sessions": _k(40, "Autonomous driver: hard stop on the number of claude sessions"),
    "auto.max_stalls": _k(
        2, "Autonomous driver: consecutive sessions with an unchanged fingerprint before it stops"
    ),
    "auto.retry_wait_seconds": _k(
        900, "Autonomous driver: wait after a failed session (usage limit, network)"
    ),
    "auto.max_retries": _k(24, "Autonomous driver: failed sessions tolerated before it stops"),
    "auto.parallel_runs": _k(
        6, "Autonomous driver: agents.max_pending_runs and features.max_parallel_domains for a run"
    ),
    "capabilities.pins": _k(
        {}, "Pinned provider per capability, e.g. {'research.deep': 'builtin'}"
    ),
    "capabilities.claude_bin": _k(
        "claude", "Claude Code CLI used for plugin detection and installs"
    ),
    "capabilities.install_scope": _k("project", "Default scope for consented plugin installs"),
}


def _check_key(key: str) -> ConfigKey:
    spec = DEFAULTS.get(key)
    if spec is None:
        raise UsageError(f"unknown config key {key!r}", code="UNKNOWN_CONFIG_KEY")
    return spec


def coerce(key: str, value: Any) -> Any:
    """Validate ``value`` against the key's type (ints are accepted for floats)."""
    spec = _check_key(key)
    if spec.type is float and isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    if spec.type is int and isinstance(value, bool):
        ok = False
    else:
        ok = isinstance(value, spec.type)
    if not ok:
        raise CheckFailed(
            f"config {key} must be {spec.type.__name__}, got {type(value).__name__}",
            code="BAD_CONFIG_VALUE",
        )
    return value


def _config_path(ws: Path) -> Path:
    from pflib.workspace import pf_dir  # local import: workspace imports config

    return pf_dir(ws) / CONFIG_FILE


def load_overrides(ws: Path | None) -> dict[str, Any]:
    if ws is None:
        return {}
    path = _config_path(ws)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CheckFailed(f"{path} is not valid JSON: {exc}", code="BAD_CONFIG_FILE") from exc
    if not isinstance(data, dict):
        raise CheckFailed(f"{path} must contain a JSON object", code="BAD_CONFIG_FILE")
    return {key: coerce(key, value) for key, value in data.items()}


def resolve(key: str, ws: Path | None = None, cli_overrides: dict[str, Any] | None = None) -> Any:
    """CLI override → workspace config.json → coded default."""
    spec = _check_key(key)
    if cli_overrides and key in cli_overrides and cli_overrides[key] is not None:
        return coerce(key, cli_overrides[key])
    overrides = load_overrides(ws)
    if key in overrides:
        return copy.deepcopy(overrides[key])
    return copy.deepcopy(spec.default)


def write_config(ws: Path, values: dict[str, Any]) -> dict[str, Any]:
    """Merge ``values`` into config.json, keeping only non-default overrides."""
    current = load_overrides(ws)
    for key, value in values.items():
        current[key] = coerce(key, value)
    stored = {k: v for k, v in sorted(current.items()) if v != DEFAULTS[k].default}
    atomic_write_text(_config_path(ws), json.dumps(stored, indent=2) + "\n")
    return stored


def parse_value(key: str, raw: str) -> Any:
    """Parse a command-line text into the key's type: JSON for non-strings, text for strings."""
    spec = _check_key(key)
    if spec.type is str:
        # Accept a JSON-quoted string too ('"sonnet"'), so it never stores its own quotes.
        if len(raw) >= 2 and raw[0] == raw[-1] == '"':
            try:
                decoded = json.loads(raw)
            except json.JSONDecodeError:
                return raw
            return decoded if isinstance(decoded, str) else raw
        return raw
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UsageError(
            f"config {key} needs a JSON {spec.type.__name__} value, got {raw!r}",
            code="BAD_CONFIG_VALUE",
        ) from exc
    return coerce(key, value)


def set_value(ws: Path, key: str, raw: str, reason: str) -> dict[str, Any]:
    """Validate and store one override; log a ``config-set`` history event."""
    from pflib.workspace import append_history  # local import: workspace imports config

    if not reason.strip():
        raise UsageError("config set needs --reason", code="USAGE_ERROR")
    value = parse_value(key, raw)
    old = resolve(key, ws)
    write_config(ws, {key: value})
    new = resolve(key, ws)
    append_history(
        ws, {"event": "config-set", "key": key, "old": old, "new": new, "reason": reason.strip()}
    )
    return {"key": key, "old": old, "new": new, "reason": reason.strip()}


def describe() -> list[dict[str, Any]]:
    return [
        {"key": k, "default": v.default, "type": v.type.__name__, "description": v.description}
        for k, v in DEFAULTS.items()
    ]
