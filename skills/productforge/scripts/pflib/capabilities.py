"""Capability adapters — reuse existing skills and plugins (IMPLEMENTATION_PLAN.md §9.4).

``capabilities.json`` maps each generic capability (deep research, browsing, PDFs, repo
analysis, …) to an ordered list of providers. The last provider of a *required* capability is
always ``builtin`` and of an *optional* one ``none``, so ProductForge works with zero extra
installs. This module validates the registry, detects which providers are available on this
machine, resolves one provider per capability, and builds (never silently runs) install
commands.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pflib.errors import CheckFailed, UsageError

SKILL_DIR = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = SKILL_DIR / "capabilities.json"
ADAPTERS_DIR = SKILL_DIR / "adapters"

KINDS = frozenset({"skill", "agent", "tool", "builtin", "none"})
FALLBACK_KINDS = frozenset({"builtin", "none"})
TRUSTS = frozenset({"first-party", "phantom-in", "third-party"})
DETECT_KEYS = frozenset({"host", "plugin", "skill"})


@dataclass(frozen=True)
class Provider:
    id: str
    kind: str
    invoke: str | None
    detect: dict[str, Any] | None
    install: dict[str, str] | None
    trust: str
    adapter: str | None

    @property
    def is_fallback(self) -> bool:
        return self.kind in FALLBACK_KINDS


@dataclass(frozen=True)
class Capability:
    id: str
    description: str
    required: bool
    used_in: tuple[str, ...]
    providers: tuple[Provider, ...]

    def provider(self, provider_id: str) -> Provider | None:
        return next((p for p in self.providers if p.id == provider_id), None)


@dataclass(frozen=True)
class Registry:
    version: int
    marketplaces: dict[str, dict[str, str]]
    capabilities: dict[str, Capability]

    def capability(self, cap_id: str) -> Capability:
        cap = self.capabilities.get(cap_id)
        if cap is None:
            known = ", ".join(self.capabilities)
            raise UsageError(f"unknown capability {cap_id!r} (known: {known})", code="CAP_UNKNOWN")
        return cap

    def provider(self, provider_id: str) -> Provider:
        for cap in self.capabilities.values():
            found = cap.provider(provider_id)
            if found is not None and not found.is_fallback:
                return found
        raise UsageError(f"unknown provider {provider_id!r}", code="CAP_UNKNOWN")


def _schema_error(message: str, code: str = "CAP_SCHEMA") -> CheckFailed:
    return CheckFailed(f"capabilities.json: {message}", code=code)


def load_registry(path: Path = REGISTRY_PATH, adapters_dir: Path = ADAPTERS_DIR) -> Registry:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _schema_error(f"cannot be read: {exc}") from exc
    if data.get("version") != 1:
        raise _schema_error("version must be 1")
    marketplaces = data.get("marketplaces", {})
    for name, market in marketplaces.items():
        if not market.get("source") or market.get("trust") not in TRUSTS:
            raise _schema_error(f"marketplace {name} needs a source and a valid trust")
    caps: dict[str, Capability] = {}
    for cap_id, raw in data.get("capabilities", {}).items():
        providers = []
        for p in raw.get("providers", []):
            prov = Provider(
                id=p["id"],
                kind=p["kind"],
                invoke=p.get("invoke"),
                detect=p.get("detect"),
                install=p.get("install"),
                trust=p.get("trust", ""),
                adapter=p.get("adapter"),
            )
            if prov.kind not in KINDS:
                raise _schema_error(f"{cap_id}/{prov.id}: unknown kind {prov.kind!r}")
            if prov.trust not in TRUSTS:
                raise _schema_error(f"{cap_id}/{prov.id}: unknown trust {prov.trust!r}")
            if prov.is_fallback:
                if prov.detect or prov.install or prov.adapter:
                    raise _schema_error(
                        f"{cap_id}/{prov.id}: fallbacks take no detect/install/adapter"
                    )
            else:
                if not prov.detect or len(prov.detect) != 1 or set(prov.detect) - DETECT_KEYS:
                    raise _schema_error(
                        f"{cap_id}/{prov.id}: detect needs one of {sorted(DETECT_KEYS)}"
                    )
                if not prov.adapter or not (adapters_dir / prov.adapter).is_file():
                    raise _schema_error(
                        f"{cap_id}/{prov.id}: adapter file {prov.adapter!r} missing"
                    )
            if prov.install is not None:
                market = prov.install.get("marketplace", "")
                if market not in marketplaces or not prov.install.get("plugin"):
                    raise _schema_error(
                        f"{cap_id}/{prov.id}: install marketplace {market!r} is not declared",
                        code="CAP_UNKNOWN_MARKETPLACE",
                    )
            providers.append(prov)
        required = bool(raw.get("required", True))
        expected = "builtin" if required else "none"
        if not providers or providers[-1].kind != expected:
            raise _schema_error(
                f"{cap_id}: the last provider must be '{expected}' "
                f"({'required' if required else 'optional'} capability)",
                code="CAP_NO_FALLBACK",
            )
        if any(p.is_fallback for p in providers[:-1]):
            raise _schema_error(f"{cap_id}: only the last provider may be a fallback")
        caps[cap_id] = Capability(
            cap_id, raw.get("description", ""), required, tuple(raw.get("used_in", [])),
            tuple(providers),
        )  # fmt: skip
    return Registry(1, marketplaces, caps)


# --------------------------------------------------------------------------- detection


@dataclass(frozen=True)
class Detection:
    installed: bool
    version: str | None = None
    location: str | None = None
    source: str = ""


def claude_plugin_list(claude_bin: str) -> list[dict[str, Any]] | None:
    """``claude plugin list --json`` (local, no network); None if unavailable or failing."""
    if shutil.which(claude_bin) is None:
        return None
    try:
        proc = subprocess.run(
            [claude_bin, "plugin", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        data = json.loads(proc.stdout) if proc.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    return data if isinstance(data, list) else None


def _short(name: str) -> str:
    return name.split(":", 1)[-1].strip().lower()


def detect(
    reg: Registry,
    host_available: set[str],
    home: Path,
    project: Path | None = None,
    plugin_list: list[dict[str, Any]] | None = None,
) -> dict[str, Detection]:
    """Which non-fallback providers are available. Fallbacks are always available."""
    host = {h.strip() for h in host_available if h.strip()}
    host_short = {_short(h) for h in host}
    installed_file = home / ".claude" / "plugins" / "installed_plugins.json"
    installed: dict[str, Any] = {}
    if installed_file.is_file():
        try:
            installed = json.loads(installed_file.read_text(encoding="utf-8")).get("plugins", {})
        except (OSError, json.JSONDecodeError, AttributeError):
            installed = {}
    cli = {entry.get("id"): entry for entry in plugin_list or [] if isinstance(entry, dict)}
    skill_dirs = [home / ".claude" / "skills"] + (
        [project / ".claude" / "skills"] if project else []
    )

    out: dict[str, Detection] = {}
    for cap in reg.capabilities.values():
        for prov in cap.providers:
            if prov.is_fallback:
                out[prov.id] = Detection(True, source="builtin")
                continue
            assert prov.detect is not None
            if "host" in prov.detect:
                ok = prov.id in host or _short(prov.id) in host_short
                out[prov.id] = Detection(ok, source="host" if ok else "")
            elif "plugin" in prov.detect:
                pid = prov.detect["plugin"]
                if pid in cli:
                    entry = cli[pid]
                    out[prov.id] = Detection(
                        bool(entry.get("enabled", True)), entry.get("version"),
                        entry.get("installPath"), "claude plugin list",
                    )  # fmt: skip
                elif installed.get(pid):
                    entry = installed[pid][0]
                    out[prov.id] = Detection(
                        True,
                        entry.get("version"),
                        entry.get("installPath"),
                        "installed_plugins.json",
                    )
                else:
                    out[prov.id] = Detection(False)
            else:
                name = prov.detect["skill"]
                found = next(
                    (d / name for d in skill_dirs if (d / name / "SKILL.md").is_file()), None
                )
                if found is not None:
                    out[prov.id] = Detection(True, location=str(found), source="skills dir")
                else:
                    ok = name in host or _short(name) in host_short
                    out[prov.id] = Detection(ok, source="host" if ok else "")
    return out


# --------------------------------------------------------------------------- resolution


@dataclass
class Resolution:
    capability: str
    provider: str
    kind: str
    invoke: str | None
    adapter: str | None
    version: str | None
    pinned: bool
    required: bool
    installable: list[str] = field(default_factory=list)
    available: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "kind": self.kind,
            "invoke": self.invoke,
            "adapter": self.adapter,
            "version": self.version,
            "pinned": self.pinned,
            "required": self.required,
            "installable": self.installable,
            "available": self.available,
            "note": self.note,
        }


def resolve(
    reg: Registry, detections: dict[str, Detection], pins: dict[str, str] | None = None
) -> dict[str, Resolution]:
    pins = pins or {}
    out: dict[str, Resolution] = {}
    for cap in reg.capabilities.values():
        available = [p for p in cap.providers if detections.get(p.id, Detection(False)).installed]
        chosen = available[0]  # the fallback is always available
        pinned, note = False, ""
        pin = pins.get(cap.id)
        if pin:
            pinned_provider = cap.provider(pin)
            if pinned_provider is None:
                note = f"pin {pin!r} is not a provider of {cap.id}; ignored"
            elif pinned_provider in available:
                chosen, pinned = pinned_provider, True
            else:
                note = f"pinned provider {pin} is not available; using {chosen.id}"
        det = detections.get(chosen.id, Detection(True))
        out[cap.id] = Resolution(
            capability=cap.id,
            provider=chosen.id,
            kind=chosen.kind,
            invoke=chosen.invoke,
            adapter=chosen.adapter,
            version=det.version,
            pinned=pinned,
            required=cap.required,
            installable=[p.id for p in cap.providers if p.install and p not in available],
            available=[p.id for p in available],
            note=note,
        )
    return out


def offers(
    reg: Registry, resolved: dict[str, Resolution], pins: dict[str, str], offered: list[str]
) -> list[str]:
    """Capabilities worth offering an install for: running on the fallback, an installable
    alternative exists, not pinned, and not offered before in this workspace."""
    out: list[str] = []
    for cap_id, res in resolved.items():
        current = reg.capability(cap_id).provider(res.provider)
        on_fallback = current is not None and current.is_fallback
        if on_fallback and res.installable and cap_id not in pins and cap_id not in offered:
            out.append(cap_id)
    return out


# --------------------------------------------------------------------------- install


def known_marketplaces(home: Path) -> set[str]:
    path = home / ".claude" / "plugins" / "known_marketplaces.json"
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, TypeError):
        return set()


def install_target(reg: Registry, target: str) -> Provider:
    """A capability id (→ its first installable provider) or a provider id."""
    if target in reg.capabilities:
        cap = reg.capabilities[target]
        prov = next((p for p in cap.providers if p.install), None)
        if prov is None:
            raise UsageError(
                f"{target} has no installable provider (host-provided skills are enabled in "
                f"Claude settings, not installed by ProductForge)",
                code="CAP_NOT_INSTALLABLE",
            )
        return prov
    prov = reg.provider(target)
    if prov.install is None:
        raise UsageError(
            f"{target} is provided by the host or installed manually; "
            "ProductForge cannot install it",
            code="CAP_NOT_INSTALLABLE",
        )
    return prov


def install_commands(
    reg: Registry, prov: Provider, scope: str, claude_bin: str, home: Path
) -> list[list[str]]:
    if prov.install is None:
        raise UsageError(f"{prov.id} is not installable", code="CAP_NOT_INSTALLABLE")
    market = prov.install["marketplace"]
    if market not in reg.marketplaces:
        raise CheckFailed(f"marketplace {market!r} is not trusted by the registry",
                          code="CAP_UNTRUSTED_SOURCE")  # fmt: skip
    cmds: list[list[str]] = []
    if market not in known_marketplaces(home):
        cmds.append(
            [claude_bin, "plugin", "marketplace", "add", reg.marketplaces[market]["source"]]
        )
    cmds.append(
        [claude_bin, "plugin", "install", f"{prov.install['plugin']}@{market}", "--scope", scope]
    )
    return cmds


def consent_text(reg: Registry, prov: Provider, scope: str, cmds: list[list[str]]) -> str:
    assert prov.install is not None
    market = reg.marketplaces[prov.install["marketplace"]]
    run = "; ".join(" ".join(c) for c in cmds)
    return (
        f"Install {prov.install['plugin']}@{prov.install['marketplace']} "
        f"({prov.trust} plugin from {market['source']}, scope: {scope}) to provide "
        f"{prov.id}? This runs: {run}. A new Claude Code session is needed to load it; "
        "this run continues with the built-in fallback."
    )
