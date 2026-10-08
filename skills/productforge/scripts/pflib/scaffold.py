"""Workspace initialisation — ``pf.py init`` (IMPLEMENTATION_PLAN.md §5).

Creates the workspace directory, ``.productforge/{state.json,config.json,history.log}``,
the ``research/``, ``spec/decisions/`` and ``plans/`` folders, and renders any template
whose catalog artifact is owned by DISCOVERY.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from pflib import catalog, config, stages, state, urls, workspace
from pflib.errors import UsageError
from pflib.io import atomic_write_text

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
GITIGNORE = "staging/\ncache/\nmerge.lock\n"


def parse_target(url: str) -> tuple[str, str]:
    """Validate a public product URL; return (normalised URL, host)."""
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise UsageError(
            f"not a public product URL: {url!r} (expected http(s)://host/…)", code="BAD_URL"
        )
    return url.strip(), parts.hostname.lower()


def slug_from_host(host: str) -> str:
    """``linear.app`` → ``linear``; ``www.example.co.uk`` → ``example``."""
    labels = [label for label in host.split(".") if label]
    if labels and labels[0] == "www":
        labels = labels[1:]
    if len(labels) >= 3 and ".".join(labels[-2:]) in urls.MULTI_PART_TLDS:
        core = labels[-3]
    elif len(labels) >= 2:
        core = labels[-2]
    else:
        core = labels[0] if labels else "product"
    return catalog.slugify(core)


def _render(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def discovery_templates() -> list[tuple[Path, str]]:
    """(template path, canonical workspace path) for every DISCOVERY-owned template."""
    out: list[tuple[Path, str]] = []
    if not TEMPLATES_DIR.is_dir():
        return out
    for path in sorted(TEMPLATES_DIR.rglob("*.md")):
        rel = path.relative_to(TEMPLATES_DIR).as_posix()
        target = catalog.TEMPLATE_ALIASES.get(rel, rel)
        spec = catalog.spec_for_path(target)
        if spec is not None and spec.owner_stage == stages.DISCOVERY:
            out.append((path, target))
    return out


def init_workspace(
    url: str,
    out: str | None = None,
    scope: str | None = None,
    name: str | None = None,
    force_adopt: bool = False,
    cwd: Path | None = None,
) -> tuple[Path, state.WorkspaceState]:
    target_url, host = parse_target(url)
    slug = slug_from_host(host)
    product_name = slug.replace("-", " ").title()
    if name is not None and name.strip().lower() in {slug, product_name.lower(), host}:
        raise UsageError(
            f"--name {name!r} reuses the target's name; our product needs its own name (§18.4)",
            code="TARGET_NAME_REUSED",
        )
    ws = (Path(out) if out else (cwd or Path.cwd()) / slug).resolve()
    if (ws / workspace.PF_DIR).exists():
        raise UsageError(
            f"{ws} is already a ProductForge workspace (use pf.py status)", code="WORKSPACE_EXISTS"
        )
    if ws.exists() and not ws.is_dir():
        raise UsageError(f"{ws} exists and is not a directory", code="BAD_OUT_DIR")
    if ws.exists() and any(ws.iterdir()) and not force_adopt:
        hint = "choose another --out, or pass --force-adopt to use this directory"
        raise UsageError(f"{ws} is not empty; {hint}", code="DIR_NOT_EMPTY")

    pf = ws / workspace.PF_DIR
    pf.mkdir(parents=True, exist_ok=True)
    now = workspace.iso(workspace.utc_now())
    scope_text = scope.strip() if scope and scope.strip() else None
    st = state.WorkspaceState(
        product={
            "name": product_name,
            "target_url": target_url,
            "slug": slug,
            "our_name": name.strip() if name else f"{slug}-alt",
            "needs_rename": name is None,
        },
        scope={
            "text": scope_text,
            "source": "user" if scope_text else None,
            "accepted": scope_text is not None,
        },
    )
    state.open_stage(st, state.State.DISCOVERY, now)
    state.save(ws, st)
    config.write_config(ws, {})
    atomic_write_text(pf / ".gitignore", GITIGNORE)

    for rel in catalog.SCAFFOLD_DIRS:
        (ws / rel).mkdir(parents=True, exist_ok=True)
    values = {
        "product_name": product_name,
        "target_url": target_url,
        "date": date.today().isoformat(),
    }
    created = []
    for template, rel in discovery_templates():
        dest = ws / rel
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(dest, _render(template.read_text(encoding="utf-8"), values))
            created.append(rel)
    workspace.append_history(
        ws,
        {"event": "init", "target_url": target_url, "scope": scope_text, "scaffolded": created},
    )
    return ws, st


def set_scope(ws: Path, text: str, accepted: bool, source: str) -> state.WorkspaceState:
    """Record the product scope (user-given or recommended+accepted, §10.5)."""
    if source not in state.SCOPE_SOURCES:
        raise UsageError(f"scope source must be one of {state.SCOPE_SOURCES}", code="BAD_SCOPE")
    if not text.strip():
        raise UsageError("scope text must not be empty", code="BAD_SCOPE")
    st = state.load(ws)
    if st.state != state.State.DISCOVERY:
        raise UsageError(
            f"scope can only be set while DISCOVERY is open (open: {st.state.value})",
            code="STAGE_CLOSED",
        )
    st.scope = {"text": text.strip(), "source": source, "accepted": accepted}
    state.save(ws, st)
    workspace.append_history(ws, {"event": "set-scope", **st.scope})
    return st
