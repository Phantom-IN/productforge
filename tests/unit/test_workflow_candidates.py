from __future__ import annotations

import json
from pathlib import Path

from pflib import config, workflows

EXPECTED = [
    ("Collaboration", "Create and manage — Guest access", ["F-018"]),
    ("Integrations & API", "Create and manage — Public REST API", ["F-025"]),
    ("Projects", "Create and manage — Projects", ["F-011"]),
    ("Workspace & access", "Create and manage — Workspaces", ["F-020"]),
    ("Integrations & API", "Create — Personal access tokens", ["F-026"]),
    ("Workspace & access", "Billing management", ["F-023"]),
    ("Integrations & API", "Configure — Webhooks", ["F-027"]),
    ("Workspace & access", "Sign-in", ["F-024"]),
    ("Integrations & API", "Get notified — Chat notifications", ["F-029"]),
    ("Workspace & access", "Create and manage — Plans and pricing", ["F-031"]),
    ("Integrations & API", "Create and manage — Git commit linking", ["F-030"]),
]


def rows(result: dict) -> list[tuple[str, str, list[str]]]:
    return [(c["domain"], c["name"], c["features"]) for c in result["candidates"]]


def test_snapshot_skips_features_already_covered(tasklet_product_model: Path) -> None:
    result = workflows.candidates(tasklet_product_model)
    assert rows(result) == EXPECTED
    assert result["cap"] == 25 and result["existing_workflows"] == 8
    assert "F-001" in result["features_covered"]  # covered by W-001 → no candidate
    assert workflows.candidates(tasklet_product_model) == result  # deterministic


def test_without_workflows_every_domain_gets_a_turn(tasklet_product_model: Path) -> None:
    for p in workflows.workflow_files(tasklet_product_model):
        p.unlink()
    result = workflows.candidates(tasklet_product_model)
    domains = [c["domain"] for c in result["candidates"]]
    assert sorted(set(domains[:5])) == sorted(set(domains))  # round-robin: one per domain first
    assert len(set(domains)) == 5 and result["features_covered"] == []
    names = [c["name"] for c in result["candidates"]]
    assert names[:5] == [
        "Comments", "Create and manage — Public REST API", "Create and manage — Projects",
        "Create and manage — Tasks", "Create and manage — Workspaces",
    ]  # fmt: skip


def test_cap_counts_existing_workflows(tasklet_product_model: Path) -> None:
    config.write_config(tasklet_product_model, {"model.max_workflows": 10})
    result = workflows.candidates(tasklet_product_model)
    assert len(result["candidates"]) == 2 and result["remaining_candidates"] == 9


def test_cli_json(pf_cli, tasklet_product_model: Path) -> None:  # type: ignore[no-untyped-def]
    code, out, _ = pf_cli(
        "workflow-candidates", "--workspace", str(tasklet_product_model), "--json"
    )
    assert code == 0
    assert [
        (c["domain"], c["name"], c["features"]) for c in json.loads(out)["candidates"]
    ] == EXPECTED
