from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from pflib import capabilities as caps
from pflib.errors import PFError

REAL = json.loads(caps.REGISTRY_PATH.read_text())


def write_registry(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "capabilities.json"
    path.write_text(json.dumps(data))
    return path


def fake_home(tmp_path: Path, plugins: dict | None = None, skills: tuple[str, ...] = (),
              markets: tuple[str, ...] = ()) -> Path:  # fmt: skip
    home = tmp_path / "home"
    (home / ".claude" / "plugins").mkdir(parents=True)
    if plugins is not None:
        (home / ".claude/plugins/installed_plugins.json").write_text(
            json.dumps({"version": 2, "plugins": plugins})
        )
    (home / ".claude/plugins/known_marketplaces.json").write_text(
        json.dumps({m: {"source": {}} for m in markets})
    )
    for name in skills:
        (home / ".claude/skills" / name).mkdir(parents=True)
        (home / ".claude/skills" / name / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
    return home


SCOUT = {"contributor-scout@phantom-in": [{"version": "1.2.0", "installPath": "/x/scout"}]}


def test_real_registry_is_valid_and_every_capability_has_a_fallback() -> None:
    reg = caps.load_registry()
    assert set(reg.capabilities) == {
        "research.deep",
        "web.browse",
        "docs.pdf",
        "repo.intel",
        "graph.explore",
        "report.publish",
        "diagram.render",
        "browser.observe",
    }
    for cap in reg.capabilities.values():
        assert cap.providers[-1].kind == ("builtin" if cap.required else "none")
        assert all(not p.is_fallback for p in cap.providers[:-1])


@pytest.mark.parametrize(
    "mutate, code",
    [
        (lambda d: d["capabilities"]["research.deep"]["providers"].pop(), "CAP_NO_FALLBACK"),
        (
            lambda d: d["capabilities"]["graph.explore"]["providers"][-1].update(
                kind="builtin", id="builtin"
            ),
            "CAP_NO_FALLBACK",
        ),
        (
            lambda d: d["capabilities"]["repo.intel"]["providers"][0]["install"].update(
                marketplace="shady"
            ),
            "CAP_UNKNOWN_MARKETPLACE",
        ),
        (
            lambda d: d["capabilities"]["docs.pdf"]["providers"][0].update(kind="magic"),
            "CAP_SCHEMA",
        ),
        (
            lambda d: d["capabilities"]["docs.pdf"]["providers"][0].update(adapter="nope.md"),
            "CAP_SCHEMA",
        ),
        (
            lambda d: d["capabilities"]["docs.pdf"]["providers"][0].update(detect={"x": 1}),
            "CAP_SCHEMA",
        ),
        (
            lambda d: d["capabilities"]["docs.pdf"]["providers"][0].update(trust="anyone"),
            "CAP_SCHEMA",
        ),
        (lambda d: d.update(version=2), "CAP_SCHEMA"),
    ],
)
def test_registry_validation(tmp_path: Path, mutate, code: str) -> None:  # type: ignore[no-untyped-def]
    data = copy.deepcopy(REAL)
    mutate(data)
    with pytest.raises(PFError) as info:
        caps.load_registry(write_registry(tmp_path, data))
    assert info.value.code == code


def test_nothing_installed_resolves_everything_to_fallbacks(tmp_path: Path) -> None:
    reg = caps.load_registry()
    det = caps.detect(reg, set(), fake_home(tmp_path), None, None)
    resolved = caps.resolve(reg, det)
    assert {k: r.provider for k, r in resolved.items()} == {
        "research.deep": "builtin",
        "web.browse": "builtin",
        "docs.pdf": "builtin",
        "repo.intel": "builtin",
        "graph.explore": "none",
        "report.publish": "none",
        "diagram.render": "builtin",
        "browser.observe": "none",
    }
    assert resolved["repo.intel"].installable == ["contributor-scout:repository-intelligence"]
    assert caps.offers(reg, resolved, {}, []) == ["repo.intel"]
    assert caps.offers(reg, resolved, {}, ["repo.intel"]) == []
    assert caps.offers(reg, resolved, {"repo.intel": "builtin"}, []) == []


def test_detection_sources(tmp_path: Path) -> None:
    reg = caps.load_registry()
    home = fake_home(tmp_path, plugins=SCOUT, skills=("graphify",))
    host = {"deep-research", "anthropic-skills:chrome-browser", "Artifact"}
    det = caps.detect(reg, host, home, None, None)
    assert det["anthropic-skills:deep-research"].installed  # short-name match
    assert det["anthropic-skills:chrome-browser"].installed
    assert not det["anthropic-skills:built-in-browser"].installed
    assert det["artifact"].installed and det["artifact"].source == "host"
    scout = det["contributor-scout:repository-intelligence"]
    assert scout.installed and scout.version == "1.2.0" and scout.source == "installed_plugins.json"
    assert det["graphify"].installed and det["graphify"].source == "skills dir"
    resolved = caps.resolve(reg, det)
    assert resolved["web.browse"].provider == "anthropic-skills:chrome-browser"
    assert resolved["repo.intel"].provider == "contributor-scout:repository-intelligence"
    assert resolved["repo.intel"].version == "1.2.0"


def test_cli_plugin_list_wins_and_respects_disabled(tmp_path: Path) -> None:
    reg = caps.load_registry()
    home = fake_home(tmp_path, plugins=SCOUT)
    disabled = [{"id": "contributor-scout@phantom-in", "version": "1.3.0", "enabled": False}]
    det = caps.detect(reg, set(), home, None, disabled)
    assert not det["contributor-scout:repository-intelligence"].installed
    enabled = [{"id": "contributor-scout@phantom-in", "version": "1.3.0", "enabled": True}]
    det = caps.detect(reg, set(), home, None, enabled)
    assert det["contributor-scout:repository-intelligence"].version == "1.3.0"


def test_project_skills_are_detected(tmp_path: Path) -> None:
    reg = caps.load_registry()
    project = tmp_path / "proj"
    (project / ".claude/skills/graphify").mkdir(parents=True)
    (project / ".claude/skills/graphify/SKILL.md").write_text("---\nname: graphify\n---\n")
    det = caps.detect(reg, set(), fake_home(tmp_path), project, None)
    assert det["graphify"].installed


def test_pins(tmp_path: Path) -> None:
    reg = caps.load_registry()
    det = caps.detect(reg, {"deep-research"}, fake_home(tmp_path, plugins=SCOUT), None, None)
    r = caps.resolve(
        reg,
        det,
        {"research.deep": "builtin", "repo.intel": "nope", "docs.pdf": "anthropic-skills:pdf"},
    )
    assert r["research.deep"].provider == "builtin" and r["research.deep"].pinned
    assert r["repo.intel"].provider == "contributor-scout:repository-intelligence"
    assert "ignored" in r["repo.intel"].note
    assert r["docs.pdf"].provider == "builtin" and "not available" in r["docs.pdf"].note


def test_install_commands(tmp_path: Path) -> None:
    reg = caps.load_registry()
    prov = caps.install_target(reg, "repo.intel")
    fresh = caps.install_commands(reg, prov, "project", "claude", fake_home(tmp_path / "a"))
    assert fresh == [
        ["claude", "plugin", "marketplace", "add", "Phantom-IN/contributor-scout"],
        ["claude", "plugin", "install", "contributor-scout@phantom-in", "--scope", "project"],
    ]
    known = caps.install_commands(
        reg, prov, "user", "/bin/cl", fake_home(tmp_path / "b", markets=("phantom-in",))
    )
    assert known == [
        ["/bin/cl", "plugin", "install", "contributor-scout@phantom-in", "--scope", "user"]
    ]
    text = caps.consent_text(reg, prov, "project", fresh)
    assert "contributor-scout@phantom-in" in text and "new Claude Code session" in text


def test_install_target_refusals() -> None:
    reg = caps.load_registry()
    for target in ("research.deep", "anthropic-skills:pdf", "graphify"):
        with pytest.raises(PFError) as info:
            caps.install_target(reg, target)
        assert info.value.code == "CAP_NOT_INSTALLABLE"
    with pytest.raises(PFError) as info:
        caps.install_target(reg, "evil-plugin")
    assert info.value.code == "CAP_UNKNOWN"
