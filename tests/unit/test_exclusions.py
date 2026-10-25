from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from pflib import exclusions, workspace
from pflib.errors import UsageError


def test_add_persists_canonical_urls_and_logs(tasklet_discovery: Path) -> None:
    out = exclusions.add(
        tasklet_discovery, ["https://docs.tasklet.example/a/?utm_source=x", "https://x.example/b"],
        "duplicate",
    )  # fmt: skip
    assert out["total"] == 2 and "https://docs.tasklet.example/a" in out["excluded"]  # type: ignore[operator]
    data = json.loads((tasklet_discovery / ".productforge/exclusions.json").read_text())
    assert data["https://docs.tasklet.example/a"]["reason"] == "duplicate"
    assert exclusions.load(tasklet_discovery) == data
    assert workspace.read_history(tasklet_discovery)[-1]["event"] == "exclude"


def test_reason_and_urls_are_required(tasklet_discovery: Path) -> None:
    with pytest.raises(UsageError):
        exclusions.add(tasklet_discovery, ["https://x.example/b"], "  ")
    with pytest.raises(UsageError):
        exclusions.add(tasklet_discovery, [], "why")


def test_load_without_file_is_empty(tasklet_discovery: Path) -> None:
    assert exclusions.load(tasklet_discovery) == {}


def test_cli_exclude_and_list(
    pf_cli: Callable[..., tuple[int, str, str]], tasklet_discovery: Path
) -> None:
    ws = str(tasklet_discovery)
    code, out, err = pf_cli(
        "exclude", "https://a.example/x", "https://a.example/y", "--reason", "off-scope",
        "--workspace", ws, "--json",
    )  # fmt: skip
    assert code == 0, err
    assert json.loads(out) == {
        "excluded": ["https://a.example/x", "https://a.example/y"],
        "total": 2,
    }
    code, out, _ = pf_cli("exclude", "--list", "--workspace", ws, "--json")
    assert code == 0 and json.loads(out)["total"] == 2
    code, _, _ = pf_cli("exclude", "https://a.example/z", "--workspace", ws)
    assert code == 2
