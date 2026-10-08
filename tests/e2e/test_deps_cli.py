from __future__ import annotations

import json
import os
import stat
from collections.abc import Callable
from pathlib import Path

from pflib import config

Cli = Callable[..., tuple[int, str, str]]


def fake_claude(tmp_path: Path) -> tuple[Path, Path]:
    log = tmp_path / "claude-calls.log"
    script = tmp_path / "fake-claude"
    script.write_text(
        f'#!/bin/sh\necho "$@" >> "{log}"\nif [ "$1 $2" = "plugin list" ]; then echo "[]"; fi\n'
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script, log


def test_deps_check_install_use_via_cli(
    pf_cli: Cli, tasklet_discovery: Path, tmp_path: Path
) -> None:
    claude, log = fake_claude(tmp_path)
    home = tmp_path / "home"
    (home / ".claude/plugins").mkdir(parents=True)
    config.write_config(tasklet_discovery, {"capabilities.claude_bin": str(claude)})
    env = {"HOME": str(home)}
    ws = str(tasklet_discovery)

    code, out, err = pf_cli(
        "deps", "--available", "anthropic-skills:pdf", "--workspace", ws, "--json", env=env
    )
    assert code == 0, err
    result = json.loads(out)
    assert result["capabilities"]["docs.pdf"]["provider"] == "anthropic-skills:pdf"
    assert result["offer"] == ["repo.intel"]
    assert log.read_text().strip() == "plugin list --json"  # detection only

    code, out, _ = pf_cli("deps", "install", "repo.intel", "--workspace", ws, "--json", env=env)
    payload = json.loads(out)
    assert code == 0 and payload["executed"] is False
    assert log.read_text().count("plugin install") == 0  # nothing ran without --confirmed

    code, out, _ = pf_cli(
        "deps", "install", "repo.intel", "--confirmed", "--workspace", ws, "--json", env=env
    )
    payload = json.loads(out)
    assert code == 0 and payload["executed"] is True
    calls = log.read_text().splitlines()
    assert calls[-2:] == [
        "plugin marketplace add Phantom-IN/contributor-scout",
        "plugin install contributor-scout@phantom-in --scope project",
    ]

    code, out, _ = pf_cli(
        "deps", "use", "repo.intel", "builtin", "--workspace", ws, "--json", env=env
    )
    assert code == 0 and json.loads(out) == {"pins": {"repo.intel": "builtin"}}
    code, out, _ = pf_cli("deps", "offered", "repo.intel", "--workspace", ws, "--json", env=env)
    assert json.loads(out) == {"offered": ["repo.intel"]}
    code, out, _ = pf_cli("deps", "use", "repo.intel", "--workspace", ws, "--json", env=env)
    assert code == 2 and json.loads(out)["error"] == "USAGE_ERROR"


def test_delegate_cli(pf_cli: Cli, tasklet_discovery: Path) -> None:
    code, out, err = pf_cli(
        "delegate",
        "anthropic-skills:deep-research",
        "--task",
        "Who competes with Tasklet?",
        "--workspace",
        str(tasklet_discovery),
        "--json",
    )
    assert code == 0, err
    payload = json.loads(out)
    assert os.path.isdir(payload["raw_dir"]) and payload["kind"] == "skill"
    assert "Who competes with Tasklet?" in payload["prompt"]
