from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from pflib import __version__

Cli = Callable[..., tuple[int, str, str]]

# Every subcommand of the CLI contract must exist.
SECTION_8_SUBCOMMANDS = [
    "init",
    "status",
    "check-command",
    "advance",
    "reopen",
    "next-id",
    "staging",
    "merge",
    "validate",
    "discover",
    "score",
    "lint-phases",
    "trace",
    "check",
]

NO_WORKSPACE = {"workspace": None, "message": "No ProductForge workspace found"}


def test_version(pf_cli: Cli) -> None:
    code, out, _ = pf_cli("--version")
    assert code == 0
    assert out.strip() == __version__  # test_versions.py pins the release number


def test_help_lists_every_section_8_subcommand(pf_cli: Cli) -> None:
    code, out, _ = pf_cli("--help")
    assert code == 0
    for name in SECTION_8_SUBCOMMANDS:
        assert f"    {name} " in out, name


@pytest.mark.parametrize("argv", [["status", "--json"], ["--json", "status"]])
def test_status_json_without_workspace(pf_cli: Cli, argv: list[str]) -> None:
    code, out, err = pf_cli(*argv)
    assert code == 0, err
    assert json.loads(out) == NO_WORKSPACE


def test_status_human_output(pf_cli: Cli) -> None:
    code, out, _ = pf_cli("status")
    assert code == 0
    assert "No ProductForge workspace found" in out


def test_every_subcommand_is_implemented() -> None:
    import pf

    stubs = [name for name, _, _, handler in pf.SUBCOMMANDS
             if handler.__qualname__.startswith("_not_implemented")]  # fmt: skip
    assert stubs == []


def test_usage_error_exits_2(pf_cli: Cli) -> None:
    code, _, err = pf_cli("no-such-command")
    assert code == 2
    assert "invalid choice" in err
