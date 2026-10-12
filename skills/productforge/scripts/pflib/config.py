"""Configuration registry (IMPLEMENTATION_PLAN.md §5.2).

Every knob resolves **CLI flag → ``.productforge/config.json`` → coded default**. New knobs
are added to ``DEFAULTS`` (with a description) and to the §5.2 table — never hardcoded at
the call site. ``config.json`` stores only non-default overrides.

``research.respect_robots`` deliberately does not exist: robots.txt is always honoured (§18).
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


# Prioritisation weights (§14.1). "External service availability" has no weight: it
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
    "research.max_pages_per_domain": _k(40, "discover.py crawl cap per host"),
    "research.request_delay_seconds": _k(1.0, "Politeness delay between discover.py requests"),
    "research.user_agent": _k(
        f"ProductForge/{__version__} (+https://github.com/Phantom-IN/productforge)",
        "User-Agent sent by discover.py",
    ),
    "research.min_claims_gate": _k(40, "DISCOVERY exit requires at least this many active claims"),
    "model.max_workflows": _k(25, "Workflow reconstruction cap"),
    "competitors.max": _k(5, "Competitor pass cap"),
    "competitors.max_sources": _k(10, "Source budget per competitor (warned above it)"),
    "quotes.max_words": _k(25, "Maximum verbatim quote length from any source"),
    **{
        f"scope.weights.{name}": _k(weight, f"Prioritisation weight: {label}")
        for name, (weight, label) in _WEIGHTS.items()
    },
    "phases.max_tasks": _k(15, "Phase lint: one-session size heuristic (max tasks per phase)"),
    "phases.min_acceptance": _k(3, "Phase lint: minimum acceptance criteria per phase"),
    "agents.max_repair_loops": _k(2, "Validator → agent repair iterations per run"),
    "agents.max_pending_runs": _k(4, "pf.py brief refuses new runs while this many are unmerged"),
    "features.max_parallel_domains": _k(
        4, "Parallel product-analyst feature passes (one per domain)"
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


def describe() -> list[dict[str, Any]]:
    return [
        {"key": k, "default": v.default, "type": v.type.__name__, "description": v.description}
        for k, v in DEFAULTS.items()
    ]
