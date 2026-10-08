"""``pf.py deps`` — capability doctor, consented installs and pins (IMPLEMENTATION_PLAN.md §9.4)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from pflib import capabilities, config, state, workspace
from pflib.errors import EXIT_CHECK_FAILED, EXIT_OK, CheckFailed, UsageError

INSTALL_SCOPES = ("project", "user", "local")


def _state_or_none(ws: Path | None) -> state.WorkspaceState | None:
    return state.load(ws) if ws is not None else None


def check(ws: Path | None, available: set[str], home: Path | None = None) -> dict[str, Any]:
    """Detect providers, resolve one per capability, record the result in state.json."""
    home = home or Path.home()
    reg = capabilities.load_registry()
    claude_bin = str(config.resolve("capabilities.claude_bin", ws))
    pins: dict[str, str] = config.resolve("capabilities.pins", ws)
    detections = capabilities.detect(
        reg, available, home, ws or Path.cwd(), capabilities.claude_plugin_list(claude_bin)
    )
    resolved = capabilities.resolve(reg, detections, pins)
    st = _state_or_none(ws)
    offered: list[str] = list((st.capabilities.get("offered") if st else None) or [])
    if ws is not None and st is not None:
        now = workspace.iso(workspace.utc_now())
        st.capabilities["resolved"] = {
            cap: {"provider": res.provider, "version": res.version, "resolved_at": now}
            for cap, res in resolved.items()
        }
        st.capabilities.setdefault("offered", offered)
        state.save(ws, st)
    return {
        "workspace": str(ws) if ws else None,
        "capabilities": {cap: res.to_dict() for cap, res in resolved.items()},
        "offer": capabilities.offers(reg, resolved, pins, offered),
    }


def install(
    ws: Path | None,
    target: str,
    scope: str | None,
    confirmed: bool,
    ack_third_party: bool,
    home: Path | None = None,
) -> tuple[dict[str, Any], int]:
    """Print (default) or, with ``confirmed``, run the install commands for one provider."""
    home = home or Path.home()
    reg = capabilities.load_registry()
    prov = capabilities.install_target(reg, target)
    scope = scope or str(config.resolve("capabilities.install_scope", ws))
    if scope not in INSTALL_SCOPES:
        raise UsageError(f"scope must be one of {INSTALL_SCOPES}", code="CAP_BAD_SCOPE")
    claude_bin = str(config.resolve("capabilities.claude_bin", ws))
    cmds = capabilities.install_commands(reg, prov, scope, claude_bin, home)
    payload: dict[str, Any] = {
        "provider": prov.id,
        "trust": prov.trust,
        "commands": cmds,
        "consent_text": capabilities.consent_text(reg, prov, scope, cmds),
        "executed": False,
        "results": [],
    }
    payload["requires_third_party_ack"] = prov.trust == "third-party"
    if not confirmed:
        payload["message"] = (
            "nothing installed: ask the user with the consent text, then re-run with --confirmed"
        )
        return payload, EXIT_OK
    if prov.trust == "third-party" and not ack_third_party:
        raise CheckFailed(
            f"{prov.id} comes from a third-party source; re-run with --ack-third-party only if "
            "the user explicitly accepted that",
            code="CAP_THIRD_PARTY",
        )
    exit_code = EXIT_OK
    for argv in cmds:
        try:
            proc = subprocess.run(
                argv, cwd=str(ws or Path.cwd()), capture_output=True, text=True, timeout=600,
                check=False,
            )  # fmt: skip
            code, out, err = proc.returncode, proc.stdout, proc.stderr
        except (OSError, subprocess.TimeoutExpired) as exc:
            code, out, err = 127, "", str(exc)
        payload["results"].append(
            {"argv": argv, "exit": code, "stdout": out[-2000:], "stderr": err[-2000:]}
        )
        if code != 0:
            exit_code = EXIT_CHECK_FAILED
            break
    payload["executed"] = True
    payload["message"] = (
        "installed: start a new Claude Code session to load it; this run continues with the "
        "built-in fallback"
        if exit_code == EXIT_OK
        else "install failed; see results"
    )
    if ws is not None:
        workspace.append_history(
            ws,
            {
                "event": "deps-install",
                "provider": prov.id,
                "commands": cmds,
                "exit": payload["results"][-1]["exit"] if payload["results"] else None,
            },
        )
    return payload, exit_code


def use(ws: Path, capability: str, provider: str) -> dict[str, Any]:
    """Pin ``capability`` to ``provider`` (``builtin``/``none`` allowed) in config.json."""
    reg = capabilities.load_registry()
    cap = reg.capability(capability)
    if cap.provider(provider) is None:
        known = ", ".join(p.id for p in cap.providers)
        raise UsageError(f"{provider!r} is not a provider of {capability} ({known})",
                         code="CAP_UNKNOWN")  # fmt: skip
    pins: dict[str, str] = config.resolve("capabilities.pins", ws)
    pins[capability] = provider
    config.write_config(ws, {"capabilities.pins": pins})
    workspace.append_history(
        ws, {"event": "deps-pin", "capability": capability, "provider": provider}
    )
    return {"pins": pins}


def mark_offered(ws: Path, caps: list[str]) -> dict[str, Any]:
    """Remember that installs for ``caps`` were offered, so they are not offered again."""
    reg = capabilities.load_registry()
    for cap in caps:
        reg.capability(cap)
    st = state.load(ws)
    offered = list(st.capabilities.get("offered") or [])
    offered += [c for c in caps if c not in offered]
    st.capabilities["offered"] = offered
    state.save(ws, st)
    return {"offered": offered}
