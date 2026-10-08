from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from pflib import __version__

Cli = Callable[..., tuple[int, str, str]]

# IMPLEMENTATION_PLAN.md §8 — every subcommand must exist in the CLI contract.
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
    assert out.strip() == __version__ == "0.1.0"


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


@pytest.mark.parametrize(
    "argv, phase",
    [
        (["score"], "13"),
        (["lint-phases"], "15"),
        (["trace"], "16"),
    ],
)
def test_unimplemented_subcommands_exit_2(pf_cli: Cli, argv: list[str], phase: str) -> None:
    code, out, err = pf_cli(*argv, "--json")
    assert code == 2
    payload = json.loads(out)
    assert payload["error"] == "NOT_IMPLEMENTED"
    assert payload["message"] == f"{argv[0]}: not implemented (phase {phase})"
    assert "not implemented" in err


def test_usage_error_exits_2(pf_cli: Cli) -> None:
    code, _, err = pf_cli("no-such-command")
    assert code == 2
    assert "invalid choice" in err
