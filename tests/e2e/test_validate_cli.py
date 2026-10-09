from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path

from conftest import INVALID, TASKLET, apply_overlay

Cli = Callable[..., tuple[int, str, str]]


def test_validate_clean_fixture(pf_cli: Cli) -> None:
    code, out, _ = pf_cli("validate", "--workspace", str(TASKLET / "DISCOVERY"), "--json")
    assert code == 0 and json.loads(out) == {"errors": 0, "warnings": 0, "findings": []}
    code, out, _ = pf_cli("validate", "--workspace", str(TASKLET / "DISCOVERY"))
    assert out.strip() == "0 error(s), 0 warning(s)"


def test_validate_reports_errors_and_exits_1(pf_cli: Cli, tasklet_discovery: Path) -> None:
    apply_overlay(tasklet_discovery, INVALID / "CONFIDENCE_RULE.md")
    code, out, _ = pf_cli("validate", "--workspace", str(tasklet_discovery), "--json")
    payload = json.loads(out)
    assert code == 1 and payload["errors"] == 1
    (f,) = payload["findings"]
    assert f["code"] == "CONFIDENCE_RULE" and f["record_id"] == "D-100"
    code, out, _ = pf_cli("validate", "--workspace", str(tasklet_discovery))
    assert out.startswith("ERROR CONFIDENCE_RULE  research/DISCOVERY_LEDGER.md D-100: ")


def test_warnings_do_not_fail(pf_cli: Cli, tasklet_discovery: Path) -> None:
    apply_overlay(tasklet_discovery, INVALID / "UNKNOWN_FIELD.md")
    code, out, _ = pf_cli("validate", "--workspace", str(tasklet_discovery), "--json")
    assert code == 0 and json.loads(out)["warnings"] == 1


def test_validate_filters(pf_cli: Cli, tasklet_discovery: Path) -> None:
    apply_overlay(tasklet_discovery, INVALID / "BAD_TIER.md")
    code, out, _ = pf_cli(
        "validate", "--stage", "product_model", "--workspace", str(tasklet_discovery), "--json"
    )
    assert code == 0 and json.loads(out)["findings"] == []
    code, out, _ = pf_cli(
        "validate",
        "--artifact",
        "research/sources.md",
        "--workspace",
        str(tasklet_discovery),
        "--json",
    )
    assert code == 1 and json.loads(out)["findings"][0]["code"] == "BAD_TIER"


def test_check_combines_validate_and_gate(pf_cli: Cli, tmp_path: Path) -> None:
    ws = tmp_path / "w"
    shutil.copytree(TASKLET / "DISCOVERY", ws)
    code, out, _ = pf_cli("check", "--workspace", str(ws), "--json")
    payload = json.loads(out)
    assert code == 0 and payload["validate"]["errors"] == 0
    gate = {r["id"]: r["status"] for r in payload["gate"]["results"]}
    assert gate["G-VALIDATE-CLEAN"] == "pass" and gate["G-DISC-TIER1"] == "pass"
    apply_overlay(ws, INVALID / "DANGLING_REF.md")
    code, out, _ = pf_cli("check", "--workspace", str(ws))
    assert code == 1 and "G-VALIDATE-CLEAN" in out
