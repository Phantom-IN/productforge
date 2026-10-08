from __future__ import annotations

import json
from pathlib import Path

import pytest

from pflib import scaffold, state, workspace
from pflib.errors import PFError


@pytest.mark.parametrize(
    "host, slug",
    [
        ("linear.app", "linear"),
        ("www.notion.so", "notion"),
        ("docs.tasklet.example", "tasklet"),
        ("shop.example.co.uk", "example"),
        ("localhost", "localhost"),
    ],
)
def test_slug_from_host(host: str, slug: str) -> None:
    assert scaffold.slug_from_host(host) == slug


def test_init_creates_workspace(tmp_path: Path) -> None:
    ws, st = scaffold.init_workspace("https://linear.app/", cwd=tmp_path, scope="issue tracking")
    assert ws == (tmp_path / "linear").resolve()
    assert st.state == state.State.DISCOVERY
    assert st.product == {
        "name": "Linear",
        "target_url": "https://linear.app/",
        "slug": "linear",
        "our_name": "linear-alt",
        "needs_rename": True,
    }
    assert st.scope == {"text": "issue tracking", "source": "user", "accepted": True}
    for rel in ("research", "spec/decisions", "plans"):
        assert (ws / rel).is_dir()
    pf = ws / ".productforge"
    assert json.loads((pf / "config.json").read_text()) == {}
    assert "staging/" in (pf / ".gitignore").read_text()
    assert state.load(ws).stages["DISCOVERY"]["opened_at"]
    assert workspace.read_history(ws)[0]["event"] == "init"


def test_init_refusals(tmp_path: Path) -> None:
    for url in ("linear.app", "ftp://linear.app", "https://"):
        with pytest.raises(PFError) as info:
            scaffold.init_workspace(url, cwd=tmp_path)
        assert info.value.code == "BAD_URL"
    with pytest.raises(PFError) as info:
        scaffold.init_workspace("https://linear.app", cwd=tmp_path, name="Linear")
    assert info.value.code == "TARGET_NAME_REUSED"
    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "notes.txt").write_text("x")
    with pytest.raises(PFError) as info:
        scaffold.init_workspace("https://linear.app", out=str(busy))
    assert info.value.code == "DIR_NOT_EMPTY"
    ws, _ = scaffold.init_workspace("https://linear.app", out=str(busy), force_adopt=True)
    assert (busy / "notes.txt").exists()
    with pytest.raises(PFError) as info:
        scaffold.init_workspace("https://linear.app", out=str(ws), force_adopt=True)
    assert info.value.code == "WORKSPACE_EXISTS"


def test_custom_name_needs_no_rename(tmp_path: Path) -> None:
    _, st = scaffold.init_workspace("https://linear.app", cwd=tmp_path, name="Trackwell")
    assert st.product["our_name"] == "Trackwell" and st.product["needs_rename"] is False


def test_templates_owned_by_discovery_are_rendered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tpl = tmp_path / "templates"
    (tpl / "research").mkdir(parents=True)
    (tpl / "research" / "sources.md").write_text(
        "# Sources for {{product_name}} ({{target_url}})\n"
    )
    (tpl / "research" / "research-README.md").write_text("# Research — {{product_name}}\n")
    (tpl / "research" / "FEATURE_MATRIX.md").write_text("# not a DISCOVERY artifact\n")
    (tpl / "research" / "workflow.md").write_text("# per-record template, not an artifact\n")
    monkeypatch.setattr(scaffold, "TEMPLATES_DIR", tpl)
    ws, _ = scaffold.init_workspace("https://tasklet.example", out=str(tmp_path / "w"))
    assert (ws / "research/sources.md").read_text() == (
        "# Sources for Tasklet (https://tasklet.example)\n"
    )
    assert (ws / "research/README.md").read_text() == "# Research — Tasklet\n"
    assert not (ws / "research/FEATURE_MATRIX.md").exists()
    assert not (ws / "research/workflow.md").exists()


def test_set_scope_only_in_discovery(new_ws: Path) -> None:
    st = scaffold.set_scope(new_ws, "projects only", accepted=True, source="recommended")
    assert st.scope == {"text": "projects only", "source": "recommended", "accepted": True}
    with pytest.raises(PFError):
        scaffold.set_scope(new_ws, " ", accepted=True, source="user")
    loaded = state.load(new_ws)
    state.transition(loaded, state.State.PRODUCT_MODEL, "2026-10-08T00:00:00Z")
    state.save(new_ws, loaded)
    with pytest.raises(PFError) as info:
        scaffold.set_scope(new_ws, "x", accepted=True, source="user")
    assert info.value.code == "STAGE_CLOSED"
